#!/usr/bin/env python3
"""Build the bench.run artifact JSON from the files one run wrote.

RUN must hold: facts.env (key=value, from the doctor commands), cmd.txt,
stdout.log, gate.json (gate.py --json). Optional: perf.json (perf.py) and
isa.json (the isa.diff `--json` report).

usage: artifact.py RUN OUT.json [--climb DIR | --base SHA]
  --climb DIR  base_sha is the baseline SHA (B) in DIR/harness.lock
  --base SHA   base_sha is SHA, given directly
  neither      the artifact has no base_sha
"""

import argparse
import datetime
import importlib.util
import json
import pathlib
import re
import sys

CLIMB_GATE = pathlib.Path(__file__).resolve().parents[3] / "scripts" / "climb-gate.py"


def optional_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def climb_baseline(climb):
    spec = importlib.util.spec_from_file_location("climb_gate", CLIMB_GATE)
    cg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cg)
    lock = cg.lock_file(climb)
    if not pathlib.Path(lock).is_file():
        sys.exit(f"no {lock}: freeze the climb first")
    return (cg.load(climb).get("baseline") or {}).get("sha")


def main(run, out, climb=None, base=None):
    base_sha = base or (climb_baseline(climb) if climb else None)
    f = dict(
        ln.split("=", 1) for ln in (run / "facts.env").read_text().splitlines() if "=" in ln
    )
    log = (run / "stdout.log").read_text(errors="replace")
    mods = sorted(set(re.findall(r"import \[(\S+)\] under (\S+)", log)))
    jit = f.get("jit_dir", "")
    gate = json.loads((run / "gate.json").read_text())
    tols = gate.get("tolerances", [])
    checks = gate.get("checks", {})
    art = {
        "key": f.get("key", ""),
        "feature": f.get("feature", ""),
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "host": f["host"],
        "container": f["container"],
        "image": f["image"],
        "gpu": {"hip_index": f["hip_index"], "arch": f["arch"]},
        "versions": {k: f.get(k, "") for k in ("rocm", "torch", "hip", "triton", "flydsl")},
        "repos": [{"path": f["repo"], "sha": f["sha"], "dirty": f["dirty"] != "0"}],
        "command": (run / "cmd.txt").read_text().strip(),
        "imports": {k[len("origin_"):]: v for k, v in f.items() if k.startswith("origin_")},
        "surface": {
            "wt": f.get("wt", ""),
            "pkg": f.get("pkg", ""),
            "arch_expected": f.get("arch_expected", ""),
        },
        "jit_dir": jit,
        "jit_modules": [{"module": m, "path": p} for m, p in mods],
        "jit_modules_in_jit_dir": all(p.startswith(jit + "/") for _, p in mods) if jit else None,
        "correctness": {
            "passed": gate["passed"],
            "verdict": gate["verdict"],
            "nan_count": gate.get("nan_count", 0),
            "rtol": max((float(t["rtol"]) for t in tols), default=None),
            "atol": max((float(t["atol"]) for t in tols), default=None),
            "snr_db": gate.get("snr_db"),
            "snr_required": f.get("snr_required", "0") == "1",
            "shapes_checked": checks.get("passed~", 0) + checks.get("warning!", 0)
            + gate.get("pytest_passed", 0) + gate.get("mha_cases", 0),
            "gate": gate,
        },
        "perf": optional_json(run / "perf.json", []),
        "isa": optional_json(run / "isa.json", None),
        "raw_output": str((run / "stdout.log").resolve()),
    }
    if base_sha:
        art["base_sha"] = base_sha
    out.write_text(json.dumps(art, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(usage=__doc__)
    p.add_argument("run", type=pathlib.Path)
    p.add_argument("out", type=pathlib.Path)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--climb")
    g.add_argument("--base")
    a = p.parse_args()
    main(a.run, a.out, a.climb, a.base)
