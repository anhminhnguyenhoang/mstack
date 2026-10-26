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
    "swarm",
]
# Prose-only terms skip code spans, so a `Forge` table name from an old env file can be cited.
RETIRED_TERMS = [
    ("forge", "PR tool", re.compile(r"(?<![\w-])forges?(?![\w-])", re.I), True),
    ("panel", "review group or list role", re.compile(r"(?<![\w-])panels?(?![\w-])", re.I), True),
    ("port", "skill function", re.compile(r"`[a-z]+\.[a-z_.]+` ports?\b|(?<![\w-])ports\.md|\bPORTS\b"), False),
]
RETIRED_PRINCIPLES = [
    "never-block-on-the-human",
    "outcome-oriented-execution",
    "experience-first",
    "type-system-discipline",
    "boundary-discipline",
    "make-operations-idempotent",
    "respect-the-roofline",
    "laziness-protocol",
    "foundational-thinking",
]
SKILL_FUNCTIONS = "skills/ateam-mode/references/skill-functions.md"
NAME_EXEMPT = {SKILL_FUNCTIONS, "skills/setup-mstack/SKILL.md", "scripts/check.py"}
NAME_EXEMPT_DIRS = ("archive/",)
STALE = re.compile(
    r"poteto-mode|poteto-agent|poteto-help|setup-pstack|pstack-models|cursor-team-kit|/deslop|smci355|silotiger-1164-mhc|mi355x-tritoners|fhuizing",
    re.I,
)
TODO = re.compile(r"`TODO`|TODO:")
LEGACY_KB_FOLDERS = ("hardware", "kernel-optimization", "papers", "dsl")
LEGACY_KB_PATH = re.compile(r"(?<![\w./-])(" + "|".join(LEGACY_KB_FOLDERS) + r")/")
KB_SENTENCE = re.compile(r"`kb` resource")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
HOME_PATH = re.compile(r"(?<!\w)~/([^\s`'\")\]>,;|]*)|/home/[A-Za-z0-9_.-]+/")
LOCAL_NAMES = re.compile(r"knowledge-base|KernelForge")
HOME_OK = (".cursor",)
ABS_PATH = re.compile(r"(?:~|(?<![\w.~}:/>-]))/[^\s`'\")\]>,;|]*")
HOME_OK_LINE = "~/Library/Application"
PROBE_FILE = "skills/setup-mstack/SKILL.md"
PROBE_MARK = "(probe)"
TICKET_KEY = re.compile(r"\bSILOTIGER-\d+|\bROCM-3\d+", re.I)
ENV_FILE = "~/.cursor/mstack/env.md"
OPTIONAL_COLUMN = "Optional"
SLOP_EXEMPT = {"skills/unslop/SKILL.md", "skills/technical-writing/SKILL.md"}
SLOP_WORDS = lambda *ws: re.compile(r"(?<![\w-])(" + "|".join(ws) + r")(?![\w-])", re.I)
SLOP = [
    (7, SLOP_WORDS("additionally", "crucial(?:ly)?", "delve[sd]?", "garner(?:s|ed)?", "interplay", "intricate", "pivotal", "showcas(?:e|es|ed|ing)", "tapestry", "testament", "underscor(?:e|es|ed|ing)", "vibrant")),
    (8, SLOP_WORDS("serves as", "serve as", "stands as", "boasts")),
    (13, re.compile("[\u2013\u2014]")),
    (18, re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")),
    (19, re.compile("[\u2018\u2019\u201c\u201d]")),
    (20, SLOP_WORDS("I hope this helps", "let me know if", "great question", "absolutely right", "smoking gun")),
    (31, SLOP_WORDS("utiliz(?:e|es|ed|ing)", "leverag(?:e|es|ed|ing)", "facilitat(?:e|es|ed|ing)", "in the event that")),
]

ap = argparse.ArgumentParser(
    description="mstack consistency checks. The skills dir is $MSTACK_SKILLS_DIR, else the Skills table of ~/.cursor/mstack/env.md. With neither, the skills checks are skipped."
)
ap.add_argument("root", nargs="?", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
mode = ap.add_mutually_exclusive_group()
mode.add_argument("--no-skills", action="store_true", help="skip the checks that read the skills dir")
mode.add_argument("--skills-only", action="store_true", help="run only the skill function and skills-dir checks, and print the Skills table")
ap.add_argument("--no-tests", action="store_true", help="skip tests/test_scripts.sh")
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


def env_text():
    try:
        return open(os.path.expanduser(os.environ.get("MSTACK_ENV") or ENV_FILE), encoding="utf-8").read()
    except OSError:
        return None


def env_kb_paths():
    text = env_text()
    m = re.search(r"^## KB[ \t]*\n(.*?)(?=^## |\Z)", text or "", re.M | re.S)
    if not m:
        return []
    lines = m.group(1).splitlines()
    paths = []
    for i, line in enumerate(lines):
        header = cells(line) if line.startswith("|") else []
        if "Role" in header and "Path inside the KB" in header:
            col = header.index("Path inside the KB")
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                value = cells(row)[col].strip("`").strip() if len(cells(row)) > col else ""
                value = re.sub(r"^(\./)+", "", value).rstrip("/")
                if value and value not in ("not set", ".", "-"):
                    paths.append(value)
    return sorted(set(paths))


def env_skills_dir():
    text = env_text()
    if text is None:
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


def parse_skill_functions():
    text = open(SKILL_FUNCTIONS, encoding="utf-8").read()
    lines = text.splitlines()
    head = next((i for i, line in enumerate(lines) if cells(line)[:5] == ["Skill function", "When", "Skill", OPTIONAL_COLUMN, "Selection rule"]), None)
    if head is None:
        raise ValueError(f"no | Skill function | When | Skill | {OPTIONAL_COLUMN} | Selection rule | table")
    bindings = []
    for line in lines[head + 2:]:
        if not line.startswith("|"):
            break
        row = cells(line)
        functions = re.findall(r"`([^`]+)`", row[0])
        skills = re.findall(r"`([^`]+)`", row[2]) if len(row) > 2 else []
        optional = row[3].strip().lower() if len(row) > 3 else ""
        if len(functions) != 1 or not skills or optional not in ("yes", "no"):
            raise ValueError(f"row needs one skill function, at least one skill, and Optional Yes or No: {line}")
        bindings.append((functions[0], skills, optional == "yes"))
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
            rel = os.path.relpath(os.path.realpath(where), top) if top else ""
            tree = git(top, "rev-parse", f"HEAD:{rel}") if branch == "detached" and top else ""
            if tree and tree == git(top, "rev-parse", f"origin/HEAD:{rel}"):
                branch = "origin/HEAD"
            if top and branch not in ("main", "origin/HEAD"):
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
    bindings, ignored = parse_skill_functions()
except Exception as e:
    fail += 1
    print(f"BAD SKILL FUNCTIONS FILE {SKILL_FUNCTIONS}: {e}")
    bindings, ignored = [], []
function_names = [p for p, _, _ in bindings]
for p in sorted({p for p in function_names if function_names.count(p) > 1}):
    fail += 1
    print(f"SKILL FUNCTION BOUND TWICE {p}")
bound = {s for _, skills, _ in bindings for s in skills}
required_bound = {s for _, skills, optional in bindings if not optional for s in skills}
own = set(os.listdir("skills"))

if not args.no_skills and not skip_skills:
    rows, bad, optional_missing = [], {"missing": 0, "malformed": 0}, 0
    for function, skills, optional in bindings:
        for s in skills:
            status, why, repo, branch, warn = resolve(s)
            skippable = status == "missing" and optional and s not in required_bound
            rows.append((f"`{function}`", f"`{s}`", status, repo, branch, "optional skill function: its step is skipped" if skippable else warn))
            if skippable:
                optional_missing += 1
                print(f"NOTE optional skill missing {function} -> {s}: {why}. The step is skipped with a note.")
            elif status != "ok":
                bad[status] += 1
                print(f"BOUND SKILL {status.upper()} {function} -> {s}: {why}")
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
        print(f"UNBOUND SKILLS (bind each in a skill function, or list it under Ignored in {SKILL_FUNCTIONS}): " + ", ".join(unbound))
    stale_ignored = [s for s in ignored if s not in installed]
    if stale_ignored:
        print(f"IGNORED BUT NOT INSTALLED (remove from Ignored in {SKILL_FUNCTIONS}): " + ", ".join(stale_ignored))
    both = sorted(bound & set(ignored))
    if both:
        print("BOTH BOUND AND IGNORED: " + ", ".join(both))
    fail += len(unbound) + len(stale_ignored) + len(both)

    if args.skills_only:
        print("| Skill function | Skill | Status | Repo | Branch | Warning |")
        print("|---|---|---|---|---|---|")
        for row in rows:
            print("| " + " | ".join(row) + " |")
    summary.append(f"skill functions {len(function_names)} bindings {sum(len(s) for _, s, _ in bindings)} | skills {len(installed)} missing {bad['missing']} optional missing {optional_missing} malformed {bad['malformed']} unbound {len(unbound)}")
else:
    summary.append(f"skill functions {len(function_names)} bindings {sum(len(s) for _, s, _ in bindings)} | skills skipped")

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
                print(f"SKILL NAME OUTSIDE SKILL FUNCTIONS {path}:{n}: {m.group(1)}")
    fail += leaks
    summary.append(f"name leaks {leaks}")

    principles = {os.path.basename(d)[len("principle-"):] for d in glob.glob("skills/principle-*")}
    retired = sorted({n for r in RETIRED_PRINCIPLES for n in (r, r.replace("-", " "))}, key=len, reverse=True)
    retired_pat = re.compile(r"(?<![\w-])(?:principle-)?(" + "|".join(map(re.escape, retired)) + r")(?![\w-])", re.I)
    principle_ref = re.compile(r"(?<![\w-])principle-([a-z0-9-]+)")
    stale_principles = 0
    for path, text in walk(hidden=True):
        if path == "scripts/check.py" or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            hits = {m.group(1).lower() for m in retired_pat.finditer(line)}
            hits |= {m.group(1) for m in principle_ref.finditer(line) if m.group(1).rstrip("-") not in principles and m.group(1) not in ("title", "x")}
            for h in sorted(hits):
                stale_principles += 1
                print(f"STALE PRINCIPLE {path}:{n}: {h}")
    fail += stale_principles
    summary.append(f"stale principles {stale_principles}")

    kb_paths = 0
    repo_suffixes = set()
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in dirnames + filenames:
            parts = os.path.relpath(os.path.join(dirpath, name)).split(os.sep)
            for i in range(len(parts)):
                repo_suffixes.add("/".join(parts[i:]))
                repo_suffixes.add("/".join(parts[i:]) + "/")

    def is_repo_path(token):
        return re.sub(r"^(\.{1,2}/)+", "", token) in repo_suffixes

    env_paths = env_kb_paths()
    env_pats = [(p, re.compile(r"(?<![\w./-])" + re.escape(p) + r"/" + (r"" if "/" not in p else r"|(?<![\w./-])" + re.escape(p) + r"(?![\w/-])"))) for p in env_paths]
    for path, text in walk(hidden=True):
        if path == "scripts/check.py" or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in LEGACY_KB_PATH.finditer(line):
                kb_paths += 1
                print(f"KB FOLDER NAME {path}:{n}: {m.group(1)}/")
            for p, pat in env_pats:
                for m in pat.finditer(line):
                    if is_repo_path(p):
                        continue
                    kb_paths += 1
                    print(f"KB PATH FROM ENV {path}:{n}: {p}")
            for sentence in SENTENCE_END.split(line):
                if not KB_SENTENCE.search(sentence):
                    continue
                for span in CODE_SPAN.findall(sentence):
                    token = span.strip()
                    if not (("/" in token or token.endswith(".md")) and " " not in token):
                        continue
                    if token.startswith(("~/.cursor", "$MSTACK")):
                        continue
                    if is_repo_path(token) or LEGACY_KB_PATH.match(token):
                        continue
                    kb_paths += 1
                    print(f"KB PATH NEAR kb RESOURCE {path}:{n}: {token}")
    fail += kb_paths

    repo_paths = {p for p in repo_suffixes if "/" in p.rstrip("/") and os.path.exists(p)}

    def install_path(token):
        parts = token.rstrip("/").split("/")
        return any("/".join(parts[i:]) in repo_paths for i in range(1, len(parts) - 1))

    local = 0
    for path, text in walk(hidden=True):
        if path == "scripts/check.py" or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if HOME_OK_LINE in line or (path == PROBE_FILE and PROBE_MARK in line):
                continue
            hits = [m.group(0) for m in HOME_PATH.finditer(line) if m.group(1) is None or not m.group(1).startswith(HOME_OK)]
            hits += [m.group(0) for m in ABS_PATH.finditer(line) if install_path(m.group(0)) and m.group(0) not in hits]
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
    summary.append(f"kb paths {kb_paths} | local paths {local} | ticket ids {keys}")

    slop = 0
    for path, text in walk(hidden=True):
        if not path.endswith(".md") or path in SLOP_EXEMPT or path.startswith(NAME_EXEMPT_DIRS):
            continue
        fenced = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            prose = CODE_SPAN.sub("", line)
            for rule, pat in SLOP:
                for m in pat.finditer(prose):
                    slop += 1
                    print(f"SLOP (unslop rule {rule}) {path}:{n}: {m.group(0)}")
    fail += slop
    summary.append(f"slop {slop}")

    terms = 0
    for path, text in walk(hidden=True):
        if path == "scripts/check.py" or path.startswith(NAME_EXEMPT_DIRS):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for old, new, pat, prose_only in RETIRED_TERMS:
                for m in pat.finditer(CODE_SPAN.sub("", line) if prose_only else line):
                    terms += 1
                    print(f"RETIRED TERM {path}:{n}: {m.group(0)} (use {new})")
    fail += terms
    summary.append(f"retired terms {terms}")

if not args.no_tests and not args.skills_only:
    r = subprocess.run(["bash", "tests/test_scripts.sh"], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout + r.stderr, end="")
        fail += 1
    summary.append(f"script tests {'ok' if r.returncode == 0 else 'FAIL'}")

print(" | ".join(summary))
print("RESULT", "PASS" if fail == 0 else f"FAIL ({fail})")
sys.exit(1 if fail else 0)
