#!/usr/bin/env bash
# Self-checks for push-check.py: push and PR claims in the last message, the remote and PR checks, offline and
# timeout fail-open, and the stop hook. Offline: a local bare remote, a fixture env.md, and a fake gh on PATH.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
PC="$ROOT/scripts/push-check.py"
export HOME="$T/home" MSTACK_ENV="$T/env.md" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C
export FAKE_LOG="$T/gh.log"
mkdir -p "$HOME" "$T/bin"
PATH="$T/bin:$PATH"

cat > "$T/env.md" <<'EOF'
## PR tool

| Host or org | Push remote (name, scheme) | PR path (`gh` or MCP namespace) | Source |
| --- | --- | --- | --- |
| github.com (fixture-fork: mstack) | origin = fixture-fork/mstack (ssh) | gh (signed in as fixture-fork) | test |
EOF

cat > "$T/bin/gh" <<'EOF'
#!/usr/bin/env bash
case "$1 $2" in
  "auth token") [ -n "${FAKE_HANG:-}" ] && sleep 30; echo fake-token ;;
  "pr view")
    echo "$*" >> "$FAKE_LOG"
    [ -n "${FAKE_HEAD:-}" ] || exit 1
    echo "$FAKE_HEAD" ;;
  *) exit 1 ;;
esac
EOF
chmod +x "$T/bin/gh"

g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main "$@"; }
commit() { echo "$2" > "$T/$1/$2.txt"; g -C "$T/$1" add "$2.txt"; g -C "$T/$1" commit -qm "$2"; g -C "$T/$1" rev-parse HEAD; }

# fork's origin is an ssh URL that env.md names: gh-as.sh reads the login from it, and nothing contacts it.
g init -q --bare "$T/origin.git"
g init -q "$T/work"; g -C "$T/work" remote add origin "$T/origin.git"
C1=$(commit work c1); g -C "$T/work" push -q -u origin main
C2=$(commit work c2)
g init -q "$T/fork"; g -C "$T/fork" remote add origin git@github.com:fixture-fork/mstack.git
F1=$(commit fork f1); F2=$(commit fork f2); F3=$(commit fork f3)

tx() {
  python3 - "$T/$1.jsonl" "$2" <<'PY'
import json, sys
path, text = sys.argv[1], sys.argv[2]
with open(path, "w") as f:
    f.write(json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "go"}]}}) + "\n")
    f.write(json.dumps({"role": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n")
PY
  echo "$T/$1.jsonl"
}
check() { python3 "$PC" "$1" "$T"; }
clean() { [ "$(check "$1" 2>&1)" = "ok: no unbacked push claims in the last message" ] || fail "expected no finding: $2 -> $(check "$1" 2>&1)"; }
flags() { check "$1" > "$T/out.txt" 2>&1 || true; grep -q -- "$2" "$T/out.txt" || fail "expected finding '$2': $(cat "$T/out.txt")"; }

flags "$(tx unpushed "Pushed ${C2:0:7} to origin.")" "${C2:0:7} (\"Pushed ${C2:0:7} to origin.\"): not on any origin branch"
clean "$(tx negated "${C2:0:7} is not pushed yet.")" "a negated claim"
clean "$(tx pushed-old "Pushed ${C1:0:7}, the first commit.")" "a commit already on origin"
g -C "$T/work" push -q origin main
clean "$(tx after-push "Pushed ${C2:0:7}.")" "a push that landed"
C5=$(commit work c5)
clean "$(tx no-claim "${C5:0:7} is the next commit to review.")" "a SHA with no claim word"
g clone -q "$T/origin.git" "$T/other" && g -C "$T/other" checkout -q -b other && commit other x >/dev/null && g -C "$T/other" push -q origin other
clean "$(tx unreadable-head "Pushed ${C5:0:7} to origin.")" "a remote head the clone does not hold"
g --git-dir="$T/origin.git" update-ref -d refs/heads/other
echo "ok push claims"

C3=$(commit work c3)
export FAKE_HEAD=$F1
flags "$(tx pr-behind "${F2:0:7} is on PR #57.")" "not on PR #57 head ${F1:0:7}"
export FAKE_HEAD=$F3
clean "$(tx pr-ancestor "${F2:0:7} is on PR #57.")" "a commit that the PR head contains"
export FAKE_HEAD=$F2
clean "$(tx pr-head "${F2:0:7} is on the PR #57 head.")" "a commit that is the PR head"
export FAKE_HEAD=$F1
flags "$(tx pr-url "Pushed ${F2:0:7} to https://github.com/fixture-fork/mstack/pull/57.")" "not on PR #57 head ${F1:0:7}"
grep -q -- '--repo fixture-fork/mstack' "$FAKE_LOG" || fail "PR URL did not reach gh with --repo: $(cat "$FAKE_LOG")"
unset FAKE_HEAD
clean "$(tx pr-no-gh "${F2:0:7} is on PR #57.")" "gh has no answer"
echo "ok PR claims"

git_url=$(g -C "$T/work" remote get-url origin)
g -C "$T/work" remote set-url origin "$T/missing.git"
clean "$(tx offline "Pushed $(commit work c4 | cut -c1-7) to origin.")" "an offline remote"
g -C "$T/work" remote set-url origin "$git_url"
export FAKE_HANG=1 FAKE_HEAD=$F1
start=$(date +%s)
clean "$(tx hang "${F2:0:7} is on PR #57.")" "a gh that hangs"
elapsed=$(( $(date +%s) - start ))
[ "$elapsed" -lt 9 ] || fail "a hung gh held the hook for ${elapsed}s"
unset FAKE_HANG FAKE_HEAD
clean "$(tx unknown "Pushed deadbee1 to origin.")" "a SHA no checkout holds"
echo "ok fail open"

hook() { python3 "$PC" hook; }
ev() { printf '{"status":"%s","conversation_id":"c1","transcript_path":"%s","workspace_roots":["%s"]}' "$1" "$2" "$T"; }
got=$(ev completed "$(tx hook-bad "Pushed ${C3:0:7} to origin.")" | hook)
python3 -c 'import json,sys; m=json.load(sys.stdin)["followup_message"]; assert "'"${C3:0:7}"'" in m and "push" in m' <<<"$got" || fail "hook followup: $got"
[ "$(ev aborted "$(tx hook-abort "Pushed ${C3:0:7} to origin.")" | hook)" = "{}" ] || fail "aborted turn must be {}"
[ "$(ev completed "$T/missing.jsonl" | hook)" = "{}" ] || fail "missing transcript must be {}"
[ "$(echo 'not json' | hook)" = "{}" ] || fail "garbage stdin must be {}"
echo "ok hook"

rc=0; python3 "$PC" "$(tx cli-bad "Pushed ${C3:0:7} to origin.")" "$T" >/dev/null || rc=$?
[ "$rc" = 1 ] || fail "findings must exit 1, got $rc"
rc=0; python3 "$PC" "$(tx cli-ok "Nothing to report.")" "$T" >/dev/null || rc=$?
[ "$rc" = 0 ] || fail "no claim must exit 0, got $rc"
rc=0; python3 "$PC" >/dev/null 2>&1 || rc=$?
[ "$rc" = 2 ] || fail "no argument must exit 2, got $rc"
rc=0; python3 "$PC" "$T/missing.jsonl" >/dev/null 2>&1 || rc=$?
[ "$rc" = 2 ] || fail "missing transcript must exit 2, got $rc"
echo "ok cli"

echo "ok push-check"
