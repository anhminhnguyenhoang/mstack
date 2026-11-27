#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
DL="$ROOT/scripts/draft-lint.py"
H="$T/home" W="$H/reviews/repo-7" ok='The gfx950 test passes.'
mkdir -p "$W" "$H/.cursor/mstack"
HR=$(realpath "$H")
export HOME="$H" XDG_CACHE_HOME="$T/cache"

lint_rc() { local rc=0; out=$("$DL" "$1" 2>&1) || rc=$?; [ "$rc" = "$2" ] || fail "$1 exit $rc, want $2: $out"; }

echo "$ok" > "$H/slack-draft-x.md"
lint_rc "$H/slack-draft-x.md" 1
grep -qF "LOCATION slack-draft-x.md sits in $HR," <<<"$out" || fail "LOCATION red did not name the draft and its folder: $out"
echo "$ok" > "$W/pr-draft-x.md"; lint_rc "$W/pr-draft-x.md" 0
mkdir "$H/ticket-x"; echo "$ok" > "$H/ticket-x/comment-draft-x.md"; lint_rc "$H/ticket-x/comment-draft-x.md" 0
echo "ok location home"

mkdir -p "$H/Downloads/sub"
printf '# folders that never hold a work draft\n~/Downloads  # browser drop folder\n\n' > "$H/.cursor/mstack/non-work-roots.txt"
echo "$ok" > "$H/Downloads/slack-draft-x.md"; lint_rc "$H/Downloads/slack-draft-x.md" 1
grep -qF "LOCATION slack-draft-x.md sits in $HR/Downloads," <<<"$out" || fail "configured root not red: $out"
echo "$ok" > "$H/Downloads/sub/slack-draft-x.md"; lint_rc "$H/Downloads/sub/slack-draft-x.md" 0
rm "$H/.cursor/mstack/non-work-roots.txt"
echo "ok location config"

echo "$ok" > "$H/slack-draft-x.md"
printf '{"conversation_id":"c1","status":"completed","file_path":"%s"}' "$H/slack-draft-x.md" | "$DL" record >/dev/null
printf '{"conversation_id":"c1","status":"completed"}' | "$DL" hook | grep -qF "LOCATION slack-draft-x.md" || fail "stop hook did not report LOCATION"
rm "$H/slack-draft-x.md"
echo "ok location hook"

P="$T/prune"; mkdir -p "$P"
for v in 1 2 3; do echo "draft $v" > "$P/pr-draft-x-v$v.md"; done
echo gate > "$P/pr-draft-x-v1.md.gate"; echo gate > "$P/pr-draft-x-v3.md.gate"
rc=0; out=$("$DL" prune "$P") || rc=$?
[ "$rc" = 1 ] || fail "prune with candidates exited $rc, want 1: $out"
grep -qF "  keep   pr-draft-x-v3.md (newest)" <<<"$out" || fail "newest not kept: $out"
grep -qF "  prune  pr-draft-x-v1.md (+ .gate)" <<<"$out" || fail "v1 not listed with its gate: $out"
grep -qF "  prune  pr-draft-x-v2.md" <<<"$out" || fail "v2 not listed: $out"
! grep -qF "  prune  pr-draft-x-v3.md" <<<"$out" || fail "newest listed for pruning: $out"
grep -qF "Dry run: nothing deleted" <<<"$out" || fail "dry run does not say so: $out"
[ -e "$P/pr-draft-x-v1.md" ] && [ -e "$P/pr-draft-x-v2.md" ] && [ -e "$P/pr-draft-x-v1.md.gate" ] || fail "dry run deleted a file"
rc=0; "$DL" prune "$P" --dry-run >/dev/null || rc=$?; [ "$rc" = 1 ] || fail "--dry-run is not the listing mode: exit $rc"
rc=0; "$DL" prune "$P" --yes >/dev/null || rc=$?; [ "$rc" = 0 ] || fail "prune --yes exited $rc"
[ ! -e "$P/pr-draft-x-v1.md" ] && [ ! -e "$P/pr-draft-x-v2.md" ] || fail "--yes left a superseded draft"
[ ! -e "$P/pr-draft-x-v1.md.gate" ] || fail "--yes left the gate stamp of a deleted draft"
[ -e "$P/pr-draft-x-v3.md" ] && [ -e "$P/pr-draft-x-v3.md.gate" ] || fail "--yes deleted the newest draft or its gate"
out=$("$DL" prune "$P") || fail "a second prune still lists work: $out"
[ "$out" = "nothing to prune" ] || fail "a second prune said: $out"
echo "ok prune"

A="$T/approved"; mkdir -p "$A"
for v in 1 2 3; do echo "draft $v" > "$A/pr-draft-x-v$v.md"; done
printf '# approvals, oldest first\npr-draft-x-v1.md\npr-draft-x-v2.md  # the human said yes\n' > "$A/posted.txt"
rc=0; out=$("$DL" prune "$A") || rc=$?
[ "$rc" = 1 ] || fail "approved run exited $rc: $out"
grep -qF "  keep   pr-draft-x-v2.md (approved)" <<<"$out" || fail "approved version not kept: $out"
grep -qF "  prune  pr-draft-x-v1.md" <<<"$out" || fail "v1 not listed with v2 approved: $out"
! grep -qF "  prune  pr-draft-x-v2.md" <<<"$out" || fail "approved version listed for pruning: $out"
printf 'pr-draft-x-v2.md\npr-draft-x-v1.md\n' > "$A/posted.txt"
rc=0; out=$("$DL" prune "$A") || rc=$?
grep -qF "  keep   pr-draft-x-v1.md (approved)" <<<"$out" || fail "the last ledger line did not win: $out"
grep -qF "  prune  pr-draft-x-v2.md" <<<"$out" || fail "v2 kept although v1 was approved last: $out"
echo "ok prune approved"

U="$T/unversioned"; mkdir -p "$U/sub"
echo one > "$U/review-draft-y.md"; echo two > "$U/review-draft-y-v2.md"
echo solo > "$U/slack-draft-solo.md"; echo note > "$U/notes.md"; echo posted > "$U/pr-draft-z.posted.md"
echo old > "$U/sub/pr-draft-q-v1.md"; echo new > "$U/sub/pr-draft-q-v2.md"
out=$("$DL" prune "$U" || true)
[ "$(grep -c '^  prune  ' <<<"$out")" = 1 ] && grep -qF "  prune  review-draft-y.md" <<<"$out" || fail "unversioned draft not the only candidate: $out"
"$DL" prune "$U" --yes >/dev/null
[ ! -e "$U/review-draft-y.md" ] && [ -e "$U/review-draft-y-v2.md" ] || fail "unversioned draft not pruned, or its newer version touched"
[ -e "$U/slack-draft-solo.md" ] && [ -e "$U/notes.md" ] && [ -e "$U/pr-draft-z.posted.md" ] || fail "prune touched a single version or a non-draft"
[ -e "$U/sub/pr-draft-q-v1.md" ] && [ -e "$U/sub/pr-draft-q-v2.md" ] || fail "prune reached into a subfolder"
echo "ok prune scope"

TI="$T/tie"; mkdir -p "$TI"
echo a > "$TI/pr-draft-t.md"; echo b > "$TI/pr-draft-t-v1.md"
out=$("$DL" prune "$TI") || fail "a tie for newest was listed for pruning: $out"
[ "$out" = "nothing to prune" ] || fail "tie said: $out"
echo "ok prune tie"

S="$T/stems"; mkdir -p "$S"
for s in a b; do for v in 1 2; do echo "$s $v" > "$S/pr-draft-$s-v$v.md"; done; done
rc=0; out=$("$DL" prune "$S" --stem pr-draft-a) || rc=$?
[ "$rc" = 1 ] || fail "--stem run exited $rc: $out"
grep -qF "  prune  pr-draft-a-v1.md" <<<"$out" || fail "--stem did not list its stem: $out"
! grep -qF "pr-draft-b" <<<"$out" || fail "--stem listed another stem: $out"
echo "ok prune stem"

rc=0; "$DL" prune "$T/nope" >/dev/null 2>&1 || rc=$?; [ "$rc" = 2 ] || fail "missing dir exited $rc, want 2"
rc=0; "$DL" prune "$S" --yes --dry-run >/dev/null 2>&1 || rc=$?; [ "$rc" = 2 ] || fail "--yes with --dry-run exited $rc, want 2"
[ -e "$S/pr-draft-b-v1.md" ] || fail "a usage error deleted a file"
echo "ok prune usage"
