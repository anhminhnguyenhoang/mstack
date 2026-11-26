#!/usr/bin/env python3
"""Print the state of background subagent lanes from their transcript files.

  lanes.py [--quiet-min N] PATH...

PATH is a subagent .jsonl file or a directory of them. A quiet lane is a fact to check,
not a verdict: a lane blocked on a long benchmark or build writes nothing while it runs.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

HEADER = ["lane", "state", "quiet_min", "lines", "brief"]
TAG_BLOCK = re.compile(r"<(?!user_query>)(\w+)>.*?</\1>", re.DOTALL)
USER_QUERY_TAG = re.compile(r"</?user_query>")
BRIEF_CHARS = 60


def parse(line):
    try:
        return json.loads(line)
    except ValueError:
        return None


def first_user_text(lines):
    for line in lines:
        record = parse(line)
        if isinstance(record, dict) and record.get("role") == "user":
            content = (record.get("message") or {}).get("content") or []
            if isinstance(content, str):
                return content
            return "".join(b.get("text") or "" for b in content if isinstance(b, dict))
    return ""


def brief_of(text):
    text = USER_QUERY_TAG.sub("", TAG_BLOCK.sub("", text))
    return " ".join(text.split())[:BRIEF_CHARS]


def state_of(lines, quiet_min, threshold):
    last = parse(lines[-1]) if lines else None
    if isinstance(last, dict) and last.get("type") == "turn_ended":
        return "done" if last.get("status") == "success" else "error"
    # A line still being written does not parse, so that lane is not finished.
    return "running" if quiet_min < threshold else "quiet"


def lane_files(paths):
    found = []
    for p in paths:
        if os.path.isdir(p):
            found += [os.path.join(p, n) for n in os.listdir(p) if n.endswith(".jsonl")]
        else:
            found.append(p)
    return list(dict.fromkeys(found))


def row(mtime, path, now, threshold):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [line for line in f if line.strip()]
    quiet = max(0.0, (now - mtime) / 60)
    return [
        Path(path).stem[:8],
        state_of(lines, quiet, threshold),
        f"{quiet:.1f}",
        str(len(lines)),
        brief_of(first_user_text(lines)),
    ]


def main(argv):
    ap = argparse.ArgumentParser(description="Print the state of background subagent lanes.")
    ap.add_argument("--quiet-min", type=float, default=10.0, metavar="N",
                    help="minutes without a write before a lane is quiet (default 10)")
    ap.add_argument("paths", nargs="+", metavar="PATH",
                    help="a subagent .jsonl file or a directory of them")
    args = ap.parse_args(argv)
    missing = [p for p in args.paths if not os.path.exists(p)]
    if missing:
        print("lanes.py: no such path: " + ", ".join(missing), file=sys.stderr)
        return 2
    now = time.time()
    try:
        files = sorted((os.path.getmtime(f), f) for f in lane_files(args.paths))
        rows = [row(mtime, f, now, args.quiet_min) for mtime, f in files]
    except OSError as e:
        print(f"lanes.py: {e}", file=sys.stderr)
        return 2
    print("\t".join(HEADER))
    for r in rows:
        print("\t".join(r))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
