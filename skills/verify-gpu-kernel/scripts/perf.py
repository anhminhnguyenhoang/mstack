#!/usr/bin/env python3
"""Median of one perf column over N saved op-test logs.

Reads the markdown summary tables the test printed (the last table that has
COL, in each log), or a CSV file (the `-o` output of op_benchmarks/triton).
Groups rows by the KEY columns. Prints JSON rows.

usage: perf.py --col "hip dq" --key m,n,q_type --regime cold-L2 [--ms]
               [--rate-col "TB/s" | --bytes "m*n*3+m*4" | --flops "2*m*n*k"]
               [--peak 8.0 --peak-source "MI355X spec, HBM"] RUN1.log RUN2.log ...
       perf.py --selftest
--ms:        the column is in milliseconds (triton perf_report); convert to us
--rate-col:  a throughput column in the unit of --peak; adds pct_of_peak (median rate / peak)
--bytes, --flops: a formula over the numeric KEY columns; the rate is the formula
             over us_median, in TB/s or TFLOPS, against --peak in that unit
regime:      cold-L2 | warm | hipGraph, as the feature file states for the entry point
spread_pct:  (max - min) / median over the runs, the same-revision noise floor of the row
"""

import argparse
import csv
import io
import json
import math
import re
import statistics
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
REGIMES = ("cold-L2", "warm", "hipGraph")


def json_tables(text):
    out = []
    for line in ANSI.sub("", text).splitlines():
        if not line.startswith('{"name"'):
            continue
        try:
            rows = json.loads(line).get("rows")
        except ValueError:
            continue
        if rows:
            head = list(dict.fromkeys(k for r in rows for k in r))
            out.append((head, [["" if r.get(k) is None else str(r.get(k)) for k in head] for r in rows]))
    return out


def tables(text):
    head = text.lstrip()
    if not head.startswith(("|", "{")) and "\n|" not in text and "," in head.split("\n", 1)[0]:
        rows = list(csv.reader(io.StringIO(text)))
        return [([c.strip() for c in rows[0]], [[c.strip() for c in r] for r in rows[1:] if r])]
    out, cur = [], []
    for line in ANSI.sub("", text).splitlines() + [""]:
        if line.startswith("|"):
            cur.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif cur:
            if len(cur) > 2:
                header, _sep, *body = cur
                out.append((header, body))
            cur = []
    return out + json_tables(text)


def measured(row, col, factor=1.0):
    try:
        v = float(row[col]) * factor
    except (KeyError, ValueError):
        return None
    return None if math.isnan(v) else v


def work(expr, shape):
    names = {}
    for k, v in shape.items():
        try:
            names[k] = float(v)
        except ValueError:
            pass
    try:
        return float(eval(expr, {"__builtins__": {}}, names))
    except NameError as e:
        raise SystemExit(f"--bytes/--flops: {e}; KEY columns are {list(shape)}")


def collect(texts, col, keys, regime="cold-L2", factor=1.0, rate_col=None, peak=None, peak_source=None,
            work_expr=None, work_unit=None):
    acc, rates = {}, {}
    for text in texts:
        hits = [t for t in tables(text) if col in t[0] and all(k in t[0] for k in keys)]
        if not hits:
            raise SystemExit(f"no table with column {col!r} and key columns {keys}")
        head, rows = hits[-1]
        if rate_col and rate_col not in head:
            raise SystemExit(f"no column {rate_col!r} beside {col!r}")
        for r in rows:
            row = dict(zip(head, r))
            v = measured(row, col, factor)
            if v is None:
                continue
            k = tuple(row[c] for c in keys)
            acc.setdefault(k, []).append(v)
            rate = measured(row, rate_col) if rate_col else None
            if rate is not None:
                rates.setdefault(k, []).append(rate)
    out = []
    for k, v in acc.items():
        med = statistics.median(v)
        row = {
            "shape": dict(zip(keys, k)),
            "side": col,
            "us_median": med,
            "runs": len(v),
            "min_us": min(v),
            "max_us": max(v),
            "spread_pct": round(100 * (max(v) - min(v)) / med, 3) if med else None,
            "regime": regime,
        }
        if rate_col and k in rates:
            row["pct_of_peak"] = round(100 * statistics.median(rates[k]) / peak, 2)
            row["peak_source"] = f"{rate_col} / {peak} ({peak_source})"
        elif work_expr and med:
            rate = work(work_expr, row["shape"]) / (med * 1e-6) / 1e12
            row["rate"] = round(rate, 4)
            row["pct_of_peak"] = round(100 * rate / peak, 2)
            row["peak_source"] = f"{work_unit} {work_expr} / us_median vs {peak} ({peak_source})"
        out.append(row)
    return out


def selftest():
    log = "x\n| m | hip dq |\n|---:|---:|\n| 1 | {a} |\n| 2 | nan |\n"
    rows = collect([log.format(a=a) for a in (3.0, 1.0, 2.0)], "hip dq", ["m"])
    assert rows == [
        {
            "shape": {"m": "1"},
            "side": "hip dq",
            "us_median": 2.0,
            "runs": 3,
            "min_us": 1.0,
            "max_us": 3.0,
            "spread_pct": 100.0,
            "regime": "cold-L2",
        }
    ], rows
    rows = collect(["T,ms\n4,0.012\n4,nan\n", "T,ms\n4,0.010\n"], "ms", ["T"], factor=1000.0)
    assert rows[0]["runs"] == 2 and abs(rows[0]["us_median"] - 11.0) < 1e-9, rows
    rated = "| m | us | TB/s |\n|---|---|---|\n| 1 | {a} | {r} |\n"
    rows = collect([rated.format(a=10, r=4.0), rated.format(a=11, r=6.0)], "us", ["m"], "warm",
                   rate_col="TB/s", peak=8.0, peak_source="spec")
    assert rows[0]["pct_of_peak"] == 62.5 and "spec" in rows[0]["peak_source"], rows
    try:
        collect(["| m | us |\n|---|---|\n| 1 | 2 |\n"], "us", ["m"], rate_col="TB/s", peak=8.0)
        raise AssertionError("missing rate column must stop")
    except SystemExit:
        pass
    rows = collect(["| m | n | us |\n|---|---|---|\n| 1024 | 1024 | 1.0 |\n"], "us", ["m", "n"],
                   work_expr="m*n*4", work_unit="TB/s", peak=8.0, peak_source="spec")
    assert abs(rows[0]["rate"] - 4.194304) < 1e-4 and rows[0]["pct_of_peak"] == 52.43, rows
    js = '{"name": "mhc_pre summary", "rows": [{"m": 1024, "hip_us": %s, "TB/s": 4.0}]}\n'
    rows = collect([js % 10.0, js % 12.0], "hip_us", ["m"], rate_col="TB/s", peak=8.0, peak_source="spec")
    assert rows[0]["us_median"] == 11.0 and rows[0]["pct_of_peak"] == 50.0, rows
    two = "| B | us |\n|---|---|\n| 1 | 5 |\n\nx\n| seq | us |\n|---|---|\n| 9 | 7 |\n"
    assert collect([two], "us", ["B"])[0]["us_median"] == 5.0
    print("selftest OK")


def main(argv):
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    p = argparse.ArgumentParser(usage=__doc__)
    p.add_argument("--col", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--regime", required=True, choices=REGIMES)
    p.add_argument("--ms", action="store_true")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--rate-col")
    g.add_argument("--bytes")
    g.add_argument("--flops")
    p.add_argument("--peak", type=float)
    p.add_argument("--peak-source")
    p.add_argument("logs", nargs="+")
    a = p.parse_args(argv[1:])
    if (a.rate_col or a.bytes or a.flops) and not (a.peak and a.peak_source):
        p.error("--rate-col, --bytes, and --flops need --peak and --peak-source")
    texts = []
    for path in a.logs:
        with open(path, errors="replace") as f:
            texts.append(f.read())
    rows = collect(texts, a.col, a.key.split(","), a.regime, 1000.0 if a.ms else 1.0,
                   a.rate_col, a.peak, a.peak_source, a.bytes or a.flops,
                   "TB/s" if a.bytes else "TFLOPS" if a.flops else None)
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
