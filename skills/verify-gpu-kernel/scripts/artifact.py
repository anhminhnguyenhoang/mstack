#!/usr/bin/env python3
"""Build the bench.run artifact JSON from the files one run wrote.

RUN must hold: facts.env (key=value, from the doctor commands), cmd.txt,
stdout.log, gate.json (gate.py --json). Optional: perf.json (perf.py) and
isa.json (the isa.diff `--json` report).

usage: artifact.py RUN OUT.json
"""

import datetime
import json
import pathlib
import re
import sys

PACKAGES = ("aiter", "sglang")


def optional_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def main(run, out):
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
        "imports": {k: f[k] for k in PACKAGES if k in f},
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
    out.write_text(json.dumps(art, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
