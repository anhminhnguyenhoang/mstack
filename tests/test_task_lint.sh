#!/usr/bin/env bash
# Self-checks for task-lint.py: the Task spawn rules, the ateam-mode gate, the turn boundary, and the stop hook.
# Offline: fixture transcripts and brief files in a temp dir.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
TL="$ROOT/scripts/task-lint.py"
export HOME="$T/home" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C
mkdir -p "$HOME" "$T/briefs" "$T/ws"
printf 'Read the rules first.\n\nateam-mode: /fixture/ateam-mode/SKILL.md. public push: no.\n' > "$T/briefs/common.md"
printf 'No ateam line in this brief.\n' > "$T/briefs/plain.md"

python3 - "$T" <<'PY'
import json, os, sys
T = sys.argv[1]
ATTACHED = "<manually_attached_skills>\nSkill Name: ateam-mode\nPath: /fixture/ateam-mode/SKILL.md\n</manually_attached_skills>\nstart"
WORKER = "Read /fixture/ateam-mode/worker.md before anything else.\n\nDo the work."

def user(text):
    return {"role": "user", "message": {"content": [{"type": "text", "text": text}]}}

def asst(*calls):
    return {"role": "assistant", "message": {"content": [{"type": "text", "text": "Spawning."}, *calls]}}

def task(**inp):
    return {"type": "tool_use", "name": "Task", "input": inp}

def dyn(**args):
    return {"type": "tool_use", "name": "CallDynamicTool", "input": {"namespace": "cursor", "toolName": "Task", "arguments": args}}

def write(name, rows):
    with open(os.path.join(T, name), "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

write("mix.jsonl", [
    user(ATTACHED),
    user("run the wave"),
    asst(task(description="Find tests", subagent_type="explore", run_in_background=True, prompt=WORKER)),
    asst(
        task(description="Fix A", subagent_type="generalPurpose", model="m", run_in_background="false", prompt=WORKER),
        task(description="Fix B", subagent_type="generalPurpose", model="m", run_in_background="true", prompt=WORKER),
    ),
    asst(task(description="Lone foreground", subagent_type="generalPurpose", model="m", run_in_background=False, prompt=WORKER)),
    asst(task(description="Ateam inline line", subagent_type="ateam-agent", model="m", run_in_background=True,
              prompt="Do it. ateam-mode: /fixture/ateam-mode/SKILL.md. public push: no.")),
    asst(task(description="Ateam no line", subagent_type="ateam-agent", model="m", run_in_background=True, prompt="Do the fix.")),
    asst(task(description="Ateam via file", subagent_type="ateam-agent", model="m", run_in_background=True,
              prompt=f"Read {T}/briefs/common.md first and follow it.")),
    asst(task(description="Ateam file without line", subagent_type="ateam-agent", model="m", run_in_background=True,
              prompt=f"Read {T}/briefs/plain.md first and follow it.")),
    asst(task(description="Worker missing", subagent_type="explore", model="m", run_in_background=True, prompt="Find the file.")),
    asst(task(description="Worker not first", subagent_type="explore", model="m", run_in_background=True,
              prompt="Intro.\nRead /fixture/ateam-mode/worker.md before anything else.")),
    asst(dyn(description="Dyn no model", subagent_type="generalPurpose", run_in_background=True, prompt=WORKER)),
    asst(dyn(description="Dyn clean", subagent_type="generalPurpose", model="m", run_in_background="true", prompt=WORKER)),
])
write("plain-chat.jsonl", [
    user("refactor the parser"),
    asst(task(description="Plain explore", subagent_type="explore", run_in_background=True, prompt="Find it.")),
])
write("later-turn.jsonl", [
    user(ATTACHED),
    asst(task(description="Old bad spawn", subagent_type="explore", run_in_background=True, prompt=WORKER)),
    user("continue"),
    asst(task(description="New clean spawn", subagent_type="explore", model="m", run_in_background=True, prompt=WORKER)),
])
with open(os.path.join(T, "partial.jsonl"), "w") as f:
    f.write(json.dumps(user(ATTACHED)) + "\n")
    f.write(json.dumps(asst(task(description="Complete line", subagent_type="explore", run_in_background=True, prompt=WORKER))) + "\n")
    f.write('{"role": "assistant", "message": {"content": [{"type": "tool_use"')
PY

rules_of() { sed -n 's/^- Task \([0-9]*\) .*\[\([a-z-]*\)\].*/\1|\2/p' <<<"$1" | sort | tr '\n' ' '; }

rc=0
out=$(python3 "$TL" "$T/mix.jsonl" 2>&1) || rc=$?
[ "$rc" = 1 ] || fail "findings must exit 1, got $rc"
want=$(printf '%s\n' '1|no-model' '2|foreground' '6|ateam-brief' '8|ateam-brief' '9|worker-brief' '10|worker-brief' '11|no-model' | sort | tr '\n' ' ')
[ "$(rules_of "$out")" = "$want" ] || fail "mix findings: got [$(rules_of "$out")] want [$want]"
grep -q 'Task 2 (generalPurpose, "Fix A") \[foreground\]' <<<"$out" || fail "Fix A named by description"
grep -q 'A Task that already started keeps its settings' <<<"$out" || fail "follow-up closes with the keep-settings line"
echo "ok rules"

out=$(python3 "$TL" "$T/plain-chat.jsonl") || fail "plain chat must exit 0"
[ "$out" = "ok: no Task violations this turn" ] || fail "plain chat output: $out"
echo "ok gate"

python3 "$TL" "$T/later-turn.jsonl" >/dev/null || fail "earlier turn's spawn leaked into this turn"
echo "ok turn"

rc=0
out=$(python3 "$TL" "$T/partial.jsonl" 2>&1) || rc=$?
[ "$rc" = 1 ] || fail "partial transcript with a bad spawn must exit 1, got $rc"
grep -q 'Complete line' <<<"$out" && grep -q '\[no-model\]' <<<"$out" || fail "partial line broke parsing: $out"
echo "ok partial"

rc=0; python3 "$TL" >/dev/null 2>&1 || rc=$?
[ "$rc" = 2 ] || fail "no argument must exit 2, got $rc"
rc=0; python3 "$TL" "$T/missing.jsonl" >/dev/null 2>&1 || rc=$?
[ "$rc" = 2 ] || fail "missing transcript must exit 2, got $rc"
echo "ok cli"

hook() { python3 "$TL" hook; }
ev() { printf '{"status":"%s","conversation_id":"%s","transcript_path":"%s","workspace_roots":["%s"]}' "$1" "$2" "$3" "$T/ws"; }
got=$(ev completed c1 "$T/mix.jsonl" | hook)
python3 -c 'import json,sys; m=json.load(sys.stdin)["followup_message"]; assert "[no-model]" in m and "Dyn no model" in m' <<<"$got" || fail "hook followup: $got"
[ "$(ev aborted c1 "$T/mix.jsonl" | hook)" = "{}" ] || fail "aborted turn must be {}"
[ "$(ev completed c1 "$T/plain-chat.jsonl" | hook)" = "{}" ] || fail "clean chat must be {}"
[ "$(ev completed c1 "$T/missing.jsonl" | hook)" = "{}" ] || fail "missing transcript must be {}"
[ "$(echo 'not json' | hook)" = "{}" ] || fail "garbage stdin must be {}"
echo "ok hook"

slug=$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]).strip("/").replace("/", "-"))' "$T/ws")
mkdir -p "$HOME/.cursor/projects/$slug/agent-transcripts/conv9"
cp "$T/mix.jsonl" "$HOME/.cursor/projects/$slug/agent-transcripts/conv9/conv9.jsonl"
got=$(printf '{"status":"completed","conversation_id":"conv9","workspace_roots":["%s"]}' "$T/ws" | hook)
grep -q 'followup_message' <<<"$got" || fail "derived transcript path not read: $got"
echo "ok derived path"

echo "ok task-lint"
