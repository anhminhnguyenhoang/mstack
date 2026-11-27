#!/usr/bin/env python3
"""Point a new chat at earlier chats that opened with the same prompt. Stdlib only.

  repeat-prompt.py hook

This is the plugin's beforeSubmitPrompt hook. It reads the hook JSON on stdin and prints one
JSON object. It acts on the first prompt of a conversation only. If an earlier chat in the
workspace opened with a near-identical prompt, the object adds additional_context. That text
names the chats and suggests /recall or /ketchup. Otherwise the object is {"continue": true}.
The hook never blocks a prompt. An error prints the same object.

An earlier chat counts when its transcript was last written within 30 days. Prompts compare as
lowercase words, using difflib's ratio over the word sequences. A ratio of THRESHOLD or more is
a match. A prompt under MIN_CHARS characters, after normalization, never matches, so greetings
and one-line questions do not pair up across unrelated chats.

Exit codes: 0 in hook mode, always. 1 on a bad command line.
"""

import difflib
import importlib.util
import json
import os
import re
import sys
import time

WINDOW_S = 30 * 86400
MIN_CHARS = 20
THRESHOLD = 0.95
MAX_MATCHES = 5
DEADLINE_S = 3.0
CONTINUE = '{"continue": true}'


def load_mine_chats():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mine-chats.py')
    spec = importlib.util.spec_from_file_location('mine_chats', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def transcripts_dir(workspace_root):
    """The agent-transcripts folder of a workspace. Cursor names the project folder after the path, / as -."""
    slug = workspace_root.strip('/').replace('/', '-')
    return os.path.join(os.path.expanduser('~'), '.cursor', 'projects', slug, 'agent-transcripts')


def words(text):
    return re.findall(r'\w+', text.lower())


def long_enough(tokens):
    return len(' '.join(tokens)) >= MIN_CHARS


def first_prompt(mc, path):
    stats = {'parse_errors': 0, 'unknown_line_shapes': 0}
    for role, blocks in mc.iter_messages(path, stats):
        if role == 'user':
            msg = mc.classify(mc.text_of(blocks))
            if msg.kind == mc.TYPED and msg.text:
                return msg.text
    return ''


def find_matches(mc, prompt, root, exclude, now):
    want = words(prompt)
    if not long_enough(want):
        return []
    recent = []
    for cid, path in mc.chat_files(root).items():
        mtime = os.path.getmtime(path)
        if cid != exclude and now - mtime <= WINDOW_S:
            recent.append((mtime, cid, path))
    deadline = time.monotonic() + DEADLINE_S
    hits = []
    for mtime, cid, path in sorted(recent, reverse=True):
        if time.monotonic() > deadline:
            break
        score = difflib.SequenceMatcher(None, want, words(first_prompt(mc, path)), autojunk=False).ratio()
        if score >= THRESHOLD:
            hits.append((score, mtime, cid))
    return sorted(hits, reverse=True)[:MAX_MATCHES]


def context_for(matches):
    lines = [f'- {cid} (last written {time.strftime("%Y-%m-%d", time.localtime(mtime))})'
             for _, mtime, cid in matches]
    return '\n'.join([
        'Earlier chats in this workspace opened with a near-identical prompt:',
        *lines,
        'They may already hold the context this prompt would rebuild. Tell the user about them in one line. '
        'Offer /recall <id> to rebuild one chat, or /ketchup in that chat to see what changed since the user last wrote there.',
    ])


def claim_first_prompt(conversation_id):
    """True only for the first call of a conversation: an exclusive create of its marker file."""
    cache = os.environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache')
    folder = os.path.join(cache, 'mstack', 'repeat-prompt')
    os.makedirs(folder, exist_ok=True)
    try:
        with open(os.path.join(folder, re.sub(r'\W', '_', conversation_id)), 'x'):
            pass
    except FileExistsError:
        return False
    return True


def decide(event, now):
    mc = load_mine_chats()
    if not claim_first_prompt(event['conversation_id']):
        return CONTINUE
    root = transcripts_dir(event['workspace_roots'][0])
    msg = mc.classify(event['prompt'])
    if msg.kind != mc.TYPED:
        return CONTINUE
    matches = find_matches(mc, msg.text, root, event['conversation_id'], now)
    if not matches:
        return CONTINUE
    return json.dumps({'continue': True, 'additional_context': context_for(matches)})


def main(argv):
    if argv != ['hook']:
        sys.exit(__doc__)
    try:
        out = decide(json.load(sys.stdin), time.time())
    except Exception:
        out = CONTINUE
    print(out)


if __name__ == '__main__':
    main(sys.argv[1:])
