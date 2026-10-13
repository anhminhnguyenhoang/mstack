#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import time

import yaml

REPO_REMOTES = {"aiter": "ROCm/aiter", "FlyDSL": "ROCm/FlyDSL", "triton": "triton-lang/triton"}
SKILLS_DIRS = (".claude/skills", ".cursor/skills")
TICKET_FILES = ("ticket-raw.md", "ticket-description.md", "ticket-description.txt")
PRUNE = {"node_modules", "__pycache__", "site-packages", "venv", "env", "build", "dist", "target", "_build", "out", "snap", "tmp"}
ROLES = {
    "hardware": ("chip", "gpu", "hbm", "cdna", "mi300", "mi355", "gfx", "bandwidth", "peak", "architecture", "hardware"),
    "method": ("measure", "profil", "diagnos", "benchmark", "method", "workflow", "loop", "trace"),
    "levers": ("lever", "optimi", "tuning", "swizzle", "pipelin", "tile"),
    "failure-modes": ("dead end", "failure", "pitfall", "anti-pattern", "heuristic", "lesson", "mistake"),
    "papers": ("paper", "arxiv", "citation", "published"),
    "dsl": ("dsl", "triton", "flydsl", "mlir", "compiler", "language"),
}
TOPICS = {
    "peaks": re.compile(r"TB/s|TFLOPS|\bpeak\b", re.I),
    "roofline": re.compile(r"roofline", re.I),
    "numerics": re.compile(r"numerics|numerical|\brtol\b|\batol\b", re.I),
}
INDEX_NAME = re.compile(r"^(readme|index|_index|contents|toc)(\.[A-Za-z]+)?$", re.I)
LINK = re.compile(r"\]\(([^)#\s]+)")

ap = argparse.ArgumentParser(description="Read-only search for mstack resources, by signature and never by folder name.")
ap.add_argument("--root", default=os.path.expanduser("~"), help="search root; it is never left")
ap.add_argument("--depth", type=int, default=4)
ap.add_argument("--time-limit", type=float, default=30.0, help="seconds per search")
ap.add_argument("--plugin", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--json", action="store_true")
args = ap.parse_args()
ROOT = os.path.realpath(args.root)
PORTS = os.path.join(args.plugin, "skills/ateam-mode/references/ports.md")


def inside(path):
    real = os.path.realpath(path)
    return real == ROOT or real.startswith(ROOT + os.sep)


def read(path, limit=4096):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def frontmatter(path):
    text = read(path, 2048)
    m = re.match(r"---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", text, re.S)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def git_remotes(checkout):
    urls = []
    for line in read(os.path.join(checkout, ".git", "config"), 65536).splitlines():
        m = re.match(r"\s*url\s*=\s*(\S+)", line)
        if m:
            urls.append(re.sub(r"(?<=://)[^/@]*@", "", m.group(1)))
    return urls


def remote_ends(urls, suffix):
    return any(re.sub(r"\.git$", "", u).rstrip("/").endswith(suffix) for u in urls)


def index_file(directory):
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return None
    for n in names:
        if INDEX_NAME.match(n) and os.path.isfile(os.path.join(directory, n)):
            return n
    return None


def walk(deadline):
    base_depth = ROOT.count(os.sep)
    for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
        if time.time() > deadline:
            yield None
            return
        depth = dirpath.count(os.sep) - base_depth
        git = os.path.join(dirpath, ".git")
        if os.path.isfile(git):
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in PRUNE and inside(os.path.join(dirpath, d)))
        if depth >= args.depth:
            dirnames[:] = []
        yield dirpath, filenames, os.path.isdir(git), dirnames


def skills_valid(directory):
    names = set()
    try:
        entries = os.listdir(directory)
    except OSError:
        return names
    for e in entries:
        p = os.path.join(directory, e, "SKILL.md")
        fm = frontmatter(p) if os.path.isfile(p) else None
        if fm and fm.get("name") and fm.get("description"):
            names.add(e)
    return names


def port_skills():
    text = read(PORTS, 1 << 20)
    names = set()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| Port |"):
            for row in lines[i + 2:]:
                if not row.startswith("|"):
                    break
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                if len(cells) > 2:
                    names.update(re.findall(r"`([^`]+)`", cells[2]))
    return names


def kb_signature(directory, excluded):
    if any(directory == e or directory.startswith(e + os.sep) for e in excluded):
        return None
    if os.path.exists(os.path.join(directory, "plugin.json")) or os.path.exists(os.path.join(directory, "SKILL.md")):
        return None
    root_index = index_file(directory)
    if not root_index:
        return None
    linked = set()
    for target in LINK.findall(read(os.path.join(directory, root_index), 65536)):
        if "://" in target or target.startswith(("/", "#", "mailto:")):
            continue
        first = os.path.normpath(target).split(os.sep)[0]
        if first not in ("", ".", "..") and os.path.isdir(os.path.join(directory, first)):
            linked.add(first)
    folders = {}
    for sub in sorted(linked):
        sub_path = os.path.join(directory, sub)
        if index_file(sub_path) and not os.path.exists(os.path.join(sub_path, "SKILL.md")):
            folders[sub] = index_file(sub_path)
    if len(folders) < 2:
        return None
    notes = 0
    for sub in folders:
        seen = 0
        for dp, dns, fns in os.walk(os.path.join(directory, sub)):
            dns[:] = sorted(d for d in dns if not d.startswith("."))
            if dp[len(directory):].count(os.sep) > 3:
                dns[:] = []
            for n in sorted(fns):
                if n.endswith(".md") and not INDEX_NAME.match(n) and seen < 30:
                    seen += 1
                    fm = frontmatter(os.path.join(dp, n))
                    if fm and fm.get("name") and fm.get("description"):
                        notes += 1
        if notes:
            break
    if not notes:
        return None
    return {"path": directory, "index": root_index, "folders": folders}


def map_roles(kb):
    root_lines = read(os.path.join(kb["path"], kb["index"]), 65536).splitlines()
    candidates = {}
    for sub, idx in kb["folders"].items():
        about = " ".join(line for line in root_lines if re.search(r"\]\(\.?/?" + re.escape(sub) + r"/", line))
        candidates[sub] = (read(os.path.join(kb["path"], sub, idx), 4096) + " " + about).lower()
    mapping, ask = {}, {}
    for role, words in ROLES.items():
        scores = sorted(((sum(c.count(w) for w in words), sub) for sub, c in candidates.items()), reverse=True)
        best = scores[0] if scores else (0, None)
        runner = scores[1][0] if len(scores) > 1 else 0
        if best[0] >= 2 and best[0] >= 1.5 * runner:
            mapping[role] = best[1]
        else:
            ask[role] = [s for sc, s in scores if sc > 0 and sc >= best[0] / 2][:4]
    return mapping, ask


def refs_scan(paths, deadline):
    hits = []
    for base in paths:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in PRUNE]
            if dirpath[len(base):].count(os.sep) >= 3:
                dirnames[:] = []
            for n in filenames:
                if time.time() > deadline:
                    return hits
                if not n.endswith(".md") or n.lower().startswith("readme"):
                    continue
                path = os.path.join(dirpath, n)
                text = read(path, 65536)
                found = {t: len(p.findall(text)) for t, p in TOPICS.items()}
                topics = [t for t, c in found.items() if c >= 2]
                if topics:
                    hits.append({"path": path, "topics": topics, "score": sum(found.values())})
    return sorted(hits, key=lambda h: -h["score"])[:8]


def run_wavescope(path):
    cli = os.path.join(path, "src/cli/att.js")
    try:
        r = subprocess.run(["node", cli], capture_output=True, text=True, timeout=10, cwd=path)
    except (OSError, subprocess.TimeoutExpired):
        return "does not run"
    return "runs" if (r.stdout + r.stderr).strip() and "Cannot find module" not in r.stderr else "does not run"


result = {}
deadline = time.time() + args.time_limit
checkouts, ticket_dirs, wave, kb_cands, timed_out = [], [], [], [], False
domain_paths = []
for item in walk(deadline):
    if item is None:
        timed_out = True
        break
    dirpath, filenames, is_git, subdirs = item
    if is_git:
        urls = git_remotes(dirpath)
        for repo, suffix in REPO_REMOTES.items():
            if remote_ends(urls, suffix):
                checkouts.append({"repo": repo, "path": dirpath, "remote": suffix})
                domain_paths.append(dirpath)
                subdirs[:] = []
        if remote_ends(urls, "/WaveScope"):
            wave.append({"path": dirpath, "signature": "remote ends in /WaveScope"})
    elif os.path.isfile(os.path.join(dirpath, "src/cli/att.js")):
        wave.append({"path": dirpath, "signature": "holds src/cli/att.js"})
    if any(f in filenames for f in TICKET_FILES):
        ticket_dirs.append(dirpath)
    if dirpath.count(os.sep) - ROOT.count(os.sep) <= 3:
        kb_cands.append(dirpath)

domain_paths = sorted(set(domain_paths))
by_repo = {}
for c in checkouts:
    by_repo.setdefault(c["repo"], []).append(c)
result["repos"] = {
    repo: {"status": "found" if len(v) == 1 else "ambiguous", "candidates": [x["path"] for x in v], "signature": "git remote ends in " + v[0]["remote"]}
    for repo, v in by_repo.items()
}

bound = port_skills()
cands = []
env_dir = os.environ.get("MSTACK_SKILLS_DIR")
if env_dir:
    cands.append((os.path.expanduser(env_dir), "$MSTACK_SKILLS_DIR"))
else:
    cands += [(os.path.join(ROOT, d), "Cursor user skills folder") for d in SKILLS_DIRS]
scored = []
for d, why in cands:
    if os.path.isdir(d):
        have = skills_valid(d)
        scored.append({"path": d, "skills": len(have), "ports_resolved": len(have & bound), "signature": why + " with */SKILL.md of valid frontmatter"})
scored = [s for s in scored if s["skills"]]
scored.sort(key=lambda s: -s["ports_resolved"])
if not scored:
    result["skills"] = {"status": "not found"}
elif env_dir or len(scored) == 1 or scored[0]["ports_resolved"] > scored[1]["ports_resolved"]:
    result["skills"] = {"status": "found", **scored[0]}
else:
    result["skills"] = {"status": "ambiguous", "candidates": scored}

excluded = set(domain_paths) | {s["path"] for s in scored}
excluded.add(os.path.realpath(args.plugin))
kbs = [k for k in (kb_signature(d, excluded) for d in sorted(set(kb_cands))) if k]
kbs = [k for k in kbs if not any(o["path"] != k["path"] and k["path"].startswith(o["path"] + os.sep) for o in kbs)]
if not kbs:
    result["kb"] = {"status": "not found"}
else:
    for k in kbs:
        k["remote"] = (git_remotes(k["path"]) or ["none"])[0] if os.path.isdir(os.path.join(k["path"], ".git")) else "none"
        k["roles"], k["roles_to_ask"] = map_roles(k)
        k["signature"] = "index file links to subfolders with their own index files, notes with name and description frontmatter"
    result["kb"] = {"status": "found", **kbs[0]} if len(kbs) == 1 else {"status": "ambiguous", "candidates": kbs}

if not wave:
    result["wavescope"] = {"status": "not found"}
else:
    for w in wave:
        w["cli"] = run_wavescope(w["path"])
    result["wavescope"] = {"status": "found", **wave[0]} if len(wave) == 1 else {"status": "ambiguous", "candidates": wave}

parents = sorted({os.path.dirname(d) for d in ticket_dirs})
if not parents:
    result["tickets"] = {"status": "not found"}
else:
    sig = "folders holding " + " or ".join(TICKET_FILES)
    if len(parents) == 1:
        result["tickets"] = {"status": "found", "root": parents[0], "folders": len(ticket_dirs), "signature": sig}
    else:
        result["tickets"] = {"status": "ambiguous", "candidates": [{"root": p, "folders": sum(os.path.dirname(d) == p for d in ticket_dirs)} for p in parents], "signature": sig}

ref_bases = [os.path.join(p, "docs") for p in domain_paths if os.path.isdir(os.path.join(p, "docs"))]
if result["kb"].get("status") == "found":
    ref_bases.append(result["kb"]["path"])
hits = refs_scan(ref_bases, time.time() + args.time_limit) if ref_bases else []
result["refs"] = {"status": "found" if hits else "not found", "sources": hits, "signature": "markdown that mentions TB/s, TFLOPS, peak, roofline, or numerics at least twice"}
result["_notes"] = {"root": ROOT, "depth": args.depth, "walk_timed_out": timed_out}

if args.json:
    print(json.dumps(result, indent=2))
    sys.exit(0)

home = os.path.expanduser("~")


def short(p):
    return "$HOME" + p[len(home):] if p.startswith(home + os.sep) or p == home else p


for key in ("repos", "skills", "kb", "wavescope", "tickets", "refs"):
    v = result[key]
    if key == "repos":
        if not v:
            print("repos: not found")
        for repo, r in v.items():
            print(f"repos/{repo}: {r['status']}: " + ", ".join(short(c) for c in r["candidates"]) + f" [{r['signature']}]")
        continue
    if v["status"] == "not found":
        print(f"{key}: not found")
    elif v["status"] == "ambiguous":
        print(f"{key}: ambiguous: " + "; ".join(short(c.get("path") or c.get("root")) for c in v["candidates"]))
    elif key == "skills":
        print(f"skills: found: {short(v['path'])} ({v['skills']} skills, {v['ports_resolved']} bound by ports.md) [{v['signature']}]")
    elif key == "kb":
        print(f"kb: found: {short(v['path'])} index={v['index']} remote={v['remote']} [{v['signature']}]")
        for role, folder in v["roles"].items():
            print(f"  role {role}: {folder}")
        for role, opts in v["roles_to_ask"].items():
            print(f"  role {role}: ask ({', '.join(opts) or 'no match'})")
    elif key == "wavescope":
        print(f"wavescope: found: {short(v['path'])} cli={v['cli']} [{v['signature']}]")
    elif key == "tickets":
        print(f"tickets: found: {short(v['root'])} ({v['folders']} ticket folders) [{v['signature']}]")
    elif key == "refs":
        for s in v["sources"]:
            print(f"refs: {short(s['path'])} topics={','.join(s['topics'])}")
if timed_out:
    print("note: the walk hit its time limit. Raise --time-limit, or name a path in step 9.")
