#!/usr/bin/env python3
"""Check a baseline and an optimized design with protocol-check.sh, and compare their rules.

  protocol-compare.py --base SPEC.tla:CFG --opt SPEC.tla:CFG [--view VIEW] [--out DIR]

Each side is a spec and its config, so one spec with two configs and two specs both work. --view
applies to both sides. The output is markdown: a table of each rule on each side, then both charts.
Exit 0 when the optimized side holds every rule the baseline holds, 1 when it breaks one of them,
3 on an error.
"""

import argparse
import pathlib
import re
import subprocess
import sys
import tempfile

CHECK = pathlib.Path(__file__).resolve().parent / "protocol-check.sh"


def run(side, view, out):
    spec, _, cfg = side.partition(":")
    cmd = [str(CHECK), spec] + (["--config", cfg] if cfg else []) + (["--view", view] if view else [])
    r = subprocess.run(cmd + ["--out", str(out)], capture_output=True, text=True)
    report = out / "report.md"
    if not report.exists():
        sys.exit(f"protocol-compare: {side} did not run:\n{r.stderr.strip() or r.stdout.strip()}")
    return " ".join(cmd + ["--out", "<new dir>"]), parse(report.read_text(), out)


def parse(text, out):
    holds = set()
    m = re.search(r"^## Rules that hold\n(.+)$", text, re.M)
    if m:
        holds = {r.strip() for r in m.group(1).split(",")}
    breaks = {
        rule: int(steps)
        for rule, steps in re.findall(r"^## (\w+) breaks\nThe shortest path has (\d+) steps?", text, re.M)
    }
    num = lambda pat: int(m.group(1)) if (m := re.search(pat, text)) else None
    chart = out / "chart.mmd"
    return {
        "holds": holds,
        "breaks": breaks,
        "tlc_states": num(r"TLC reached (\d+) states"),
        "chart_states": num(r"The chart draws (\d+) states"),
        "arrows": num(r"and (\d+) arrows"),
        "chart": chart.read_text().strip() if chart.exists() else None,
    }


def cell(side, rule):
    if rule in side["breaks"]:
        return f"breaks ({side['breaks'][rule]} steps)"
    return "holds" if rule in side["holds"] else "not checked"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True, metavar="SPEC.tla:CFG")
    ap.add_argument("--opt", required=True, metavar="SPEC.tla:CFG")
    ap.add_argument("--view")
    ap.add_argument("--out", help="new folder for both runs (default: a temp folder)")
    a = ap.parse_args()
    root = pathlib.Path(a.out) if a.out else pathlib.Path(tempfile.mkdtemp(prefix="protocol-compare-"))
    (bcmd, base), (ocmd, opt) = run(a.base, a.view, root / "base"), run(a.opt, a.view, root / "opt")

    rules = sorted(base["holds"] | set(base["breaks"]) | opt["holds"] | set(opt["breaks"]))
    regressions = [r for r in rules if r in base["holds"] and r in opt["breaks"]]
    fixed = [r for r in rules if r in base["breaks"] and r in opt["holds"]]

    print("### Baseline vs optimized\n")
    print("| Rule | Baseline | Optimized |\n|---|---|---|")
    for r in rules:
        print(f"| `{r}` | {cell(base, r)} | {cell(opt, r)} |")
    print(f"| model states | {base['tlc_states']} | {opt['tlc_states']} |")
    print(f"| chart | {base['chart_states']} states, {base['arrows']} arrows | {opt['chart_states']} states, {opt['arrows']} arrows |")
    print()
    print(f"Fixed by the optimization: {', '.join(fixed) or 'none'}. Broken by it: {', '.join(regressions) or 'none'}.\n")
    for name, side, cmd in (("Baseline", base, bcmd), ("Optimized", opt, ocmd)):
        print(f"#### {name}\n\n`{cmd}`\n")
        if side["chart"]:
            print(f"```mermaid\n{side['chart']}\n```\n")
    return 1 if regressions else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code, file=sys.stderr)
            sys.exit(3)
        raise
