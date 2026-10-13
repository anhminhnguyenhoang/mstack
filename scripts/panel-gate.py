#!/usr/bin/env python3
"""Gates for the panel steps of the PR review playbook. Every command exits 1 on a red gate.

  panel-gate.py prompt        <WORK> <LABEL>          write the blind reviewer prompt
  panel-gate.py record        <WORK> <LABEL> < reply  record a reviewer's blind findings
  panel-gate.py refute-prompt <WORK> <LABEL>          write the independent-reader prompt
  panel-gate.py record-refute <WORK> <LABEL> < reply  record its verdicts as independent.txt
  panel-gate.py merge         <WORK> <DRAFT> [--no-panel <reason>]
                                                      check the merged draft, then stamp it

The blind prompt holds only the PR diff, the PR's title and body, and the interrogate
rubric, never the card. A reply counts only when it echoes the nonce of the prompt the
script wrote, so a reviewer that never received that prompt cannot be recorded. The
refute prompt is written only after that reviewer's blind findings are recorded. merge
requires each panel finding on the draft or dropped with a reason, a source tag on each
draft finding, the card's Validation and Perf lines unchanged, and the pr.review skill's
own independent gate green. post-review.py posts only a draft whose stamp matches it.
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERROGATE = os.path.join(ROOT, "skills", "interrogate", "references")
PORTS = os.path.join(ROOT, "skills", "ateam-mode", "references", "ports.md")
SKILLS = os.environ.get("MSTACK_SKILLS_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "skills")
FINDING = re.compile(r"^(🔴|⚠️|📝)")
SOURCE = re.compile(r"\[src: ([^\]]+)\]")
LABEL = re.compile(r"[A-Z]")


def red(*msgs):
    for m in msgs:
        print(f"RED {m}", file=sys.stderr)
    sys.exit(1)


def read(path):
    if not os.path.isfile(path):
        red(f"missing {path}")
    return open(path, encoding="utf-8").read()


def panel(work, *parts):
    os.makedirs(os.path.join(work, "panel"), exist_ok=True)
    return os.path.join(work, "panel", *parts)


def nonce_of(work, name):
    return read(panel(work, name + ".nonce")).strip()


def check_nonce(work, name, reply):
    first = next((l for l in reply.splitlines() if l.strip()), "")
    if first.strip() != f"nonce: {nonce_of(work, name)}":
        red(f"reply's first line is not the nonce of {name}.prompt: the reviewer did not get the script's prompt")


def write_prompt(work, name, text):
    nonce = secrets.token_hex(8)
    open(panel(work, name + ".nonce"), "w").write(nonce + "\n")
    path = panel(work, name + ".prompt")
    open(path, "w", encoding="utf-8").write(text + f"\n\nStart your reply with the line `nonce: {nonce}`.\n")
    print(path)


def card_findings(work):
    return [l for l in read(os.path.join(work, "card.md")).splitlines() if FINDING.match(l)]


def blind_prompt(work, label):
    meta = json.loads(read(os.path.join(work, "pr_meta.json")))
    template = read(os.path.join(INTERROGATE, "reviewer-prompt.md")).split("\n---\n", 1)[1]
    fill = {
        "{INTENT}": f"{meta.get('title', '')}\n\n{meta.get('body') or ''}".strip().replace("\n", "\n> "),
        "{DIFF_OR_FILES}": "```diff\n" + read(os.path.join(work, "pr.diff")) + "\n```",
        "{RUBRIC_CONTENTS}": read(os.path.join(INTERROGATE, "rubric.md")),
        "{CODE_QUALITY_CONTENTS}": read(os.path.join(INTERROGATE, "code-quality-review.md")),
    }
    for k, v in fill.items():
        template = template.replace(k, v)
    write_prompt(work, label, template.strip())


def record(work, label):
    reply = sys.stdin.read()
    check_nonce(work, label, reply)
    found = re.findall(r"^### (\d+)\. \[(critical|warning|nit)\] (.+)$", reply, re.M | re.I)
    if not found and "no findings" not in reply.lower():
        red("no `### <n>. [severity] title` findings and no `no findings`")
    open(panel(work, label + ".md"), "w", encoding="utf-8").write(reply)
    open(panel(work, label + ".ids"), "w").write("".join(f"{label}{n}\t{sev}\t{title}\n" for n, sev, title in found))
    print(f"recorded {len(found)} finding(s) from reviewer {label}")


def refute_prompt(work, label):
    if not os.path.isfile(panel(work, label + ".ids")):
        red(f"reviewer {label} has no recorded blind findings: run its blind review first, so the card cannot anchor it")
    findings = card_findings(work)
    if not findings:
        red("card.md has no findings to refute")
    target = open(os.path.join(work, "merge_target.txt"), encoding="utf-8").read() if os.path.isfile(os.path.join(work, "merge_target.txt")) else "unavailable"
    lines = "\n".join(f"{i}. {f}" for i, f in enumerate(findings, 1))
    write_prompt(work, label + ".refute", f"""You are the independent reader of a PR review card. Every finding below is false until you defend it from the code. Open the files it names on the base tree and the PR head, and try to kill it.

Base tree:
{target}

Findings:
{lines}

Reply with exactly one line per finding, in this order, each `SURVIVED -- <what you opened and what it said>` or `KILLED -- <what you opened and what it said>`.""")


def record_refute(work, label):
    reply = sys.stdin.read()
    check_nonce(work, label + ".refute", reply)
    verdicts = [l.strip() for l in reply.splitlines() if re.match(r"^\s*(SURVIVED|KILLED) -- .{10,}", l)]
    n = len(card_findings(work))
    if len(verdicts) != n:
        red(f"{len(verdicts)} verdict line(s) for {n} card finding(s)")
    open(os.path.join(work, "independent.txt"), "w", encoding="utf-8").write("\n".join(verdicts) + "\n")
    open(panel(work, "reader"), "w").write(label + "\n")
    print(f"independent.txt: {n} verdict(s) from reviewer {label}")


def merge(work, draft, no_panel):
    errs = []
    labels = sorted(f[:-4] for f in os.listdir(panel(work)) if f.endswith(".ids") and LABEL.fullmatch(f[:-4]))
    if no_panel:
        if len(no_panel) < 20:
            errs.append("--no-panel needs a reason of 20 characters or more")
        if not os.path.isfile(os.path.join(work, "independent.txt")):
            errs.append("no panel and no independent.txt: another reader must refute the card")
    else:
        if not os.path.isfile(panel(work, "reader")):
            errs.append("independent.txt was not recorded from a panel reviewer: run `prompt`, `record`, `refute-prompt`, "
                        "and `record-refute`, or pass --no-panel <reason>")

    ids = {}
    for label in labels:
        for row in open(panel(work, label + ".ids"), encoding="utf-8"):
            fid, _, title = row.rstrip("\n").split("\t", 2)
            ids[fid] = title
    dropped = {}
    if os.path.isfile(panel(work, "dispositions.txt")):
        for row in open(panel(work, "dispositions.txt"), encoding="utf-8"):
            m = re.match(r"^(\w+) DROPPED -- (.+)$", row.strip())
            if m and len(m.group(2)) >= 20:
                dropped[m.group(1)] = m.group(2)
            elif row.strip():
                errs.append(f"dispositions.txt: `{row.strip()}` is not `<id> DROPPED -- <reason of 20+ characters>`")

    text = read(draft)
    body = re.split(r"^## Inline\s*$", text, maxsplit=1, flags=re.M)[0]
    findings = [l for l in body.splitlines() if FINDING.match(l)]
    if len(findings) > 5:
        errs.append(f"{len(findings)} findings on the draft; the card allows at most 5")
    cited = set()
    for f in findings:
        m = SOURCE.search(f)
        if not m:
            errs.append(f"finding has no `[src: card|panel:<id>|convention:<repo>]` tag: {f[:80]}")
            continue
        for src in (s.strip() for s in m.group(1).split(",")):
            if src.startswith("panel:"):
                if src[6:] not in ids:
                    errs.append(f"`{src}` names no recorded panel finding")
                cited.add(src[6:])
            elif src != "card" and not src.startswith("convention:"):
                errs.append(f"unknown source `{src}`")
    for fid, title in ids.items():
        if fid not in cited and fid not in dropped:
            errs.append(f"panel finding {fid} ({title}) is neither on the draft nor dropped with a reason in panel/dispositions.txt")

    card = read(os.path.join(work, "card.md")).splitlines()
    for key in ("Validation (", "Perf ("):
        want = [l for l in card if l.startswith(key)]
        got = [l for l in text.splitlines() if l.startswith(key)]
        if want != got:
            errs.append(f"the draft's `{key}...` line differs from the card's; the panel adds judgment, never evidence")

    skill = re.search(r"^\| `pr\.review` \|[^|]*\| `([^`]*)`", read(PORTS), re.M).group(1)
    gate = os.path.join(SKILLS, skill, "triage.py")
    r = subprocess.run([gate, "independent", os.path.join(work, "independent.txt"), os.path.join(work, "card.md")], capture_output=True, text=True) if os.path.isfile(gate) else None
    if r is None:
        errs.append(f"cannot run the pr.review skill's independent gate: no {gate}")
    elif r.returncode:
        errs.append("the pr.review skill's independent gate is red:\n" + (r.stdout + r.stderr).strip())

    if errs:
        red(*errs)
    open(draft + ".gate", "w").write(hashlib.sha256(text.encode()).hexdigest() + "\n")
    print(f"merge gate green: {len(findings)} finding(s), {len(ids)} panel finding(s) accounted for. Stamped {draft}.gate")


def main():
    a = sys.argv[1:]
    cmds = {"prompt": blind_prompt, "record": record, "refute-prompt": refute_prompt, "record-refute": record_refute}
    if len(a) == 3 and a[0] in cmds and LABEL.fullmatch(a[2]):
        cmds[a[0]](a[1], a[2])
    elif len(a) in (3, 5) and a[0] == "merge" and (len(a) == 3 or a[3] == "--no-panel"):
        merge(a[1], a[2], a[4] if len(a) == 5 else None)
    else:
        red("usage:\n" + __doc__)


main()
