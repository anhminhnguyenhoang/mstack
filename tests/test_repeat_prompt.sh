#!/usr/bin/env bash
# Offline checks for repeat-prompt.py, the beforeSubmitPrompt hook.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c advice.detachedHead=false "$@"; }
H="$T/home"
mkdir -p "$H"
export HOME="$H" XDG_CACHE_HOME="$T/cache"

# --- repeat-prompt.py: the beforeSubmitPrompt hook names earlier chats that opened with the same prompt
RP="$ROOT/scripts/repeat-prompt.py" RW="$T/rp/ws/app" RW0="$T/rp/ws/none"
RS="$H/.cursor/projects/$(echo "${RW#/}" | tr / -)/agent-transcripts"
LONG='walk me through the Mega-mHC fused kernel, its LDS layout, the MFMA tile shapes, the scale path, and where the time goes in the epilogue'
python3 - "$RS" "$LONG" <<'EOF'
import json, os, sys
root, long = sys.argv[1], sys.argv[2]
def msg(*texts): return json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": t} for t in texts]}})
def q(text): return f"<user_query>\n{text}\n</user_query>"
chats = {
    "a1.jsonl": [msg(f"<manually_attached_skills>\nSkill Name: fixture\n</manually_attached_skills>\n<timestamp>Friday, Nov 20, 2026</timestamp>\n{q(long)}")],
    "b2.jsonl": [msg(q(long.replace("epilogue", "epilog")))],
    "c3/c3.jsonl": [msg(q("fix the flaky lanes test in tests/test_scripts.sh so the quiet lane passes"))],
    "d4/d4.jsonl": [msg(q(long))],
    "e5/e5.jsonl": [msg("<timestamp>Monday, Nov 23, 2026</timestamp>"), msg(q(long))],
    "g7/g7.jsonl": [msg(q("what model are you"))],
    "h8/h8.jsonl": [msg(q(long.replace("Mega-mHC fused kernel", "attlas lane report").replace("epilogue", "report")))],
    "cur-7/cur-7.jsonl": [msg(q(long))],
    "p8/subagents/s9.jsonl": [msg(q(long))],
}
for rel, lines in chats.items():
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
EOF
touch -d '3 days ago' "$RS/a1.jsonl"
touch -d '10 days ago' "$RS/b2.jsonl"
touch -d '2 days ago' "$RS/c3/c3.jsonl"
touch -d '45 days ago' "$RS/d4/d4.jsonl"
touch -d '5 days ago' "$RS/e5/e5.jsonl"
touch -d '4 days ago' "$RS/g7/g7.jsonl" "$RS/p8/subagents/s9.jsonl"
touch -d '6 days ago' "$RS/h8/h8.jsonl"
touch -d '1 day ago' "$RS/cur-7/cur-7.jsonl"
hookev() { python3 -c 'import json,sys; print(json.dumps({"conversation_id": sys.argv[1], "prompt": sys.argv[2], "workspace_roots": [sys.argv[3]]}))' "$@"; }
hookrun() { python3 "$RP" hook; }
ctx_ids() { python3 -c 'import json,re,sys; d=json.load(sys.stdin); print(" ".join(sorted(re.findall(r"^- (\S+) ", d.get("additional_context", ""), re.M))))'; }
cont='{"continue": true}'
[ "$(hookev cur-7 "$LONG" "$RW" | hookrun | ctx_ids)" = "a1 b2 e5" ] || fail "repeat-prompt did not name the earlier chats a1 b2 e5"
hookev new-1 "$LONG" "$RW" | hookrun | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["continue"] is True; assert "/recall" in d["additional_context"] and "/ketchup" in d["additional_context"]' || fail "repeat-prompt output lacks continue or the /recall and /ketchup hint"
[ "$(hookev cur-7 "$LONG" "$RW" | hookrun)" = "$cont" ] || fail "a second prompt in the same chat got context"
[ "$(hookev new-2 "$LONG" "$RW0" | hookrun)" = "$cont" ] || fail "a workspace with no transcripts got context"
[ "$(hookev new-3 "what model are you" "$RW" | hookrun)" = "$cont" ] || fail "a prompt under 20 characters matched"
[ "$(hookev new-4 "summarize the quiet lane check and list its exit codes for a reviewer" "$RW" | hookrun)" = "$cont" ] || fail "an unrelated prompt matched"
[ "$(printf 'not json' | hookrun)" = "$cont" ] || fail "a malformed event did not fail open"
mkdir -p "$T/rp/lone" && cp "$RP" "$T/rp/lone/"
[ "$(hookev new-6 "$LONG" "$RW" | python3 "$T/rp/lone/repeat-prompt.py" hook)" = "$cont" ] || fail "a missing mine-chats.py did not fail open"
rc=0; python3 "$RP" nope </dev/null >/dev/null 2>&1 || rc=$?
[ "$rc" = 1 ] || fail "repeat-prompt.py exit $rc on a bad command line, want 1"
bhook=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["hooks"]["beforeSubmitPrompt"][0]["command"])' "$ROOT/hooks/hooks.json")
(cd /tmp && hookev new-5 "$LONG" "$RW" | CURSOR_PLUGIN_ROOT="$ROOT" timeout 5 sh -c "$bhook") | ctx_ids | grep -qx "a1 b2 cur-7 e5" || fail "plugin beforeSubmitPrompt hook did not name a1 b2 cur-7 e5 within the hook timeout"
echo "ok repeat-prompt"
