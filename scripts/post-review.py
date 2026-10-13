#!/usr/bin/env python3
"""usage: post-review.py <owner/repo> <pr> <draft.md> <COMMENT|REQUEST_CHANGES|APPROVE>

Posts the draft as one PR review pinned to the head SHA on its `Reviewed head: <sha>` line.
Each `### <path>:<line>` or `### <path>:<start>-<end>` section under a `## Inline` heading
becomes an inline comment on the new side of the diff. A section whose lines are not all in
the diff moves into the body, because GitHub rejects the whole review otherwise.
Refuses when the head moved (exit 3), when this user already reviewed that head (exit 5,
REPOST=1 posts again), or when the draft leaks a local path, an internal ticket key, or a
pattern from the optional machine-local file ~/.cursor/mstack/leak-patterns.txt (exit 6),
or when it has no merge stamp from panel-gate.py that matches its text (exit 8). The
internal `[src: ...]` tags are stripped before posting.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

GH = os.environ.get("GH", "gh")
# Ticket keys as TICKET_KEY in check.py. NDA names stay machine-local, never in this repo.
LOCAL_PATTERNS = os.path.expanduser(os.environ.get("MSTACK_LEAK_PATTERNS", "~/.cursor/mstack/leak-patterns.txt"))
EXTRA = [p.strip() for p in open(LOCAL_PATTERNS) if p.strip() and not p.startswith("#")] if os.path.isfile(LOCAL_PATTERNS) else []
LEAK = re.compile("|".join([r"/home/[A-Za-z0-9_.-]+/", re.escape(os.environ.get("TMPDIR", "/tmp")) + r"/review-pr-", r"\bSILOTIGER-\d+", r"\bROCM-3\d+", *EXTRA]), re.I)
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
SOURCE = re.compile(r"\s*\[src: [^\]]*\]")
ANCHOR = re.compile(r"^### (\S+?):(\d+)(?:-(\d+))?\s*$")


def die(code, msg):
    print(msg, file=sys.stderr)
    sys.exit(code)


def gh(*args):
    r = subprocess.run([GH, *args], capture_output=True, text=True)
    if r.returncode:
        die(1, f"gh {' '.join(args[:3])} failed: {r.stderr.strip()}")
    return r.stdout


def new_side_lines(patch):
    lines, n = set(), 0
    for row in patch.splitlines():
        m = HUNK.match(row)
        if m:
            n = int(m.group(1))
        elif row[:1] in (" ", "+"):
            lines.add(n)
            n += 1
    return lines


def main():
    if len(sys.argv) != 5:
        die(2, __doc__)
    repo, pr, draft, event = sys.argv[1:]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not pr.isdigit() or not os.path.isfile(draft):
        die(2, __doc__)
    if event not in ("COMMENT", "REQUEST_CHANGES", "APPROVE"):
        die(2, "event must be COMMENT, REQUEST_CHANGES, or APPROVE")
    text = open(draft).read()
    m = re.search(r"^Reviewed head: *([0-9a-f]{40})\b", text, re.M)
    if not m:
        die(2, f"{draft} has no 'Reviewed head: <40-hex sha>' line")
    reviewed = m.group(1)
    stamp = draft + ".gate"
    if not os.path.isfile(stamp) or open(stamp).read().strip() != hashlib.sha256(text.encode()).hexdigest():
        die(8, f"{draft} has no merge stamp that matches it: run panel-gate.py merge after the last edit")

    leaks = [f"{n}: {line}" for n, line in enumerate(text.splitlines(), 1) if LEAK.search(line)]
    if leaks:
        die(6, "\n".join(leaks) + "\nthe draft leaks a local path or an internal ticket key. Edit it, then post.")

    live = gh("api", f"repos/{repo}/pulls/{pr}", "--jq", ".head.sha").strip()
    if live != reviewed:
        die(3, f"head moved: reviewed {reviewed}, live {live}. Re-review before posting.")

    me = gh("api", "user", "--jq", ".login").strip()
    if os.environ.get("REPOST") != "1":
        reviews = gh("api", "--paginate", f"repos/{repo}/pulls/{pr}/reviews", "--jq", ".[] | [.user.login, .commit_id] | @tsv")
        if [me, reviewed] in [row.split("\t") for row in reviews.splitlines()]:
            die(5, f"{me} already reviewed {reviewed} on {repo}#{pr}. REPOST=1 to post again.")

    body, *rest = re.split(r"^## Inline\s*$", text, maxsplit=1, flags=re.M)
    inline = rest[0] if rest else ""
    sections = []
    for line in inline.splitlines():
        a = ANCHOR.match(line)
        if a:
            sections.append((a.group(1), int(a.group(2)), int(a.group(3) or a.group(2)), []))
        elif sections:
            sections[-1][3].append(line)
        elif line.strip():
            body += "\n" + line

    files = {}
    for row in gh("api", "--paginate", f"repos/{repo}/pulls/{pr}/files", "--jq", '.[] | [.filename, (.patch // "")] | @json').splitlines():
        name, patch = json.loads(row)
        files[name] = new_side_lines(patch)

    comments, outside = [], []
    for path, start, end, lines in sections:
        note = SOURCE.sub("", "\n".join(lines)).strip()
        if start <= end and path in files and all(n in files[path] for n in range(start, end + 1)):
            c = {"path": path, "line": end, "side": "RIGHT", "body": note}
            if start != end:
                c.update(start_line=start, start_side="RIGHT")
            comments.append(c)
        else:
            outside.append(f"**{path}:{start if start == end else f'{start}-{end}'}** {note}")
    if outside:
        body = body.rstrip() + "\n\n### Outside the diff\n\n" + "\n\n".join(outside)
        print(f"{len(outside)} inline comment(s) are not on diff lines and went into the body", file=sys.stderr)

    payload = {"commit_id": reviewed, "event": event, "body": SOURCE.sub("", body).strip() + "\n", "comments": comments}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
    try:
        print(gh("api", "--method", "POST", f"repos/{repo}/pulls/{pr}/reviews", "--input", f.name, "--jq", ".html_url").strip())
    finally:
        os.unlink(f.name)


main()
