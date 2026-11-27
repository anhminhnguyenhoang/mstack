#!/usr/bin/env python3
"""Summarize agent chat transcripts for the recall skill. Stdlib only.

  mine-chats.py --root DIR --since YYYY-MM-DD --out DIR
                [--as-of 'YYYY-MM-DD HH:MM:SS'] [--exclude-text TEXT]

DIR is an agent-transcripts directory. It holds legacy <id>.jsonl files, nested
<id>/<id>.jsonl files, and subagent files <id>/subagents/<child>.jsonl. Dates are local time.
A chat is skipped when its file is older than --since, when its first user message holds
--exclude-text, or when its file was written after --as-of. A chat written again after --as-of
drops out of later runs, so to freeze a live directory, copy it and run on the copy.

Each user message is typed or injected. The harness wraps or replaces the user's words with
injected text, matched by SIGNATURES. Only typed messages count in n_user_msgs. A message with
no typed words left counts in n_injected. A mixed message keeps its <user_query> text.

Writes to --out:
  chats.csv         one row per chat, oldest first
  user_messages.md  per chat: a header, then each typed user message (1500 characters at most)
  stats.json        totals, injected counts by signature, parse errors, unknown line shapes,
                    and the filters used
"""

import argparse
import collections
import csv
import glob
import json
import os
import re
import time

TEXT_LIMIT = 1500
PROMPT_LIMIT = 300

# One row per injected signature. A wrapper row matches a block the harness puts around the
# user's words, and the block is removed. A turn row matches the start of the typed words of a
# whole turn that the harness or a stop hook writes, and the message is injected.
SIGNATURES = (
    ('manually_attached_skills', 'wrapper', r'<manually_attached_skills>.*?</manually_attached_skills>'),
    ('system_reminder', 'wrapper', r'<system_reminder>.*?</system_reminder>'),
    ('system_notification', 'wrapper', r'<system_notification>.*?</system_notification>'),
    ('cursor_commands', 'wrapper', r'<cursor_commands>.*?</cursor_commands>'),
    ('image_files', 'wrapper', r'<image_files>.*?</image_files>'),
    ('side_chat_boundary', 'wrapper', r'<side_chat_boundary>.*?</side_chat_boundary>'),
    ('agent_catalog', 'wrapper', r'<(available_subagent_types|available_subagent_models|dynamic_tool_catalog|dynamic_tool_namespaces)>.*?</\1>'),
    ('timestamp', 'wrapper', r'<timestamp>.*?</timestamp>'),
    ('draft_lint', 'turn', r'mstack draft lint is red on a draft (changed in the last 20 minutes|this chat edited)\.'),
    ('task_finished', 'turn', r'Briefly inform the user about the task result|Perform any necessary follow-up actions in response to the subagent completion'),
    ('harness_continue', 'turn', r'Your previous response was interrupted\. Continue from where you left off\.'),
)
TYPED, INJECTED = 'typed', 'injected'
Msg = collections.namedtuple('Msg', ['kind', 'signature', 'text'])


def iter_messages(path, stats):
    """Yield (role, blocks) for each message line, in file order. Count bad lines in stats."""
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError:
                stats['parse_errors'] += 1
                continue
            if isinstance(d, dict) and d.get('type') == 'turn_ended':
                continue
            msg = d.get('message') if isinstance(d, dict) else None
            content = msg.get('content') if isinstance(msg, dict) else None
            if not isinstance(d, dict) or d.get('role') not in ('user', 'assistant') or not isinstance(content, (list, str)):
                stats['unknown_line_shapes'] += 1
                continue
            if isinstance(content, str):
                content = [{'type': 'text', 'text': content}]
            yield d['role'], [b for b in content if isinstance(b, dict)]


def load(path, stats):
    return list(iter_messages(path, stats))


def chat_files(root):
    """Map each chat id to its transcript file. Subagent files sit one folder deeper and do not match."""
    paths = glob.glob(os.path.join(root, '*.jsonl')) + glob.glob(os.path.join(root, '*', '*.jsonl'))
    return {os.path.splitext(os.path.basename(p))[0]: p for p in paths}


def text_of(blocks):
    return '\n'.join(b['text'] for b in blocks if b.get('type') == 'text' and isinstance(b.get('text'), str))


def classify(raw):
    """Return a Msg. TYPED carries the typed words. INJECTED carries the signature that made the
    whole message injected, or 'empty' when no words and no wrapper remain."""
    found = re.findall(r'<user_query>(.*?)</user_query>', raw, re.DOTALL)
    body = '\n'.join(found) if found else raw
    hit = None
    for name, kind, pattern in SIGNATURES:
        if kind != 'wrapper':
            continue
        if hit is None and re.search(pattern, body, re.DOTALL):
            hit = name
        body = re.sub(pattern, '', body, flags=re.DOTALL)
    body = body.strip()
    if not body:
        return Msg(INJECTED, hit or 'empty', '')
    for name, kind, pattern in SIGNATURES:
        if kind == 'turn' and re.match(pattern, body):
            return Msg(INJECTED, name, '')
    return Msg(TYPED, None, body)


def attached_skills(raw):
    names = []
    for block in re.findall(r'<manually_attached_skills>(.*?)</manually_attached_skills>', raw, re.DOTALL):
        names += re.findall(r'^Skill Name:\s*(.+?)\s*$', block, re.MULTILINE)
    return names


def is_task(block):
    # Arguments often hold invalid JSON (a stray trailing brace), so only the tool name is read.
    inp = block.get('input') if isinstance(block.get('input'), dict) else {}
    return block.get('name') == 'Task' or (block.get('name') == 'CallDynamicTool' and inp.get('toolName') == 'Task')


def clip(text):
    if len(text) <= TEXT_LIMIT:
        return text
    return f'{text[:TEXT_LIMIT]}\n[...truncated {len(text) - TEXT_LIMIT} chars]'


def main():
    ap = argparse.ArgumentParser(description='Summarize agent chat transcripts for the recall skill.')
    ap.add_argument('--root', required=True, help='agent-transcripts directory')
    ap.add_argument('--since', required=True, help='YYYY-MM-DD: skip chats last written before this date')
    ap.add_argument('--as-of', help="'YYYY-MM-DD HH:MM:SS': skip files written after this time")
    ap.add_argument('--exclude-text', default='', help='skip chats whose first user message contains this')
    ap.add_argument('--out', required=True, help='output directory')
    args = ap.parse_args()

    since = time.mktime(time.strptime(args.since, '%Y-%m-%d'))
    as_of = time.mktime(time.strptime(args.as_of, '%Y-%m-%d %H:%M:%S')) if args.as_of else None

    def kept(ts):
        return as_of is None or ts <= as_of

    stats = {'parse_errors': 0, 'unknown_line_shapes': 0}
    files = chat_files(args.root)
    mtime = {cid: os.path.getmtime(p) for cid, p in files.items()}
    chats, excluded = [], []
    by_signature = collections.Counter()
    for cid in sorted(files, key=lambda c: (mtime[c], c)):
        if mtime[cid] < since or not kept(mtime[cid]):
            continue
        msgs = load(files[cid], stats)
        raws = [text_of(blocks) for role, blocks in msgs if role == 'user']
        if args.exclude_text and raws and args.exclude_text in raws[0]:
            excluded.append(cid)
            continue
        subs = [s for s in sorted(glob.glob(os.path.join(args.root, cid, 'subagents', '*.jsonl')))
                if kept(os.path.getmtime(s))]
        for s in subs:
            load(s, stats)
        tools = [b for _, blocks in msgs for b in blocks if b.get('type') == 'tool_use']
        msgs_typed = [classify(r) for r in raws]
        texts = [m.text for m in msgs_typed if m.kind == TYPED]
        injected = [m.signature for m in msgs_typed if m.kind == INJECTED]
        by_signature.update(injected)
        chats.append({
            'id': cid,
            'mtime': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(mtime[cid])),
            'n_user_msgs': len(texts),
            'n_injected': len(injected),
            'n_assistant_msgs': sum(1 for role, _ in msgs if role == 'assistant'),
            'n_tool_uses': len(tools),
            'attached_skills': ';'.join(dict.fromkeys(n for r in raws for n in attached_skills(r))),
            'first_prompt': ' '.join(next(iter(texts), '').split())[:PROMPT_LIMIT],
            'n_subagents': len(subs),
            'task_calls': sum(is_task(b) for b in tools),
            'texts': texts,
        })

    os.makedirs(args.out, exist_ok=True)
    cols = ['id', 'mtime', 'n_user_msgs', 'n_injected', 'n_assistant_msgs', 'n_tool_uses', 'attached_skills',
            'first_prompt', 'n_subagents', 'task_calls']
    with open(os.path.join(args.out, 'chats.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for c in chats:
            w.writerow([c[k] for k in cols])

    with open(os.path.join(args.out, 'user_messages.md'), 'w', encoding='utf-8') as fh:
        for c in chats:
            fh.write(f"## {c['id']} | {c['mtime']} | {c['first_prompt'][:80]}\n\n")
            for i, text in enumerate(c['texts'], 1):
                fh.write(f'**msg {i}**\n\n{clip(text)}\n\n')

    with open(os.path.join(args.out, 'stats.json'), 'w', encoding='utf-8') as fh:
        json.dump({
            'since': args.since,
            'as_of': args.as_of,
            'excluded_ids': excluded,
            'n_parent_chats': len(chats),
            'n_subagent_files': sum(c['n_subagents'] for c in chats),
            'n_user_msgs': sum(c['n_user_msgs'] for c in chats),
            'n_injected_msgs': sum(c['n_injected'] for c in chats),
            'injected_by_signature': dict(sorted(by_signature.items())),
            'parse_errors': stats['parse_errors'],
            'unknown_line_shapes': stats['unknown_line_shapes'],
        }, fh, indent=2)
        fh.write('\n')
    print(f'{len(chats)} chats, {len(excluded)} excluded, written to {args.out}')


if __name__ == '__main__':
    main()
