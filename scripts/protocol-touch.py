#!/usr/bin/env python3
"""Flag the sync constructs that a git diff adds or removes in kernel code.

  protocol-touch.py [--repo DIR] BASE..HEAD

Reads the added and removed lines of `git diff -U0 BASE..HEAD` in kernel files (.py .cu .hip
.cpp .h .hpp .s .mlir .td). A hit is one line and one kind:

  protocol.check applies:
  kernel.py:12 [barrier] + rocdl.s_barrier()

Exit 2 when a hit exists, 0 with `no sync change` when none does, 1 on error. A line number is
the new file's for an added line and the old file's for a removed line. Advisory: a hit says
run the protocol.check skill function on the change, not that the change is wrong.
"""
import argparse
import re
import subprocess
import sys

KERNEL_EXTS = (".py", ".cu", ".hip", ".cpp", ".h", ".hpp", ".s", ".mlir", ".td")

PATTERNS = {
    "barrier": [r"s_barrier", r"__syncthreads", r"gpu\.barrier", r"rocdl\.barrier", r"barrier\("],
    "wait": [r"s_waitcnt", r"waitcnt"],
    "atomic": [r"atomic_add", r"atomicAdd", r"atomic_cas", r"atomicCAS", r"tl\.atomic_", r"atomic_"],
    "stages": [
        r"num_stages",
        r"NUM_STAGES",
        r"(?i:ping_?pong)",
        r"double_buffer",
        r"num_buffers",
        r"\blds_stage\b",
        r"\b[A-Z_]*STAGES[A-Z_]*\b",
        r"\b[ka]Stages\b",
        r"\bPREFETCH\b",
        r"prefetch_depth",
        r"\bstages\s*=",
    ],
    "lock": [r"flock", r"\.lock\b"],
    "flag": [r"while.*flag", r"volatile"],
}

HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
FILE = re.compile(r"^diff --git a/(.*) b/(.*)$")
MAX_TEXT = 160


class GitError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"protocol-touch: {message}\n")
        sys.exit(1)


def diff_text(repo, rng):
    cmd = ["git", "-c", "core.quotePath=false", "-C", repo, "diff", "--no-color", "--no-ext-diff", "-U0", rng, "--"]
    try:
        proc = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", check=False)
    except OSError as error:
        raise GitError(str(error)) from error
    if proc.returncode:
        raise GitError(proc.stderr.strip() or f"git diff exited {proc.returncode}")
    return proc.stdout


def scan(diff):
    hits = []
    path = None
    in_hunk = False
    old = new = 0
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            match = FILE.match(line)
            path = match.group(2) if match else None
            in_hunk = False
            continue
        match = HUNK.match(line)
        if match:
            old, new = int(match.group(1)), int(match.group(2))
            in_hunk = True
            continue
        if not in_hunk or path is None or not path.endswith(KERNEL_EXTS) or line[:1] not in ("+", "-"):
            continue
        sign, text = line[0], line[1:].strip()
        if sign == "+":
            lineno, new = new, new + 1
        else:
            lineno, old = old, old + 1
        for kind, patterns in PATTERNS.items():
            if any(re.search(p, text) for p in patterns):
                hits.append({"file": path, "line": lineno, "kind": kind, "text": f"{sign} {text[:MAX_TEXT]}"})
    return hits


def main(argv=None):
    ap = Parser(description="Flag the sync constructs that a git diff adds or removes in kernel code.")
    ap.add_argument("--repo", default=".", help="git repo to read (default: the current directory)")
    ap.add_argument("range", metavar="BASE..HEAD")
    args = ap.parse_args(argv)
    if ".." not in args.range:
        ap.error(f"range must be BASE..HEAD, got {args.range}")
    try:
        hits = scan(diff_text(args.repo, args.range))
    except GitError as error:
        print(f"protocol-touch: {error}", file=sys.stderr)
        return 1
    if not hits:
        print("no sync change")
        return 0
    print("protocol.check applies:")
    for h in hits:
        print(f"{h['file']}:{h['line']} [{h['kind']}] {h['text']}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
