#!/usr/bin/env python3
"""Correctness verdict for one aiter op-test log.

aiter's checkAllclose logs a mismatch and returns a ratio. It raises only on a
catastrophic error, so an op test can exit 0 with failed checks. Read the log.

usage: gate.py LOG EXIT_CODE [--json OUT] [--strict]
--strict: a checkAllclose warning! (mismatch within tol_err_ratio) fails, for tests whose predicate is zero error
       gate.py --selftest
exit:  0 PASS, 1 FAIL, 2 INCONCLUSIVE (no evidence that any check ran)
"""

import json
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
CHECK = re.compile(
    r"\[checkAllclose atol=(?P<atol>\S+) rtol=(?P<rtol>\S+) "
    r"(?P<state>passed~|warning!|failed!|catastrophic!|skipped: empty mask)\]"
)
# Triton prints this only under TRITON_PRINT_AUTOTUNING=1;
# aiter CI fails a unit test that autotunes (.github/workflows/triton-test.yaml)
HARD = re.compile(
    r"Traceback \(most recent call last\)|AssertionError|"
    r"accuracy check failed|output contains NaN|Triton autotuning for function"
)
# `pytest -q` prints the summary bare, default verbosity wraps it in `=`;
# the subtests plugin adds two-word items ("4 subtests passed")
PYTEST_SUMMARY = re.compile(
    r"^=*\s*((?:\d+ [a-z]+(?: [a-z]+)?(?:, )?)+) in [\d.]+s\b", re.M
)
UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in [\d.]+s\s*\n+\s*(OK|FAILED)\b(.*)$", re.M)
MHA_CASE = re.compile(r"^Output max diff:", re.M)
NAN = re.compile(r"\bnan\b")
WRAPPED_PASS = re.compile(r"^\[checkwrap\] assert_close passed", re.M)
JSON_TABLE = re.compile(r'^\{"name": .*"rows": \[(.*)\]\}$', re.M)
SNR = re.compile(r"\[snr_db=(-?inf|-?[\d.]+)\]")


def table_rows(lines):
    rows = 0
    for i, line in enumerate(lines):
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", line):
            prev = lines[i - 1] if i else ""
            if prev.startswith("|"):
                rows += 1
    return rows


def parse(text, rc, strict=False):
    text = ANSI.sub("", text)
    lines = text.splitlines()
    states = {"passed~": 0, "warning!": 0, "failed!": 0, "catastrophic!": 0}
    tols = set()
    for m in CHECK.finditer(text):
        if m["state"] in states:
            states[m["state"]] += 1
        tols.add((m["rtol"], m["atol"]))
    hard = sorted({m.group(0) for m in HARD.finditer(text)})
    # pandas prints nan for skipped candidates, so look for NaN outside tables only
    nan_lines = sum(
        1 for ln in lines if not ln.startswith("|") and NAN.search(ln.lower())
    )
    pytest = {}
    for summary in PYTEST_SUMMARY.findall(text):
        for n, word in re.findall(r"(\d+) ([a-z]+(?: [a-z]+)?)", summary):
            word = word.replace("errors", "error")
            pytest[word] = pytest.get(word, 0) + int(n)
    pytest_passed = pytest.get("passed", 0)
    pytest_skipped = pytest.get("skipped", 0)
    pytest_failed = sum(
        pytest.get(k, 0) for k in ("failed", "error", "subtests failed", "subtests error")
    )
    for ran, state, rest in UNITTEST_RAN.findall(text):
        skipped = sum(int(n) for n in re.findall(r"skipped=(\d+)", rest))
        pytest_skipped += skipped
        if state == "OK":
            pytest_passed += int(ran) - skipped
        else:
            pytest_failed += sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", rest)) or 1
    rows = table_rows(lines) + sum(m.count('{"') for m in JSON_TABLE.findall(text))
    wrapped = len(WRAPPED_PASS.findall(text))
    mha_cases = len(MHA_CASE.findall(text))
    snrs = [float(s) for s in SNR.findall(text)]

    reasons = []
    if rc != 0:
        reasons.append(f"exit code {rc}")
    if states["failed!"] or states["catastrophic!"]:
        reasons.append(
            f"{states['failed!']} failed!, {states['catastrophic!']} catastrophic!"
        )
    if strict and states["warning!"]:
        reasons.append(f"{states['warning!']} warning! under --strict")
    reasons += hard
    if pytest_failed:
        reasons.append(f"pytest/unittest: {pytest_failed} failed or errored")
    if nan_lines:
        reasons.append(f"{nan_lines} log line(s) outside tables mention nan")
    evidence = states["passed~"] + states["warning!"] + pytest_passed + mha_cases + wrapped
    if reasons:
        verdict = "FAIL"
    elif evidence == 0:
        verdict = "INCONCLUSIVE"
        reasons.append("no checkAllclose line, pytest or unittest pass, or MHA case in the log")
    else:
        verdict = "PASS"
    return {
        "verdict": verdict,
        "passed": verdict == "PASS",
        "exit_code": rc,
        "checks": states,
        "tolerances": [{"rtol": r, "atol": a} for r, a in sorted(tols)],
        "pytest_passed": pytest_passed,
        "pytest_skipped": pytest_skipped,
        "mha_cases": mha_cases,
        "wrapped_passes": wrapped,
        "table_rows": rows,
        "nan_count": nan_lines,
        "snr_db": min(snrs) if snrs else None,
        "snr_checks": len(snrs),
        "reasons": reasons,
    }


def selftest():
    ok = "[aiter] hip: dynamic quant[checkAllclose atol=0.001 rtol=0.001 \x1b[32mpassed~\x1b[0m]\n"
    table = "| m | hip dq |\n|---:|---:|\n| 1 | 3.1 |\n| 2 | nan |\n"
    bad = "[aiter] hip: dynamic quant[checkAllclose atol=0.001 rtol=0.001 \x1b[31mfailed!\x1b[0m]\n"
    nan = ok + "-->max abs delta:nan, delta details: 1.0% (1 of 100) elements\n"
    assert parse(ok + table, 0)["verdict"] == "PASS"
    assert parse(ok + table, 0)["table_rows"] == 2
    assert parse(ok + bad + table, 0)["verdict"] == "FAIL"
    warn = ok.replace("passed~", "warning!")
    assert parse(warn, 0)["verdict"] == "PASS" and parse(warn, 0, strict=True)["verdict"] == "FAIL"
    assert parse(ok, 1)["verdict"] == "FAIL"
    assert parse(nan, 0)["verdict"] == "FAIL"
    assert parse("unsupported on gfx942; skipping\n", 0)["verdict"] == "INCONCLUSIVE"
    assert parse("===== 3 passed, 1 skipped in 2.0s =====\n", 0)["verdict"] == "PASS"
    assert parse("===== 1 failed, 3 passed in 2.0s =====\n", 1)["verdict"] == "FAIL"
    assert parse("..s    [100%]\n2 passed, 1 skipped in 0.00s\n", 0)["verdict"] == "PASS"
    assert parse("1 failed, 3 passed in 2.0s\n", 0)["verdict"] == "FAIL"
    assert parse("1 error in 0.02s\n", 0)["verdict"] == "FAIL"
    assert parse("3 skipped in 1.0s\n", 0)["verdict"] == "INCONCLUSIVE"
    assert parse(ok, 0)["pytest_passed"] == 0
    assert parse("Ran 4 tests in 1.2s\n\nOK (skipped=1)\n", 0)["verdict"] == "PASS"
    assert parse("Ran 4 tests in 1.2s\n\nOK (skipped=1)\n", 0)["pytest_passed"] == 3
    assert parse("Ran 4 tests in 1.2s\n\nFAILED (failures=1)\n", 0)["verdict"] == "FAIL"
    assert parse("Ran 2 tests in 0.1s\n\nOK (skipped=2)\n", 0)["verdict"] == "INCONCLUSIVE"
    sub = "3 passed, 5 warnings, 4 subtests passed in 11.90s\n"
    assert parse(sub, 0)["verdict"] == "PASS" and parse(sub, 0)["pytest_passed"] == 3
    assert parse("1 passed, 2 subtests failed in 1.0s\n", 1)["verdict"] == "FAIL"
    assert "pytest/unittest: 2 failed or errored" in parse("1 passed, 2 subtests failed in 1.0s\n", 0)["reasons"]
    tuned = "Triton autotuning for function _k finished after 1.2s\n2 passed in 3.0s\n"
    assert parse(tuned, 0)["verdict"] == "FAIL"
    assert parse("Output max diff: 0.001\n", 0)["verdict"] == "PASS"
    assert parse("[checkwrap] assert_close passed\n", 0)["verdict"] == "PASS"
    js = '{"name": "t", "rows": [{"m": 1, "us": 2}, {"m": 2, "us": 3}]}\n'
    assert parse(ok + js, 0)["table_rows"] == 2
    snr = "[snr_db=31.50] fp8 out\n[snr_db=inf] exact\n" + ok
    assert parse(snr, 0)["snr_db"] == 31.5 and parse(snr, 0)["snr_checks"] == 2
    assert parse(ok, 0)["snr_db"] is None
    assert parse("[snr_db=nan] x\n" + ok, 0)["verdict"] == "FAIL"
    assert parse(nan, 0)["nan_count"] == 1
    print("selftest OK")


def main(argv):
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    strict = "--strict" in argv
    argv = [a for a in argv if a != "--strict"]
    if len(argv) not in (3, 5) or (len(argv) == 5 and argv[3] != "--json"):
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], errors="replace") as f:
        res = parse(f.read(), int(argv[2]), strict)
    if len(argv) == 5:
        with open(argv[4], "w") as f:
            json.dump(res, f, indent=2)
    c = res["checks"]
    print(
        f"checkAllclose: {c['passed~']} passed~, {c['warning!']} warning!, "
        f"{c['failed!']} failed!, {c['catastrophic!']} catastrophic! | "
        f"pytest passed {res['pytest_passed']}, skipped {res['pytest_skipped']} | "
        f"table rows {res['table_rows']} | tolerances {res['tolerances']} | "
        f"nan {res['nan_count']} | snr_db {res['snr_db']}"
    )
    for r in res["reasons"]:
        print(f"  reason: {r}")
    print(f"GATE: {res['verdict']}")
    return {"PASS": 0, "FAIL": 1}.get(res["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
