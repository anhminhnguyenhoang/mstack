#!/usr/bin/env python3
"""List the upstream pstack commits that mstack has not reviewed.

  pstack-updates.py [--json] [--no-fetch] [--remote URL] [--clone DIR] [--mstack DIR] [--since SHA]

The reviewed commit is the Reviewed through row of UPSTREAM.md. The name map and the decided
commits come from its ## Name map and ## Decisions sections. The clone lives under
$XDG_CACHE_HOME (default: the home cache dir) at mstack/pstack-upstream, and it is fetched on
each run unless --no-fetch. Each changed file under pstack/ maps to its mstack path, with one
status:
  manifest                  a plugin.json version file
  shipped                   the mapped file exists in mstack
  missing-in-shipped-skill  the mapped file lies in a skill folder that exists in mstack
  absent                    none of these
A commit is review when one of its files is shipped or missing-in-shipped-skill, otherwise
skip-candidate.

Exit 0 when up to date or every new commit is decided. Exit 2 when a new commit is undecided.
Exit 1 on error. --json prints the commits as a JSON list. --since reviews from SHA instead.
"""

import argparse
import json
import os
import re
import subprocess
import sys

DEFAULT_REMOTE = "https://github.com/cursor/plugins"
UPSTREAM_DIR = "pstack/"
MANIFEST = "pstack/.cursor-plugin/plugin.json"
MANIFESTS = {"plugin.json", ".cursor-plugin/plugin.json"}
REVIEW_STATUSES = {"shipped", "missing-in-shipped-skill"}
SHA = r"[0-9a-f]{7,40}"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def die(message):
    print(f"pstack-updates: {message}", file=sys.stderr)
    sys.exit(1)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(1, f"{self.prog}: error: {message}\n")


def git(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        die(f"git {args[0]} failed: {r.stderr.strip()}")
    return r


def cache_dir():
    return os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")


def section(text, title):
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        die(f"UPSTREAM.md has no ## {title} section")
    return m.group(1)


def read_upstream_md(path):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        die(f"cannot read {path}: {e.strerror}")
    names = {}
    for line in section(text, "Name map").splitlines():
        tokens = re.findall(r"`([^`]+)`", line)
        if line.startswith("|") and len(tokens) == 2:
            names[tokens[0]] = tokens[1]
    decided = []
    for line in section(text, "Decisions").splitlines():
        if line.startswith("|"):
            decided += re.findall(rf"`({SHA})`", line.split("|")[1])
    m = re.search(rf"^\|\s*Reviewed through\s*\|\s*`({SHA})`", text, re.M)
    return (m.group(1) if m else None), names, decided


def ensure_clone(clone, remote, fetch):
    if not os.path.isdir(clone):
        os.makedirs(os.path.dirname(os.path.abspath(clone)), exist_ok=True)
        git("clone", "--quiet", "--filter=blob:none", "--no-checkout", remote, clone)
    elif git("remote", "get-url", "origin", cwd=clone).stdout.strip() != remote:
        git("remote", "set-url", "origin", remote, cwd=clone)
    if fetch:
        git("fetch", "--quiet", "origin", cwd=clone)
        git("remote", "set-head", "origin", "--auto", cwd=clone)


def resolve(clone, rev):
    r = git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", cwd=clone, check=False)
    if r.returncode:
        die(f"no commit {rev} in {clone}")
    return r.stdout.strip()


def default_ref(clone):
    r = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=clone, check=False)
    if r.returncode:
        die(f"{clone} has no origin/HEAD")
    return r.stdout.strip()


def new_commits(clone, rng):
    out = git("log", "--reverse", "--format=%H%x1f%cs%x1f%s", rng, "--", UPSTREAM_DIR, cwd=clone).stdout
    return [line.split("\x1f", 2) for line in out.splitlines() if line]


def changed_files(clone, sha):
    out = git("diff-tree", "--no-commit-id", "-r", "-z", "--name-status", "-M", "-m", "--first-parent",
              "--root", sha, "--", UPSTREAM_DIR, cwd=clone).stdout
    fields = [f for f in out.split("\0") if f]
    paths, i = [], 0
    while i < len(fields):
        width = 2 if fields[i][0] in "RC" else 1
        paths.append(fields[i + width])
        i += width + 1
    return paths


def version_at(clone, rev):
    r = git("show", f"{rev}:{MANIFEST}", cwd=clone, check=False)
    if r.returncode:
        return None
    try:
        return json.loads(r.stdout).get("version")
    except (ValueError, AttributeError):
        return None


def map_path(upstream, names):
    segments = []
    for seg in upstream[len(UPSTREAM_DIR):].split("/"):
        for old, new in sorted(names.items(), key=lambda kv: -len(kv[0])):
            seg = seg.replace(old, new)
        segments.append(seg)
    return "/".join(segments)


def status_of(mstack, mapped):
    if mapped in MANIFESTS:
        return "manifest"
    if os.path.exists(os.path.join(mstack, mapped)):
        return "shipped"
    parts = mapped.split("/")
    if len(parts) > 2 and parts[0] == "skills" and os.path.isdir(os.path.join(mstack, "skills", parts[1])):
        return "missing-in-shipped-skill"
    return "absent"


def commit_record(clone, mstack, names, decided, sha, date, subject):
    files = []
    for path in changed_files(clone, sha):
        mapped = map_path(path, names)
        files.append({"upstream": path, "mstack": mapped, "status": status_of(mstack, mapped)})
    verdict = "review" if any(f["status"] in REVIEW_STATUSES for f in files) else "skip-candidate"
    return {
        "sha": sha,
        "subject": subject,
        "date": date,
        "version": version_at(clone, sha),
        "decided": any(sha.startswith(d) for d in decided),
        "verdict": verdict,
        "files": files,
    }


def report(clone, base, tip, commits):
    review = sum(c["verdict"] == "review" for c in commits)
    print(f"pstack {version_at(clone, base) or base[:7]} -> {version_at(clone, tip) or tip[:7]} : "
          f"{len(commits)} new commits ({review} review, {len(commits) - review} skip-candidate)")
    print(f"clone: {clone}")
    print()
    print("| sha | version | verdict | decided | subject | mstack files touched |")
    print("|---|---|---|---|---|---|")
    for c in commits:
        subject = c["subject"].replace("|", "\\|")
        touched = sum(f["status"] in REVIEW_STATUSES for f in c["files"])
        print(f"| {c['sha'][:7]} | {c['version'] or '-'} | {c['verdict']} | "
              f"{'yes' if c['decided'] else 'no'} | {subject} | {touched} |")
    for c in commits:
        if c["verdict"] != "review":
            continue
        print()
        print(f"**{c['sha'][:7]}** ({c['version'] or '-'})")
        for f in c["files"]:
            if f["status"] in REVIEW_STATUSES:
                print(f"- `{f['mstack']}` {f['status']} (from `{f['upstream']}`)")


def main():
    ap = Parser(description="List the upstream pstack commits after the reviewed one, with their mstack files.")
    ap.add_argument("--json", action="store_true", help="print the commits as a JSON list")
    ap.add_argument("--no-fetch", action="store_true", help="use the clone as it is")
    ap.add_argument("--remote", default=DEFAULT_REMOTE, help="upstream URL (default: %(default)s)")
    ap.add_argument("--clone", default=os.path.join(cache_dir(), "mstack", "pstack-upstream"), help="blobless clone directory")
    ap.add_argument("--mstack", default=ROOT, help="mstack checkout (default: this repo)")
    ap.add_argument("--since", metavar="SHA", help="review from SHA instead of the Reviewed through row")
    args = ap.parse_args()

    reviewed, names, decided = read_upstream_md(os.path.join(args.mstack, "UPSTREAM.md"))
    if not (args.since or reviewed):
        die("UPSTREAM.md has no Reviewed through row, and no --since was given")
    ensure_clone(args.clone, args.remote, fetch=not args.no_fetch)
    tip = resolve(args.clone, default_ref(args.clone))
    base = resolve(args.clone, args.since or reviewed)
    commits = [commit_record(args.clone, args.mstack, names, decided, sha, date, subject)
               for sha, date, subject in new_commits(args.clone, f"{base}..{tip}")]

    if args.json:
        print(json.dumps(commits, indent=2))
    elif not commits:
        print(f"pstack up to date at {base[:7]}")
    else:
        report(args.clone, base, tip, commits)
    return 2 if any(not c["decided"] for c in commits) else 0


if __name__ == "__main__":
    sys.exit(main())
