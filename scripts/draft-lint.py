#!/usr/bin/env python3
"""Lint a draft the human posts. Exits 1 on a red check.

  draft-lint.py <draft> [--channel slack|pr-comment|jira|pr-review|pr-body]
  draft-lint.py prune <dir> [--stem STEM] [--yes]
                         keep the newest version of each draft stem and the one the human
                         last approved; list the rest, and delete them only with --yes
  draft-lint.py record   the plugin afterFileEdit hook: note each draft this chat's agent edits
  draft-lint.py hook     the plugin stop hook: lint the drafts this chat's agent edited,
                         once per file version

The channel comes from the file name when --channel is absent:
  slack-draft-*        slack       at most 50 prose words
  pr-comment-draft-*   pr-comment  at most 30 prose words
  comment-draft-*      jira        no total cap
  review-draft-*       pr-review   no total cap
  pr-draft-*, pr-description-draft*   pr-body   no total cap

Every channel fails on a pleasantry, on a sentence longer than 100 words, on a sentence of
6 or more words that the draft repeats, and on a prose term from the optional machine-local
file ~/.cursor/mstack/jargon.txt (one term per line, # starts a comment).
Prose is the text outside fenced code, tables, headings, and the review card's
Reviewed head, Review, Validation, and Perf lines. Inline code counts as one word,
a link as its text, and a [src: ...] tag as nothing.

Every channel also fails with LOCATION on a draft that sits directly in $HOME or in a
non-work root listed in ~/.cursor/mstack/non-work-roots.txt (one path per line, # starts a
comment). A draft in a subfolder of those roots passes.

A draft is <stem>.md (version 1) or <stem>-v<N>.md (version N). prune keeps the highest N of
each stem and the file the human last approved. The approval ledger is <dir>/posted.txt: one
file name per line, in approval order. A deleted draft takes its <draft>.gate stamp with it.
prune exits 0 when nothing is left to prune or after --yes, 1 when it lists candidates
without --yes, and 2 on a usage error.
"""
import argparse
import hashlib
import json
import os
import re
import sys

CAPS = {"slack": 50, "pr-comment": 30, "jira": None, "pr-review": None, "pr-body": None}
NAMES = [
    ("slack-draft-", "slack"),
    ("pr-comment-draft-", "pr-comment"),
    ("review-draft-", "pr-review"),
    ("comment-draft-", "jira"),
    ("pr-draft-", "pr-body"),
    ("pr-description-draft", "pr-body"),
]
SENTENCE_WORDS = 100
REPEAT_WORDS = 6
VERSION = re.compile(r"^(?P<stem>.+?)(?:-v(?P<n>\d+))?\.md$")
SEEN = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(os.environ["HOME"], ".cache"), "mstack", "draft-lint")
CARD = ("Reviewed head:", "Review (", "Validation (", "Perf (")
PLEASANTRY = re.compile(
    r"(?<![\w-])(thanks?|thank you|thx|great (?:work|job|pr|change|catch|stuff)|nice (?:work|job|catch|pr|change)|awesome|"
    r"kudos|cheers|appreciated?|hope (?:this|that) helps|let me know|feel free|happy to help|sorry|just wanted to)(?![\w-])"
    r"|^(?:hi|hey|hello|dear)\b", re.I)


def channel_of(path, override):
    if override:
        if override not in CAPS:
            sys.exit(f"unknown channel `{override}`, expected one of {', '.join(CAPS)}")
        return override
    name = os.path.basename(path)
    for prefix, channel in NAMES:
        if name.startswith(prefix):
            return channel
    sys.exit(f"cannot tell the channel of {name}: pass --channel {'|'.join(CAPS)}")


def prose_lines(text):
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced or not s or s.startswith(("|", "#", "<!--")) or s.startswith(CARD):
            continue
        s = re.sub(r"\[src: [^\]]+\]", "", s)
        s = re.sub(r"`[^`]*`", "CODE", s)
        s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", s)
        s = re.sub(r"[*_]{1,3}", "", s).strip()
        if s:
            yield n, s


def words(s):
    return re.findall(r"[\w][\S]*", s)


def read_list(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [s for s in (line.split("#", 1)[0].strip() for line in f) if s]


def jargon_terms():
    return [(t, re.compile(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])"))
            for t in read_list(os.path.expanduser("~/.cursor/mstack/jargon.txt"))]


def non_work_roots():
    roots = {os.path.realpath(os.path.expanduser("~"))}
    roots.update(os.path.realpath(os.path.expanduser(p))
                 for p in read_list(os.path.expanduser("~/.cursor/mstack/non-work-roots.txt")))
    return roots


def location_errors(path):
    folder = os.path.dirname(os.path.realpath(path))
    if folder not in non_work_roots():
        return []
    return [f"LOCATION {os.path.basename(path)} sits in {folder}, not in a work folder: "
            "move it to its ticket folder or to <work>/<repo>-<N>/"]


def lint(path, channel):
    errs, total = location_errors(path), 0
    jargon = jargon_terms()
    sentences = {}
    for n, line in prose_lines(open(path, encoding="utf-8").read()):
        total += len(words(line))
        m = PLEASANTRY.search(line)
        if m:
            errs.append(f"line {n}: pleasantry `{m.group(0)}`: cut it")
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            k = len(words(sentence))
            if k > SENTENCE_WORDS:
                errs.append(f"line {n}: a sentence of {k} words, the limit is {SENTENCE_WORDS}: split it or drop clauses: {sentence[:70]}...")
            if k >= REPEAT_WORDS:
                sentences.setdefault(" ".join(sentence.lower().split()), []).append((n, sentence.strip()))
        for term, pattern in jargon:
            if pattern.search(line):
                errs.append(f"line {n}: `{term}` is on your jargon list: say it in plain words")
    for hits in sentences.values():
        if len(hits) > 1:
            lines = sorted({n for n, _ in hits})
            shown = hits[0][1][:70] + ("..." if len(hits[0][1]) > 70 else "")
            where = ("lines " if len(lines) > 1 else "line ") + ", ".join(map(str, lines))
            errs.append(f"{where}: the same sentence appears {len(hits)} times, \"{shown}\": say it once")
    cap = CAPS[channel]
    if cap is not None and total > cap:
        errs.append(f"{total} prose words, and a {channel} draft allows at most {cap}")
    return errs, total


def is_draft(path):
    f = os.path.basename(path)
    return f.endswith(".md") and ".posted" not in f and any(f.startswith(pre) for pre, _ in NAMES)


def versions(folder):
    found = {}
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if is_draft(path) and os.path.isfile(path):
            m = VERSION.match(name)
            found.setdefault(m["stem"], []).append((int(m["n"] or 1), path))
    return found


def approved_order(folder):
    names = read_list(os.path.join(folder, "posted.txt"))
    return {os.path.basename(n): i for i, n in enumerate(names)}


def prune_plan(folder, stem=None):
    order = approved_order(folder)
    plans = []
    for name, found in sorted(versions(folder).items()):
        if stem not in (None, name):
            continue
        found.sort()
        top = found[-1][0]
        reasons = {path: [] for _, path in found}
        for n, path in found:
            if n == top:
                reasons[path].append("newest")
        approved = [p for _, p in found if os.path.basename(p) in order]
        if approved:
            reasons[max(approved, key=lambda p: order[os.path.basename(p)])].append("approved")
        prune = [path for _, path in found if not reasons[path]]
        if prune:
            keep = [(path, reasons[path]) for _, path in found if reasons[path]]
            plans.append((name, keep, prune))
    return plans


def prune_cmd(argv):
    ap = argparse.ArgumentParser(prog="draft-lint.py prune",
                                 description="list or delete superseded draft versions")
    ap.add_argument("dir")
    ap.add_argument("--stem", help="prune only this draft stem")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="list only (the default)")
    mode.add_argument("--yes", action="store_true", help="delete the listed drafts and their .gate stamps")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.dir):
        ap.error(f"not a directory: {args.dir}")
    plans = prune_plan(args.dir, args.stem)
    total = sum(len(prune) for _, _, prune in plans)
    if not total:
        return print("nothing to prune")
    for name, keep, prune in plans:
        print(name)
        for path, reasons in keep:
            print(f"  keep   {os.path.basename(path)} ({', '.join(reasons)})")
        for path in prune:
            gate = " (+ .gate)" if os.path.isfile(path + ".gate") else ""
            print(f"  prune  {os.path.basename(path)}{gate}")
    if not args.yes:
        print(f"{total} to prune in {len(plans)} stem(s). Dry run: nothing deleted. Run with --yes to delete.")
        sys.exit(1)
    for _, _, prune in plans:
        for path in prune:
            os.remove(path)
            if os.path.isfile(path + ".gate"):
                os.remove(path + ".gate")
    print(f"deleted {total} draft(s) in {len(plans)} stem(s)")


def state_file(event):
    return os.path.join(SEEN, re.sub(r"\W", "_", str(event.get("conversation_id") or "none")) + ".json")


def load_state(event):
    f = state_file(event)
    return json.load(open(f)) if os.path.isfile(f) else {"edited": [], "seen": {}}


def save_state(event, state):
    os.makedirs(SEEN, exist_ok=True)
    json.dump(state, open(state_file(event), "w"))


def record(event):
    path = event.get("file_path") or ""
    if is_draft(path):
        state = load_state(event)
        if path not in state["edited"]:
            state["edited"].append(path)
            save_state(event, state)


def stop_message(event):
    if event.get("status") != "completed":
        return None
    state = load_state(event)
    report = []
    for p in state["edited"]:
        if not os.path.isfile(p):
            continue
        digest = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if state["seen"].get(p) == digest:
            continue
        state["seen"][p] = digest
        errs, _ = lint(p, channel_of(p, None))
        if errs:
            report += [f"{p}:", *(f"- {e}" for e in errs)]
    save_state(event, state)
    if not report:
        return None
    return "\n".join(["mstack draft lint is red on a draft this chat edited.", *report,
                      "Fix the lines you wrote, then run `draft-lint.py <draft>` until it is green. "
                      "Do not rewrite text the human wrote: name those lines in the reply instead."])


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
    if argv == ["hook"]:
        return hook()
    if argv == ["record"]:
        try:
            record(json.load(sys.stdin))
        except Exception:
            pass
        return print("{}")
    if argv[:1] == ["prune"]:
        return prune_cmd(argv[1:])
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    path = argv[0]
    override = argv[argv.index("--channel") + 1] if "--channel" in argv[1:-1] else None
    if not os.path.isfile(path):
        sys.exit(f"missing {path}")
    channel = channel_of(path, override)
    errs, total = lint(path, channel)
    for e in errs:
        print(f"RED {e}", file=sys.stderr)
    if errs:
        sys.exit(1)
    cap = CAPS[channel]
    print(f"draft lint green: {channel}, {total} prose words{f' of {cap}' if cap else ''}")


if __name__ == "__main__":
    main(sys.argv[1:])
