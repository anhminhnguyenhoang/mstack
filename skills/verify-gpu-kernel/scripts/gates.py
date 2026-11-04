#!/usr/bin/env python3
"""The five proof gates of one bench.run artifact.

  1 correct    gate.py PASS, no NaN, snr_db present when the output is fp8/fp4
  2 codegen    the isa.diff report in the artifact is OK (n/a without one)
  3 surface    expected arch, package imported from the tree under test,
               clean repo, every JIT module from this run's JIT dir
  4 explained  every perf row carries pct_of_peak with its source (n/a without perf)
  5 noise      every perf row is a median of >= MIN_RUNS runs; reports the
               noise floor, the largest same-revision spread (n/a without perf)

A delta smaller than the noise floor is not a result.

usage: gates.py ARTIFACT.json [--min-runs 5] [--json OUT]
       gates.py --selftest
exit:  0 PASS, 1 FAIL, 2 INCONCLUSIVE (n/a gates do not count)
"""

import argparse
import copy
import json
import sys

PASS, FAIL, INC, NA = "PASS", "FAIL", "INCONCLUSIVE", "n/a"


def correct(art):
    c = art.get("correctness") or {}
    nan = c.get("nan_count", c.get("nan_lines", 0))
    why = []
    if c.get("verdict") == INC:
        return INC, ["gate.py found no check in the log"]
    if not c.get("passed"):
        why.append(f"gate.py {c.get('verdict', 'missing')}")
    if nan:
        why.append(f"{nan} NaN line(s)")
    if c.get("snr_required") and c.get("snr_db") is None:
        why.append("fp8/fp4 output without snr_db: run under checkwrap.py snr")
    return (FAIL, why) if why else (PASS, [f"nan 0, snr_db {c.get('snr_db')}"])


def codegen(art):
    isa = art.get("isa")
    if not isa:
        return NA, ["no isa.diff report in this run"]
    state = {0: PASS, 1: FAIL}.get(isa.get("exit_code"), INC)
    return state, [f"isa.diff {isa.get('verdict')}, worsened {isa.get('worsened_metrics', [])}"]


def surface(art):
    s = art.get("surface")
    if not s:
        return INC, ["artifact has no surface block (written before gates.py)"]
    why, inc = [], []
    arch = art.get("gpu", {}).get("arch")
    if str(art.get("gpu", {}).get("hip_index", "")).strip() == "":
        why.append("no hip_index: the run did not pin the GPU it locked")
    if not s.get("arch_expected"):
        inc.append("no arch_expected in facts.env")
    elif arch != s["arch_expected"]:
        why.append(f"arch {arch} != expected {s['arch_expected']}")
    pkg, wt = s.get("pkg"), s.get("wt", "").rstrip("/")
    origin = art.get("imports", {}).get(pkg, "")
    if not (pkg and wt):
        inc.append("no pkg or wt in facts.env")
    elif not origin.startswith(wt + "/"):
        why.append(f"{pkg} imported from {origin or 'nowhere'}, not under {wt}")
    if any(r.get("dirty") for r in art.get("repos", [])):
        why.append("dirty repo")
    in_jit = art.get("jit_modules_in_jit_dir")
    if in_jit is False:
        why.append(f"JIT module outside {art.get('jit_dir') or 'any per-run JIT dir'}")
    elif in_jit is None and pkg == "aiter" and art.get("jit_modules"):
        why.append("aiter under test with no per-revision AITER_JIT_DIR")
    if why:
        return FAIL, why + inc
    return (INC, inc) if inc else (PASS, [f"{arch}, {pkg} under {wt}"])


def explained(art):
    rows = perf_rows(art)
    if rows is None:
        return FAIL, ["perf is not a list of bench.run rows"]
    if not rows:
        return NA, ["no perf rows"]
    bare = [r for r in rows if r.get("pct_of_peak") is None or not r.get("peak_source")]
    if bare:
        return FAIL, [f"{len(bare)} of {len(rows)} perf rows lack pct_of_peak: perf.py --rate-col --peak --peak-source"]
    lo = min(r["pct_of_peak"] for r in rows)
    hi = max(r["pct_of_peak"] for r in rows)
    return PASS, [f"{lo} to {hi} % of peak ({rows[0]['peak_source']})"]


def perf_rows(art):
    rows = art.get("perf") or []
    return rows if isinstance(rows, list) and all(isinstance(r, dict) for r in rows) else None


def spread(r):
    if r.get("spread_pct") is not None:
        return r["spread_pct"]
    med, hi, lo = r.get("us_median"), r.get("max_us"), r.get("min_us")
    return 100 * (hi - lo) / med if med and hi is not None and lo is not None else None


def noise(art, min_runs):
    rows = perf_rows(art)
    if rows is None:
        return FAIL, ["perf is not a list of bench.run rows"], None
    if not rows:
        return NA, ["no perf rows"], None
    short = [r for r in rows if (r.get("runs") or 0) < min_runs]
    spreads = [s for s in map(spread, rows) if s is not None]
    floor = round(max(spreads), 3) if spreads else None
    if short:
        return FAIL, [f"{len(short)} of {len(rows)} rows have < {min_runs} runs"], floor
    return PASS, [f"noise floor {floor} % over {len(rows)} rows"], floor


def check(art, min_runs=5):
    n_state, n_why, floor = noise(art, min_runs)
    gates = {
        "correct": correct(art),
        "codegen": codegen(art),
        "surface": surface(art),
        "explained": explained(art),
        "noise": (n_state, n_why),
    }
    states = [g[0] for g in gates.values()]
    verdict = FAIL if FAIL in states else INC if INC in states else PASS
    return {
        "verdict": verdict,
        "noise_floor_pct": floor,
        "gates": {k: {"state": s, "why": w} for k, (s, w) in gates.items()},
    }


def selftest():
    good = {
        "gpu": {"arch": "gfx950", "hip_index": "6"},
        "repos": [{"path": "/r", "sha": "a", "dirty": False}],
        "imports": {"aiter": "/w/t/aiter/__init__.py"},
        "surface": {"wt": "/w/t", "pkg": "aiter", "arch_expected": "gfx950"},
        "jit_modules_in_jit_dir": True,
        "correctness": {"passed": True, "verdict": PASS, "nan_count": 0, "snr_db": None, "snr_required": False},
        "perf": [{"us_median": 10, "runs": 7, "min_us": 9.9, "max_us": 10.1, "spread_pct": 2.0,
                  "pct_of_peak": 61.0, "peak_source": "TB/s / 8.0 (spec)"}],
        "isa": None,
    }
    r = check(good)
    assert r["verdict"] == PASS and r["gates"]["codegen"]["state"] == NA and r["noise_floor_pct"] == 2.0, r

    def mut(value, *path):
        a = copy.deepcopy(good)
        tgt = a
        for k in path[:-1]:
            tgt = tgt[k]
        tgt[path[-1]] = value
        return check(a)

    assert mut(2, "correctness", "nan_count")["gates"]["correct"]["state"] == FAIL
    assert mut(True, "correctness", "snr_required")["gates"]["correct"]["state"] == FAIL
    assert mut({"passed": False, "verdict": INC}, "correctness")["verdict"] == INC
    assert mut("gfx942", "gpu", "arch")["gates"]["surface"]["state"] == FAIL
    assert mut("", "gpu", "hip_index")["gates"]["surface"]["state"] == FAIL
    assert mut("/sgl-workspace/aiter/aiter/__init__.py", "imports", "aiter")["gates"]["surface"]["state"] == FAIL
    assert mut("/w/t2/aiter/__init__.py", "imports", "aiter")["gates"]["surface"]["state"] == FAIL
    assert mut(False, "jit_modules_in_jit_dir")["verdict"] == FAIL
    dep = copy.deepcopy(good)
    dep.update(jit_modules_in_jit_dir=None, jit_modules=[{"module": "m", "path": "/img/m.so"}])
    assert check(dep)["gates"]["surface"]["state"] == FAIL
    dep["surface"]["pkg"], dep["imports"]["sglang"] = "sglang", "/w/t/python/sglang/__init__.py"
    assert check(dep)["gates"]["surface"]["state"] == PASS
    assert mut("", "surface", "arch_expected")["gates"]["surface"]["state"] == INC
    assert mut(None, "surface")["gates"]["surface"]["state"] == INC
    assert mut({"exit_code": 1, "verdict": "REGRESSION"}, "isa")["gates"]["codegen"]["state"] == FAIL
    assert mut({"exit_code": 0, "verdict": "OK"}, "isa")["gates"]["codegen"]["state"] == PASS
    unexplained = [{"us_median": 10, "runs": 7, "min_us": 9, "max_us": 11}]
    assert mut(unexplained, "perf")["gates"]["explained"]["state"] == FAIL
    assert mut(unexplained, "perf")["noise_floor_pct"] == 20.0
    assert mut([dict(good["perf"][0], runs=3)], "perf")["gates"]["noise"]["state"] == FAIL
    assert mut([], "perf")["verdict"] == PASS
    assert mut([{"us_median": 10, "runs": 7}], "perf")["noise_floor_pct"] is None
    assert mut({"B": 1.0}, "perf")["gates"]["noise"]["state"] == FAIL
    assert mut({"passed": True, "verdict": PASS, "nan_lines": 1}, "correctness")["gates"]["correct"]["state"] == FAIL
    print("selftest OK")


def main(argv):
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    p = argparse.ArgumentParser(usage=__doc__)
    p.add_argument("artifact")
    p.add_argument("--min-runs", type=int, default=5)
    p.add_argument("--json")
    a = p.parse_args(argv[1:])
    with open(a.artifact) as f:
        res = check(json.load(f), a.min_runs)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=2)
    for name, g in res["gates"].items():
        print(f"{name:<10} {g['state']:<13} {'; '.join(g['why'])}")
    print(f"GATES: {res['verdict']}")
    return {PASS: 0, FAIL: 1}.get(res["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
