#!/usr/bin/env python3
"""Lint this turn's Task calls against the ateam-mode spawn rules.

  task-lint.py hook          the plugin's stop hook. Reads the stop event on stdin and prints
                             {"followup_message"} naming each violation, or {}.
  task-lint.py <transcript>  prints the same findings. Exits 1 on findings, 0 when there are none,
                             2 on usage or an unreadable transcript.

A chat is linted when it attaches the ateam-mode skill, or when a user message holds an
`ateam-mode: <path>` line (a delegate brief). The turn is every message after the last user
message. A Task is a direct Task call, or a CallDynamicTool call with toolName Task, whose
arguments hold the same fields. The brief of an ateam-agent Task may hold the line itself or
name a file, by absolute path, that holds it. The hook fails open: it prints {} on any error.
"""

import collections
import json
import os
import re
import sys

from hook_transcript import read_messages, text_of, this_turn, transcript_of

ATTACHED = re.compile(r"Skill Name: ateam-mode\b")
ATEAM_LINE = re.compile(r"ateam-mode:[ \t]+(/\S*?SKILL\.md)\b")
POINTER = re.compile(r"(?<![\w./-])(/[^\s`'\"<>()]+?\.md)\b")
WORKER_LINE = re.compile(r"Read \S*worker\.md before anything else\.")
POINTER_MAX = 256 * 1024

Spawn = collections.namedtuple("Spawn", "n description subagent_type model background prompt peers")


def first_line(text):
    return text.lstrip().split("\n", 1)[0]


def brief_has_ateam_line(prompt):
    if ATEAM_LINE.search(prompt):
        return True
    for path in POINTER.findall(prompt):
        try:
            if os.path.getsize(path) <= POINTER_MAX and ATEAM_LINE.search(open(path, encoding="utf-8", errors="replace").read()):
                return True
        except OSError:
            continue
    return False


RULES = [
    (
        "no-model",
        lambda s: not s.model,
        "has no `model`. Set the role's model from the `mstack-models` rule. Omit it only for a role set to `inherit-parent` or `auto`.",
    ),
    (
        "foreground",
        lambda s: not s.background and s.peers > 1,
        "runs in the foreground while other Tasks run in the same message. Set `run_in_background: true`.",
    ),
    (
        "ateam-brief",
        lambda s: s.subagent_type == "ateam-agent" and not brief_has_ateam_line(s.prompt),
        "is an `ateam-agent` brief with no `ateam-mode: <path>` line. Add the absolute path of the ateam-mode `SKILL.md`.",
    ),
    (
        "worker-brief",
        lambda s: s.subagent_type != "ateam-agent" and not WORKER_LINE.match(first_line(s.prompt)),
        "is not an `ateam-agent` brief, and it does not start with `Read <path>/worker.md before anything else.`",
    ),
]


def task_input(block):
    if block.get("type") != "tool_use":
        return None
    inp = block.get("input") if isinstance(block.get("input"), dict) else {}
    if block.get("name") == "Task":
        return inp
    if block.get("name") == "CallDynamicTool" and inp.get("toolName") == "Task":
        args = inp.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = None
        return args if isinstance(args, dict) else {}
    return None


def spawns_of(turn):
    out = []
    for role, blocks in turn:
        if role != "assistant":
            continue
        inputs = [inp for inp in (task_input(b) for b in blocks) if inp is not None]
        for inp in inputs:
            out.append(
                Spawn(
                    len(out) + 1,
                    str(inp.get("description") or ""),
                    str(inp.get("subagent_type") or ""),
                    str(inp.get("model") or "").strip(),
                    str(inp.get("run_in_background")).strip().lower() == "true",
                    str(inp.get("prompt") or ""),
                    len(inputs),
                )
            )
    return out


def ateam_chat(messages):
    for role, blocks in messages:
        if role == "user":
            text = text_of(blocks)
            if ATTACHED.search(text) or ATEAM_LINE.search(text):
                return True
    return False


def violations(messages):
    if not ateam_chat(messages):
        return []
    return [
        (s, rule_id, message)
        for s in spawns_of(this_turn(messages))
        for rule_id, broken, message in RULES
        if broken(s)
    ]


def render(found):
    lines = ["mstack Task lint: a Task in this turn breaks the ateam-mode spawn rules."]
    for s, rule_id, message in found:
        lines.append(f'- Task {s.n} ({s.subagent_type or "generalPurpose"}, "{s.description[:60]}") [{rule_id}] {message}')
    lines.append("A Task that already started keeps its settings. Say so in your reply, and set the fields on the next Task.")
    return "\n".join(lines)


def hook(event):
    if event.get("status") != "completed":
        return {}
    path = transcript_of(event)
    found = violations(read_messages(path)) if path else []
    return {"followup_message": render(found)} if found else {}


def main(argv):
    if argv == ["hook"]:
        try:
            out = hook(json.load(sys.stdin))
        except Exception:
            out = {}
        print(json.dumps(out))
        return 0
    if len(argv) != 1 or argv[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        found = violations(read_messages(argv[0]))
    except OSError as err:
        print(f"cannot read {argv[0]}: {err}", file=sys.stderr)
        return 2
    if not found:
        print("ok: no Task violations this turn")
        return 0
    print(render(found))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
