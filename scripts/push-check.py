#!/usr/bin/env python3
"""Check that a commit the last message reports as pushed, or on a PR, is on that remote.

  push-check.py hook                   the plugin's stop hook. Reads the stop event on stdin and prints
                                       {"followup_message"} naming each claim the remote does not back,
                                       or {}.
  push-check.py <transcript> [DIR...]  prints the same findings. Exits 1 on findings, 0 when there are
                                       none, 2 on usage or an unreadable transcript. DIR is a workspace
                                       root, default the working directory.

A claim is a sentence of the turn's last assistant message that names a commit SHA and says that the
commit is pushed, is on a PR, or sits in a PR URL. A sentence that says the commit is not pushed makes
no claim. A commit is looked up in each git checkout under a root or one of its direct children, the
most recently changed first. A push claim passes when a head of the origin remote holds the commit. A PR
claim passes when the PR head, read through gh-as.sh, holds it. A check that cannot run (offline, no gh
login, a remote head or PR head that is not in the local clone, no checkout holds the commit) is skipped,
so the hook fails open. Checks stop after 8 seconds.
"""

import collections
import functools
import json
import os
import re
import subprocess
import sys
import time

from hook_transcript import last_text, read_messages, this_turn, transcript_of

HERE = os.path.dirname(os.path.abspath(__file__))
GH_AS = os.path.join(HERE, "gh-as.sh")
BUDGET = 8.0
CLAIM = re.compile(r"\bpushed\b|\bpushes to\b|\bon (?:the |this |my )?PRs?\b|\bPR\s*#\d+|/pull/\d+", re.I)
NEGATED = re.compile(
    r"\bunpushed\b|\b(?:not|never)\b[^.;]{0,40}?\b(?:pushed|on (?:the )?PR|in (?:the )?PR)\b|n't\b[^.;]{0,30}?\bpush",
    re.I,
)
SHA = re.compile(r"(?<![\w/.-])([0-9a-f]{7,40})(?![\w-])")
PR_REF = re.compile(r"(?:github\.com/([\w.-]+/[\w.-]+))?/pull/(\d+)|\bPR\s*#(\d+)")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
Claim = collections.namedtuple("Claim", "sha pr text")
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0")
ENV.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes -o ConnectTimeout=4")
_end = 0.0


class OutOfTime(Exception):
    pass


def run(args, cwd=None, stdin=""):
    limit = min(5.0, _end - time.monotonic())
    if limit <= 0:
        raise OutOfTime()
    try:
        return subprocess.run(
            args, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=limit, env=ENV, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def mtime(path):
    try:
        return os.stat(path).st_mtime
    except OSError:
        return 0.0


def pr_of(sentence):
    m = PR_REF.search(sentence)
    return (m.group(1), m.group(2) or m.group(3)) if m else None


def claims_of(text):
    out = []
    for sentence in SENTENCE.split(text):
        if not CLAIM.search(sentence) or NEGATED.search(sentence):
            continue
        for sha in dict.fromkeys(SHA.findall(sentence)):
            out.append(Claim(sha, pr_of(sentence), sentence.strip()))
    return out


def checkouts(roots):
    seen, found = set(), []
    for root in roots:
        root = os.path.abspath(str(root))
        try:
            with os.scandir(root) as entries:
                kids = [e.path for e in entries if e.is_dir(follow_symlinks=False) and not e.name.startswith(".")]
        except OSError:
            kids = []
        kids.sort(key=mtime, reverse=True)
        for d in [root, *kids]:
            real = os.path.realpath(d)
            if real not in seen and os.path.exists(os.path.join(d, ".git")):
                seen.add(real)
                found.append(d)
    return found


def commits_in(repo, names):
    if not names:
        return {}
    r = run(["git", "-C", repo, "cat-file", "--batch-check=%(objectname) %(objecttype)"], stdin="\n".join(names) + "\n")
    if r is None or r.returncode != 0:
        return {}
    out = {}
    for name, line in zip(names, r.stdout.splitlines()):
        parts = line.split()
        if len(parts) == 2 and parts[1] == "commit":
            out[name] = parts[0]
    return out


def locate(shas, repos):
    found = {}
    for repo in repos:
        todo = [s for s in shas if s not in found]
        if not todo:
            break
        for name, full in commits_in(repo, todo).items():
            found[name] = (repo, full)
    return found


def is_ancestor(repo, sha, head):
    r = run(["git", "-C", repo, "merge-base", "--is-ancestor", sha, head])
    if r is None or r.returncode not in (0, 1):
        return None
    return r.returncode == 0


@functools.lru_cache(maxsize=None)
def origin_heads(repo):
    listing = run(["git", "-C", repo, "ls-remote", "--heads", "origin"])
    if listing is None or listing.returncode != 0:
        return None
    return tuple(sorted({line.split()[0] for line in listing.stdout.splitlines() if line.strip()}))


def pushed_to_origin(repo, sha):
    heads = origin_heads(repo)
    if heads is None:
        return None
    if any(h.startswith(sha) for h in heads):
        return True
    local = commits_in(repo, heads)
    verdicts = [is_ancestor(repo, sha, h) for h in local.values()]
    if True in verdicts:
        return True
    return False if len(local) == len(heads) else None


def pr_head(repo, pr):
    slug, number = pr
    args = ["bash", GH_AS, "-C", repo, "--", "pr", "view", number] + (["--repo", slug] if slug else [])
    r = run(args + ["--json", "headRefOid", "--jq", ".headRefOid"], cwd=repo)
    head = r.stdout.strip() if r is not None and r.returncode == 0 else ""
    return head if re.fullmatch(r"[0-9a-f]{40}", head) else None


def on_pr(repo, sha, pr):
    head = pr_head(repo, pr)
    if head is None:
        return None, None
    if head.startswith(sha):
        return True, head
    if head not in commits_in(repo, [head]):
        return None, head
    return is_ancestor(repo, sha, head), head


def findings(text, roots):
    global _end
    _end = time.monotonic() + BUDGET
    claims = claims_of(text)
    out, seen = [], set()
    try:
        located = locate(sorted({c.sha for c in claims}), checkouts(roots)) if claims else {}
        for c in claims:
            if c.sha not in located:
                continue
            repo, full = located[c.sha]
            if c.pr:
                verdict, head = on_pr(repo, full, c.pr)
                where = f"PR #{c.pr[1]} head {head[:7]}" if head else ""
            else:
                verdict, where = pushed_to_origin(repo, full), "any origin branch"
            if verdict is False and (full, where) not in seen:
                seen.add((full, where))
                out.append((c, where))
    except OutOfTime:
        pass
    return out


def render(found):
    lines = ["mstack push check: a commit your last message reports as pushed is not on that remote."]
    for claim, where in found:
        lines.append(f'- {claim.sha[:7]} ("{claim.text[:120]}"): not on {where}.')
    lines.append("Push the commit, or correct the claim in your reply. Then check it with `git ls-remote` or the PR head.")
    return "\n".join(lines)


def hook(event):
    if event.get("status") != "completed":
        return {}
    path = transcript_of(event)
    if not path:
        return {}
    roots = event.get("workspace_roots") or [os.getcwd()]
    found = findings(last_text(this_turn(read_messages(path))), roots)
    return {"followup_message": render(found)} if found else {}


def main(argv):
    if argv == ["hook"]:
        try:
            out = hook(json.load(sys.stdin))
        except Exception:
            out = {}
        print(json.dumps(out))
        return 0
    if not argv or argv[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        turn = this_turn(read_messages(argv[0]))
    except OSError as err:
        print(f"cannot read {argv[0]}: {err}", file=sys.stderr)
        return 2
    found = findings(last_text(turn), argv[1:] or [os.getcwd()])
    if not found:
        print("ok: no unbacked push claims in the last message")
        return 0
    print(render(found))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
