#!/usr/bin/env python3
"""Guard the shell commands an agent runs. Block or warn on the ones the rules forbid.

  shell-guard.py hook         the plugin's beforeShellExecution hook. Reads {"command", "cwd"}
                              on stdin and prints {"permission"}, plus "user_message" and
                              "agent_message" when a rule matches. Always exits 0.
  shell-guard.py login [DIR]  prints the login that the PR tool table of env.md names for the
                              origin of DIR. Exits 3 when no row names one. gh-as.sh uses it.

RULES is the one table. deny blocks the command, ask waits for the user, and warn runs the
command and shows the message. The strongest match wins, and every message is sent.

A legit exception names the rule on the command line, as a shell comment:
  # shell-guard: allow <name>[, <name>]

The hook fails open and never exits 2, because Cursor reads exit 2 as a block.
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys

ENV_FILE = os.environ.get("MSTACK_ENV") or os.path.expanduser("~/.cursor/mstack/env.md")
GH_AS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gh-as.sh")
PERMISSION = {"deny": "deny", "ask": "ask", "warn": "allow"}
RANK = {"warn": 1, "ask": 2, "deny": 3}
ALLOW = re.compile(r"#\s*shell-guard:\s*allow\s+([\w ,-]+)")
REPO_FLAG = re.compile(r"(?:^|\s)(?:-R|--repo)[=\s]+([\w.-]+/[\w.-]+)")
REMOTE = re.compile(r"^(?:[a-z+]+://)?(?:[^@/]+@)?([^:/]+)[:/]([^/]+)/")
HOST_ORGS = re.compile(r"^\s*([^\s(]+)\s*\((.*)\)\s*$")
LOGIN = re.compile(r"gh auth token -u\s+([\w.-]+)|signed in as\s+\**([\w.-]+)")
START = r"(?:^|[;&|(`'\"\n])\s*(?:sudo\s+)?"

SLEEP = re.compile(
    START
    + r"sleep\s+(?:(?:[3-9]\d|\d{3,})(?:\.\d+)?[smhd]?|\d+(?:\.\d+)?[mhd])(?![\w.])"
)
KILL = re.compile(
    START + r"(?:pkill|killall)\b"
    r"|\bkill\s+(?:-\S+\s+)?(?:\$\(|`)\s*pgrep\b"
    r"|\bpgrep\b[^;&|\n]*\|\s*xargs\s+(?:-\S+\s+)*kill\b"
)
DOCKER = re.compile(
    r"\bdocker\s+(?:compose\s+)?exec\b(?![^;&|\n]*\s(?:-u\S*|--user\b))"
)
GH = re.compile(r"\A(?![\s\S]*\bGH_TOKEN=)[\s\S]*?" + START + r"gh\s+(?:pr|api)\b")

Rule = collections.namedtuple("Rule", "name pattern action message context")


def cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def pr_routes():
    try:
        with open(ENV_FILE, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    routes = []
    for i, line in enumerate(lines):
        head = cells(line) if line.startswith("|") else []
        if head[:1] != ["Host or org"]:
            continue
        col = next((j for j, c in enumerate(head) if c.startswith("PR path")), None)
        if col is None:
            continue
        for row in lines[i + 2 :]:
            if not row.startswith("|"):
                break
            c = cells(row)
            if len(c) <= col:
                continue
            host_orgs, login = HOST_ORGS.match(c[0]), LOGIN.search(c[col])
            if host_orgs and login:
                orgs = frozenset(
                    o.split(":")[0].strip().lower()
                    for o in host_orgs.group(2).split(",")
                    if o.strip()
                )
                routes.append(
                    (host_orgs.group(1).lower(), orgs, login.group(1) or login.group(2))
                )
    return routes


def parse_remote(url):
    m = REMOTE.match(url.strip() + "/")
    return (m.group(1).lower(), m.group(2).lower()) if m else None


def origin(directory):
    if not directory:
        return ""
    try:
        r = subprocess.run(
            ["git", "-C", directory, "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_login(url):
    host_owner = parse_remote(url)
    if host_owner is None:
        return None
    host, owner = host_owner
    for row_host, orgs, login in pr_routes():
        if row_host == host and owner in orgs:
            return login
    return None


def gh_context(command, cwd):
    repo = REPO_FLAG.search(command)
    login = (
        repo_login(f"https://github.com/{repo.group(1)}")
        if repo
        else repo_login(origin(cwd))
    )
    return {"login": login, "gh_as": GH_AS} if login else None


RULES = [
    Rule(
        "sleep",
        SLEEP,
        "deny",
        "Do not wait with a sleep of 30 seconds or more. To wait on a background shell job, call AwaitShell.",
        None,
    ),
    Rule(
        "pattern-kill",
        KILL,
        "deny",
        "Do not kill by name pattern. A pattern can match a process that another run or user owns. Kill only a PID this run started, by its PID.",
        None,
    ),
    Rule(
        "docker-user",
        DOCKER,
        "warn",
        "This docker exec has no -u, so it runs as root. Root writes root-owned files into mounts, and those block git worktree remove. Name the host uid with -u $(id -u), per the bench.run skill function.",
        None,
    ),
    Rule(
        "gh-login",
        GH,
        "warn",
        "The PR tool row in env.md names the login {login} for this repo. A bare gh call uses the active account, not that login. Run gh through {gh_as} -C <repo dir> -- <gh args>.",
        gh_context,
    ),
]


def decide(command, cwd):
    allowed = {
        n for m in ALLOW.finditer(command) for n in re.split(r"[,\s]+", m.group(1)) if n
    }
    hits = []
    for rule in RULES:
        if rule.name in allowed or not rule.pattern.search(command):
            continue
        values = rule.context(command, cwd) if rule.context else {}
        if values is None:
            continue
        note = f"{rule.message.format(**values)} To allow this once, add `# shell-guard: allow {rule.name}` to the command."
        hits.append((rule.action, note))
    if not hits:
        return {"permission": "allow"}
    worst = max(hits, key=lambda h: RANK[h[0]])[0]
    text = " ".join(note for _, note in hits)
    return {
        "permission": PERMISSION[worst],
        "user_message": text,
        "agent_message": text,
    }


def main(argv):
    ap = argparse.ArgumentParser(
        description="Guard shell commands. See the module docstring."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("hook")
    login = sub.add_parser("login")
    login.add_argument("dir", nargs="?", default=".")
    args = ap.parse_args(argv)
    if args.cmd == "hook":
        try:
            event = json.load(sys.stdin)
            out = decide(str(event.get("command") or ""), str(event.get("cwd") or ""))
        except Exception:
            out = {"permission": "allow"}
        print(json.dumps(out))
        return 0
    name = repo_login(origin(args.dir))
    if name is None:
        print(
            f"no PR tool row in {ENV_FILE} names a login for {args.dir}",
            file=sys.stderr,
        )
        return 3
    print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
