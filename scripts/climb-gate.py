#!/usr/bin/env python3
"""Harness lock and stop gate for the Kernel hillclimb playbook. check exits 1 on a red gate.

  climb-gate.py freeze <TICKET> <ROOT> <FILE>...   hash the harness files into TICKET/harness.lock
                                                   and turn the stop hook on for this chat
  climb-gate.py check  <TICKET>                    re-hash them in ROOT and in every worktree
                                                   of ROOT's repo whose HEAD descends from B
  climb-gate.py best   <TICKET> <WORKTREE>         the worktree of S*, which the stop gate checks
                                                   instead of B
  climb-gate.py pause  <TICKET> <REASON>           let the next stop pass without proof
  climb-gate.py done   <TICKET>                    turn the stop hook off for this chat
  climb-gate.py hook                               the plugin's stop hook, the event on stdin

FILE is relative to ROOT. When ROOT is in a git checkout, B is its HEAD at freeze, and a
file that B tracks counts as changed when a descendant worktree lacks it. The hook acts
only for the chat that ran freeze (CURSOR_CONVERSATION_ID) and only on a completed stop.
It sends the turn back when the harness changed, or when the best worktree (S*, else B)
has no TICKET/bench_*.json with correctness passed at its clean HEAD. It prints {} on any
error, so a broken lock never blocks an unrelated chat.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

CLIMBS = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(os.environ["HOME"], ".cache"), "mstack", "climbs")
CONV = re.compile(r"^[\w-]+$")


def red(*msgs):
    for m in msgs:
        print(f"RED {m}", file=sys.stderr)
    sys.exit(1)


def git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def lock_file(ticket):
    return os.path.join(ticket, "harness.lock")


def registration(conv):
    return os.path.join(CLIMBS, conv) if conv and CONV.match(conv) else None


def freeze(ticket, root, files):
    root = os.path.abspath(root)
    if not files:
        red("give at least one FILE")
    missing = [f for f in files if not os.path.isfile(os.path.join(root, f))]
    if missing:
        red(*(f"no file {os.path.join(root, f)}" for f in missing))
    top = git(root, "rev-parse", "--show-toplevel")
    rels = [os.path.relpath(os.path.join(root, f), top) for f in files] if top else files
    top = top or root
    lock = {"root": top, "base": git(top, "rev-parse", "HEAD"), "files": {r: digest(os.path.join(top, r)) for r in rels}}
    os.makedirs(ticket, exist_ok=True)
    with open(lock_file(ticket), "w") as f:
        json.dump(lock, f, indent=1)
    reg = registration(os.environ.get("CURSOR_CONVERSATION_ID"))
    if reg:
        os.makedirs(CLIMBS, exist_ok=True)
        with open(reg, "w") as f:
            f.write(os.path.abspath(ticket))
    else:
        print("NOTE stop hook off: no CURSOR_CONVERSATION_ID in this shell. Run check before each keep.")
    print(f"frozen {len(rels)} files at {lock['base'] or top}")


def worktrees(lock):
    root, base = lock["root"], lock["base"]
    if not base:
        return [root]
    listing = git(root, "worktree", "list", "--porcelain") or ""
    trees = [l[len("worktree "):] for l in listing.splitlines() if l.startswith("worktree ")]
    keep = [root]
    for w in trees:
        if os.path.isdir(w) and not os.path.samefile(w, root) and git(w, "merge-base", "--is-ancestor", base, "HEAD") is not None:
            keep.append(w)
    return keep


def changed(lock):
    bad = []
    for w in worktrees(lock):
        for rel, want in lock["files"].items():
            path = os.path.join(w, rel)
            if os.path.isfile(path):
                if digest(path) != want:
                    bad.append(path)
            elif w == lock["root"] or (lock["base"] and git(w, "cat-file", "-e", f"{lock['base']}:{rel}") is not None):
                bad.append(f"{path} (missing)")
    return bad


def load(ticket):
    with open(lock_file(ticket)) as f:
        return json.load(f)


def pause_file(ticket):
    return os.path.join(ticket, "harness.pause")


def best(ticket, worktree):
    if not os.path.isfile(lock_file(ticket)):
        red(f"no {lock_file(ticket)}: run freeze first")
    head = git(worktree, "rev-parse", "HEAD")
    if not head:
        red(f"{worktree} is not a git worktree")
    lock = load(ticket)
    lock["best"] = os.path.abspath(worktree)
    with open(lock_file(ticket), "w") as f:
        json.dump(lock, f, indent=1)
    print(f"stop gate checks {lock['best']}")


def pause(ticket, reason):
    if not reason.strip():
        red("give a reason")
    with open(pause_file(ticket), "w") as f:
        f.write(reason)
    print("the next stop passes without proof")


def proven(ticket, head):
    for path in glob.glob(os.path.join(ticket, "bench_*.json")):
        try:
            with open(path) as f:
                art = json.load(f)
            if art["correctness"]["passed"] is True and any(
                len(r.get("sha") or "") >= 7 and head.startswith(r["sha"]) and r.get("dirty") is False for r in art["repos"]
            ):
                return True
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
    return False


def proof_message(ticket, lock):
    target = lock.get("best") or (lock["root"] if lock["base"] else None)
    head = target and git(target, "rev-parse", "HEAD")
    if not head:
        return None
    dirty = git(target, "status", "--porcelain", "--untracked-files=no")
    if not dirty and proven(ticket, head):
        return None
    me = os.path.abspath(__file__)
    what = "S*" if lock.get("best") else "B"
    state = "has uncommitted changes" if dirty else f"has no bench_*.json with correctness passed at {head[:12]}"
    return "\n".join([
        f"mstack stop gate: {what} in {target} {state}, in {ticket}.",
        "Commit it and measure it through the bench.run skill function before you end the turn.",
        f'To stop on purpose first, such as NO_GPU or a question for the human, log the reason in decision.tsv, run `python3 {me} pause {ticket} "<reason>"`, and end the turn.',
    ])


def check(ticket):
    if not os.path.isfile(lock_file(ticket)):
        red(f"no {lock_file(ticket)}: run freeze first")
    lock = load(ticket)
    bad = changed(lock)
    if bad:
        red(*(f"changed {p}" for p in bad))
    print(f"ok {len(lock['files'])} files in {len(worktrees(lock))} worktrees")


def done(ticket):
    reg = registration(os.environ.get("CURSOR_CONVERSATION_ID"))
    if reg and os.path.isfile(reg) and open(reg).read() == os.path.abspath(ticket):
        os.remove(reg)
    print("stop hook off")


def stop_message(event):
    reg = registration(event.get("conversation_id"))
    if event.get("status") != "completed" or not reg or not os.path.isfile(reg):
        return None
    ticket = open(reg).read()
    if not os.path.isfile(lock_file(ticket)):
        os.remove(reg)
        return None
    lock = load(ticket)
    bad = changed(lock)
    if not bad:
        if os.path.isfile(pause_file(ticket)):
            os.remove(pause_file(ticket))
            return None
        return proof_message(ticket, lock)
    restore = f"git -C <worktree> checkout {lock['base']} -- <file>" if lock["base"] else "your frozen copy"
    return "\n".join([
        f"mstack harness lock ({lock_file(ticket)}): the frozen harness changed.",
        *(f"- {p}" for p in bad),
        f"Restore each file from B ({restore}). A lever measured on a changed harness is class `broken`.",
        "If the harness must change, log the reason in decision.tsv, run freeze again, and re-measure B and every lever on it.",
    ])


def hook():
    out = {}
    try:
        msg = stop_message(json.load(sys.stdin))
        if msg:
            out["followup_message"] = msg
    except Exception:
        pass
    print(json.dumps(out))


def main(argv):
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "freeze" and len(args) >= 2:
        freeze(args[0], args[1], args[2:])
    elif cmd == "check" and len(args) == 1:
        check(args[0])
    elif cmd == "best" and len(args) == 2:
        best(args[0], args[1])
    elif cmd == "pause" and len(args) == 2:
        pause(args[0], args[1])
    elif cmd == "done" and len(args) == 1:
        done(args[0])
    elif cmd == "hook" and not args:
        hook()
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
