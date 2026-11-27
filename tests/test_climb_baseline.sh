#!/usr/bin/env bash
# Self-checks for the climb baseline record: freeze writes B and why, and the stop gate
# refuses a B that moved and a bench artifact that names another base_sha. Offline: local repos.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c advice.detachedHead=false "$@"; }
export HOME="$T/home" XDG_CACHE_HOME="$T/cache"
mkdir -p "$HOME"
CG="$ROOT/scripts/climb-gate.py"

# newrepo NAME: a repo whose one commit is B, with a kernel and a harness file
newrepo() {
  local r="$T/$1"
  g init -q "$r"; echo k0 > "$r/kernel.py"; echo h0 > "$r/test_x.py"
  g -C "$r" add -A; g -C "$r" commit -qm B
  echo "$r"
}
head_of() { git -C "$1" rev-parse HEAD; }
stop() { printf '{"conversation_id":"%s","status":"completed"}' "$1" | python3 "$CG" hook; }
# art TICKET NAME SHA [BASE_SHA]: a bench artifact that passed correctness at SHA on a clean tree
art() {
  local base=""
  [ -n "${4:-}" ] && base=",\"base_sha\":\"$4\""
  printf '{"ts":"%s","correctness":{"passed":true},"repos":[{"path":"/in/container","sha":"%s","dirty":false}]%s}' "$(date -u +%FT%T+00:00)" "$3" "$base" > "$1/bench_$2.json"
}
# edit_lock LOCK KEY VALUE: set KEY to the JSON VALUE in the lock, or drop KEY when VALUE is "-"
edit_lock() { python3 - "$1" "$2" "$3" <<'EOF'
import json, sys
path, key, val = sys.argv[1:]
lock = json.load(open(path))
if val == "-": lock.pop(key)
else: lock[key] = json.loads(val)
json.dump(lock, open(path, "w"))
EOF
}

R=$(newrepo a); B=$(head_of "$R"); TK="$T/t1"
CURSOR_CONVERSATION_ID=c1 python3 "$CG" freeze "$TK" "$R" test_x.py --chosen-by user --reason "the commit the user named" >/dev/null
python3 - "$TK/harness.lock" "$B" <<'EOF' || fail "freeze did not write the baseline record: $(cat "$TK/harness.lock")"
import json, sys
lock = json.load(open(sys.argv[1])); b = lock["baseline"]
assert lock["schema"] == 2 and b["sha"] == sys.argv[2] == lock["base"], lock
assert (b["chosen_by"], b["reason"]) == ("user", "the commit the user named"), b
assert b["recorded_at"] == lock["frozen"], b
EOF
python3 "$CG" freeze "$TK" "$R" test_x.py >/dev/null
python3 -c 'import json,sys; b=json.load(open(sys.argv[1]))["baseline"]; assert b["reason"] == "the commit the user named", b' "$TK/harness.lock" || fail "re-freeze at the same B dropped the reason"
echo k1 > "$R/kernel.py"; g -C "$R" commit -qam B2
out=$(python3 "$CG" freeze "$TK" "$R" test_x.py)
grep -q "^NOTE B has no reason" <<<"$out" || fail "re-freeze at a new B did not say the reason is missing"
python3 -c 'import json,sys; b=json.load(open(sys.argv[1]))["baseline"]; assert b["reason"] is None and b["sha"] != sys.argv[2], b' "$TK/harness.lock" "$B" || fail "re-freeze at a new B kept the old reason"
python3 "$CG" freeze --reason "flags before the paths" "$T/t1b" "$R" test_x.py >/dev/null
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["baseline"]["reason"] == "flags before the paths"' "$T/t1b/harness.lock" || fail "--reason before the paths was not recorded"
rc=0; python3 "$CG" freeze "$T/t1c" "$R" test_x.py --reason >/dev/null 2>"$T/err1c" || rc=$?
[ "$rc" = 1 ] && grep -q "needs a value" "$T/err1c" || fail "--reason without a value: exit $rc"
echo "ok freeze record"

R=$(newrepo b); B=$(head_of "$R"); TK="$T/t2"
CURSOR_CONVERSATION_ID=c2 python3 "$CG" freeze "$TK" "$R" test_x.py >/dev/null
edit_lock "$TK/harness.lock" schema -; edit_lock "$TK/harness.lock" baseline -
stop c2 | grep -q "B in $R has no bench_" || fail "a climb with no baseline record got no proof gap"
art "$TK" a "$B"
[ "$(stop c2)" = '{}' ] || fail "a climb with no baseline record refused a measured B"
echo k1 > "$R/kernel.py"; g -C "$R" commit -qam moved
stop c2 | grep -q "frozen baseline" && fail "a climb with no schema: the baseline check refused the moved B"
stop c2 | grep -q "B in $R has no bench_" || fail "a climb with no schema: no proof gap at the moved B"
echo "ok old climb"

R=$(newrepo c); B=$(head_of "$R"); TK="$T/t3"
CURSOR_CONVERSATION_ID=c3 python3 "$CG" freeze "$TK" "$R" test_x.py >/dev/null
art "$TK" a "$B"
[ "$(stop c3)" = '{}' ] || fail "measured B refused"
edit_lock "$TK/harness.lock" baseline -
stop c3 | grep -q "has no baseline record" || fail "a new climb with no baseline record passed"
python3 "$CG" pause "$TK" "no idle GPU" >/dev/null
stop c3 | grep -q "has no baseline record" || fail "pause covered a missing baseline record"
echo "ok missing record"

R=$(newrepo d); B=$(head_of "$R"); TK="$T/t4"
CURSOR_CONVERSATION_ID=c4 python3 "$CG" freeze "$TK" "$R" test_x.py --reason "the first commit" >/dev/null
art "$TK" a "$B"
[ "$(stop c4)" = '{}' ] || fail "measured B refused"
echo k1 > "$R/kernel.py"; g -C "$R" commit -qam B2; B2=$(head_of "$R")
art "$TK" b "$B2"
stop c4 | grep -q "B in $R is at $B2, but the baseline recorded at freeze is $B" || fail "a B that moved off the baseline passed"
python3 "$CG" pause "$TK" "no idle GPU" >/dev/null
stop c4 | grep -q "is at $B2" || fail "pause covered a moved B"
echo "ok moved B"

R=$(newrepo e); B=$(head_of "$R"); TK="$T/t5"; S="$T/s5"
CURSOR_CONVERSATION_ID=c5 python3 "$CG" freeze "$TK" "$R" test_x.py --reason "the first commit" >/dev/null
g -C "$R" worktree add -q -b s5 "$S"; echo k2 > "$S/kernel.py"; g -C "$S" commit -qam S; SH=$(head_of "$S")
python3 "$CG" best "$TK" "$S" >/dev/null
art "$TK" s "$SH" "$(printf 'f%.0s' {1..40})"
stop c5 | grep -q "bench_s.json names baseline ffffffff" || fail "S* proof naming another baseline passed"
art "$TK" s "$SH" "${B:0:6}"
stop c5 | grep -q "bench_s.json names baseline ${B:0:6}" || fail "S* proof naming a 6 character prefix passed"
art "$TK" s "$SH" "${B:0:12}"
[ "$(stop c5)" = '{}' ] || fail "S* proof naming the baseline by prefix refused"
rm "$TK/bench_s.json"; art "$TK" s "$SH"
[ "$(stop c5)" = '{}' ] || fail "S* proof with no base_sha refused"
echo "ok artifact base_sha"
