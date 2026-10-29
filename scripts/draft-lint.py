#!/usr/bin/env python3
"""Lint a draft the human posts. Exits 1 on a red check.

  draft-lint.py <draft> [--channel slack|pr-comment|jira|pr-review|pr-body]
  draft-lint.py record   the plugin afterFileEdit hook: note each draft this chat's agent edits
  draft-lint.py hook     the plugin stop hook: lint the drafts this chat's agent edited,
                         once per file version

The channel comes from the file name when --channel is absent:
  slack-draft-*        slack       at most 50 prose words
  pr-comment-draft-*   pr-comment  at most 30 prose words
  comment-draft-*      jira        no total cap
  review-draft-*       pr-review   no total cap
  pr-draft-*, pr-description-draft*   pr-body   no total cap

Every channel fails on a pleasantry and on a sentence longer than 100 words.
Prose is the text outside fenced code, tables, headings, and the review card's
Reviewed head, Review, Validation, and Perf lines. Inline code counts as one word,
a link as its text, and a [src: ...] tag as nothing.
"""
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


def lint(path, channel):
    errs, total = [], 0
    for n, line in prose_lines(open(path, encoding="utf-8").read()):
        total += len(words(line))
        m = PLEASANTRY.search(line)
        if m:
            errs.append(f"line {n}: pleasantry `{m.group(0)}`: cut it")
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            k = len(words(sentence))
            if k > SENTENCE_WORDS:
                errs.append(f"line {n}: a sentence of {k} words, the limit is {SENTENCE_WORDS}: split it or drop clauses: {sentence[:70]}...")
    cap = CAPS[channel]
    if cap is not None and total > cap:
        errs.append(f"{total} prose words, and a {channel} draft allows at most {cap}")
    return errs, total


def is_draft(path):
    f = os.path.basename(path)
    return f.endswith(".md") and ".posted" not in f and any(f.startswith(pre) for pre, _ in NAMES)


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
