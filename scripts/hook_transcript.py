#!/usr/bin/env python3
"""Read the turn that a stop hook ended, from the chat transcript. Shared by task-lint.py and push-check.py.

  read_messages(path)   [(role, blocks)] for every user and assistant message, via mine-chats.py
  this_turn(messages)   the messages after the last user message
  last_text(turn)       the text of the last assistant message in the turn that has text
  transcript_of(event)  the event's transcript_path. Without one, the path that Cursor keeps for
                        the conversation: ~/.cursor/projects/<slug>/agent-transcripts/<id>/<id>.jsonl

A partial last line is skipped, not an error.
"""

import importlib.util
import os
import re

MINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mine-chats.py")
ID = re.compile(r"[\w-]+")


def _mine_chats():
    spec = importlib.util.spec_from_file_location("mine_chats", MINE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mine = _mine_chats()
text_of = mine.text_of


def read_messages(path):
    return mine.load(path, {"parse_errors": 0, "unknown_line_shapes": 0})


def this_turn(messages):
    last = max((i for i, (role, _) in enumerate(messages) if role == "user"), default=-1)
    return messages[last + 1 :]


def last_text(turn):
    for role, blocks in reversed(turn):
        if role == "assistant":
            text = text_of(blocks)
            if text.strip():
                return text
    return ""


def transcript_of(event):
    path = event.get("transcript_path")
    if path:
        return path
    roots = event.get("workspace_roots") or []
    conversation = str(event.get("conversation_id") or "")
    if not roots or not ID.fullmatch(conversation):
        return None
    slug = os.path.abspath(str(roots[0])).strip("/").replace("/", "-")
    return os.path.join(
        os.path.expanduser("~"), ".cursor", "projects", slug, "agent-transcripts", conversation, conversation + ".jsonl"
    )
