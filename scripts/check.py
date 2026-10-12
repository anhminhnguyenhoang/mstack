import argparse
import glob
import json
import os
import re
import subprocess
import sys

import yaml

REMOVED = [
    "flydsl-internal-types-cleanup",
    "check-python-style",
    "jdbba-autoresearch",
    "jdbba-frontier-search",
    "kernel-walkthrough",
]
PORTS = "skills/ateam-mode/references/ports.md"
NAME_EXEMPT = {PORTS, "skills/setup-mstack/SKILL.md", "scripts/check.py"}
NAME_EXEMPT_DIRS = ("archive/",)
STALE = re.compile(
    r"poteto-mode|poteto-agent|poteto-help|setup-pstack|pstack-models|cursor-team-kit|/deslop|smci355|silotiger-1164-mhc|mi355x-tritoners|fhuizing",
    re.I,
)
TODO = re.compile(r"`TODO`|TODO:")
KB_AREAS = ("hardware", "kernel-optimization", "papers", "dsl")
KB_AREA_PATH = re.compile(r"(?<![\w./-])(" + "|".join(KB_AREAS) + r")/([^\s`'\")\]>]*)")
HOME_PATH = re.compile(r"(?<!\w)~/([^\s`'\")\]>,;|]*)|/home/[A-Za-z0-9_.-]+/")
LOCAL_NAMES = re.compile(r"knowledge-base|KernelForge")
HOME_OK = (".cursor",)
HOME_OK_LINE = "~/Library/Application"
PROBE_FILE = "skills/setup-mstack/SKILL.md"
PROBE_MARK = "(probe)"
TICKET_KEY = re.compile(r"\bSILOTIGER-\d+|\bROCM-3\d+", re.I)
ENV_FILE = "~/.cursor/mstack/env.md"

ap = argparse.ArgumentParser(
    description="mstack consistency checks. The skills dir is $MSTACK_SKILLS_DIR, else the Skills table of ~/.cursor/mstack/env.md. With neither, the skills checks are skipped."
)
ap.add_argument("root", nargs="?", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
mode = ap.add_mutually_exclusive_group()
mode.add_argument("--no-skills", action="store_true", help="skip the checks that read the skills dir")
mode.add_argument("--skills-only", action="store_true", help="run only the port and skills-dir checks, and print the Skills table")
args = ap.parse_args()
os.chdir(os.path.abspath(args.root))
home = os.path.expanduser("~")
fail = 0


def walk(hidden):
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = sorted(d for d in dirnames if d != ".git" and (hidden or not d.startswith(".")))
        for name in sorted(filenames):
            if name == ".git" or (not hidden and name.startswith(".")):
                continue
            path = os.path.relpath(os.path.join(dirpath, name))
            try:
                yield path, open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue


def frontmatter(path):
    m = re.match(r"---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", open(path, encoding="utf-8").read(), re.S)
    if not m:
        raise ValueError("no frontmatter block")
    fm = yaml.safe_load(m.group(1))
    if not isinstance(fm, dict) or not fm.get("name") or not fm.get("description"):
        raise ValueError("frontmatter lacks name or description")
    return fm


def cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def env_skills_dir():
    try:
        text = open(os.path.expanduser(ENV_FILE), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(r"^## Skills[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return None
    lines = m.group(1).splitlines()
    for i, line in enumerate(lines):
        if line.startswith("|") and cells(line)[:1] == ["Dir"]:
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                value = cells(row)[0].strip("`").strip()
                return None if value in ("", "not set") else os.path.expanduser(value)
    return None


def parse_ports():
    text = open(PORTS, encoding="utf-8").read()
    lines = text.splitlines()
    head = next((i for i, line in enumerate(lines) if cells(line)[:4] == ["Port", "When", "Skill", "Selection rule"]), None)
    if head is None:
        raise ValueError("no | Port | When | Skill | Selection rule | table")
    bindings = []
    for line in lines[head + 2:]:
        if not line.startswith("|"):
            break
        row = cells(line)
        ports = re.findall(r"`([^`]+)`", row[0])
        skills = re.findall(r"`([^`]+)`", row[2]) if len(row) > 2 else []
        if len(ports) != 1 or not skills:
            raise ValueError(f"row needs one port and at least one skill: {line}")
        bindings.append((ports[0], skills))
    m = re.search(r"^## Ignored[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        raise ValueError("no ## Ignored section")
    return bindings, re.findall(r"^- `([^`]+)`", m.group(1), re.M)


def git(cwd, *cmd):
    r = subprocess.run(["git", "-C", cwd, *cmd], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tilde(path):
    return "~" + path[len(home):] if path.startswith(home + os.sep) else path


skills_dir = os.environ.get("MSTACK_SKILLS_DIR") or env_skills_dir()
skills_dir = os.path.expanduser(skills_dir) if skills_dir else None
skip_skills = skills_dir is None and not args.no_skills
if skip_skills:
    print(f"NOTE skills checks skipped: no skills dir. Set MSTACK_SKILLS_DIR, or run /setup-mstack env to fill the Skills table of {ENV_FILE}.")


def resolve(name):
    own = os.path.join("skills", name)
    if os.path.isdir(own):
        where, repo, branch, warn = own, "mstack", "-", ""
    else:
        where = os.path.join(skills_dir, name)
        repo, branch, warn = "local" if os.path.isdir(where) else "-", "-", ""
        if os.path.islink(where):
            top = git(os.path.realpath(where), "rev-parse", "--show-toplevel")
            repo, branch = (tilde(top), git(top, "branch", "--show-current") or "detached") if top else (tilde(os.path.realpath(where)), "-")
            if top and branch != "main":
                warn = f"{repo} is on {branch}, not main, and the link follows the checked-out branch"
    if not os.path.isdir(where):
        return "missing", "no skill directory", repo, branch, warn
    try:
        frontmatter(os.path.join(where, "SKILL.md"))
    except Exception as e:
        return "malformed", str(e), repo, branch, warn
    return "ok", "", repo, branch, warn


summary = []

if not args.skills_only:
    links = broken = 0
    for f in glob.glob("**/*.md", recursive=True):
        text = open(f).read()
        for m in re.finditer(r"\]\((\.{1,2}/[^)#\s]+|[A-Za-z0-9_\-/]+\.md)(#[^)]*)?\)", text):
            links += 1
            target = os.path.normpath(os.path.join(os.path.dirname(f), m.group(1)))
            if not os.path.exists(target):
                broken += 1
                print(f"BROKEN LINK {f} -> {m.group(1)}")
    fail += broken

    bad_fm = 0
    for f in glob.glob("skills/*/SKILL.md"):
        try:
            frontmatter(f)
        except Exception as e:
            bad_fm += 1
            print(f"BAD FRONTMATTER {f}: {e}")
    fail += bad_fm

    a = json.load(open("plugin.json"))
    b = json.load(open(".cursor-plugin/plugin.json"))
    plugin_ok = a["name"] == b["name"] == "mstack" and a["version"] == b["version"]
    if not plugin_ok:
        fail += 1
        print("PLUGIN.JSON MISMATCH: name or version differs between plugin.json and .cursor-plugin/plugin.json")

    stale, todo = [], []
    for path, text in walk(hidden=False):
        if not path.endswith(".md"):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if os.path.basename(path) != "README.md" and STALE.search(line):
                stale.append(f"{path}:{n}:{line}")
            if not path.startswith(("skills/architect/", "skills/why/")) and TODO.search(line):
                todo.append(f"{path}:{n}:{line}")
    if stale:
        fail += 1
        print("STALE NAMES OR MACHINE FACTS:\n" + "\n".join(stale))
    if todo:
        fail += 1
        print("TODO PLACEHOLDERS:\n" + "\n".join(todo))

    pb_files = glob.glob("skills/ateam-mode/playbooks/*.md")
    summary.append(f"links {links} broken {broken} | SKILL.md {len(glob.glob('skills/*/SKILL.md'))} bad {bad_fm} | plugin.json ok {plugin_ok} | playbook files {len(pb_files)}")

try:
    bindings, ignored = parse_ports()
except Exception as e:
    fail += 1
    print(f"BAD PORTS FILE {PORTS}: {e}")
    bindings, ignored = [], []
port_names = [p for p, _ in bindings]
for p in sorted({p for p in port_names if port_names.count(p) > 1}):
    fail += 1
    print(f"PORT BOUND TWICE {p}")
bound = {s for _, skills in bindings for s in skills}
own = set(os.listdir("skills"))

if not args.no_skills and not skip_skills:
    rows, bad = [], {"missing": 0, "malformed": 0}
    for port, skills in bindings:
        for s in skills:
            status, why, repo, branch, warn = resolve(s)
            rows.append((f"`{port}`", f"`{s}`", status, repo, branch, warn))
            if status != "ok":
                bad[status] += 1
                print(f"BOUND SKILL {status.upper()} {port} -> {s}: {why}")
            if warn:
                print(f"WARN {s}: {warn}")
    fail += bad["missing"] + bad["malformed"]

    if os.path.isdir(skills_dir):
        installed = sorted(e for e in os.listdir(skills_dir) if not e.startswith(".") and (os.path.isdir(os.path.join(skills_dir, e)) or os.path.islink(os.path.join(skills_dir, e))))
    else:
        installed = []
        fail += 1
        print(f"NO SKILLS DIR {skills_dir}: fix MSTACK_SKILLS_DIR or the Skills table of {ENV_FILE}, or run with --no-skills")
    unbound = [s for s in installed if s not in bound and s not in ignored]
    for s in unbound:
        status, why, repo, branch, warn = resolve(s)
        rows.append(("-", f"`{s}`", "unbound", repo, branch, warn))
    if unbound:
        print(f"UNBOUND SKILLS (bind each in a port, or list it under Ignored in {PORTS}): " + ", ".join(unbound))
    stale_ignored = [s for s in ignored if s not in installed]
    if stale_ignored:
        print(f"IGNORED BUT NOT INSTALLED (remove from Ignored in {PORTS}): " + ", ".join(stale_ignored))
    both = sorted(bound & set(ignored))
    if both:
        print("BOTH BOUND AND IGNORED: " + ", ".join(both))
    fail += len(unbound) + len(stale_ignored) + len(both)

    if args.skills_only:
        print("| Port | Skill | Status | Repo | Branch | Warning |")
        print("|---|---|---|---|---|---|")
        for row in rows:
            print("| " + " | ".join(row) + " |")
    summary.append(f"ports {len(port_names)} bindings {sum(len(s) for _, s in bindings)} | skills {len(installed)} missing {bad['missing']} malformed {bad['malformed']} unbound {len(unbound)}")
else:
    summary.append(f"ports {len(port_names)} bindings {sum(len(s) for _, s in bindings)} | skills skipped")

if not args.skills_only:
    names = sorted((bound | set(ignored) | set(REMOVED)) - own, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, names)) + r")(?![\w-])")
    leaks = 0
    for path, text in walk(hidden=True):
        if path in NAME_EXEMPT or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in pattern.finditer(line):
                leaks += 1
                print(f"SKILL NAME OUTSIDE PORTS {path}:{n}: {m.group(1)}")
    fail += leaks
    summary.append(f"name leaks {leaks}")

    deep = 0
    for path, text in walk(hidden=True):
        if path == "scripts/check.py" or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in KB_AREA_PATH.finditer(line):
                rest = m.group(2).rstrip(".,;:")
                if rest not in ("", "README.md"):
                    deep += 1
                    print(f"KB DEEP PATH {path}:{n}: {m.group(1)}/{rest}")
    fail += deep

    local = 0
    for path, text in walk(hidden=True):
        if path == "scripts/check.py" or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if HOME_OK_LINE in line or (path == PROBE_FILE and PROBE_MARK in line):
                continue
            hits = [m.group(0) for m in HOME_PATH.finditer(line) if m.group(1) is None or not m.group(1).startswith(HOME_OK)]
            hits += LOCAL_NAMES.findall(line)
            for hit in hits:
                local += 1
                print(f"LOCAL PATH {path}:{n}: {hit}")
    fail += local

    keys = 0
    for path, text in walk(hidden=True):
        if path == "scripts/check.py" or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in TICKET_KEY.finditer(line):
                keys += 1
                print(f"TICKET ID {path}:{n}: {m.group(0)}")
    fail += keys
    summary.append(f"kb deep paths {deep} | local paths {local} | ticket ids {keys}")

print(" | ".join(summary))
print("RESULT", "PASS" if fail == 0 else f"FAIL ({fail})")
sys.exit(1 if fail else 0)
