#!/usr/bin/env bash
# Self-checks for scripts/sync-upstream-skills.sh, pr-review.sh, post-review.sh, and the
# check.py detached-at-origin exemption. Offline: fixtures are local repos and a fake gh.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
S=$(sed -n 's/^| `pr.review` |[^|]*| `\([^`]*\)`.*/\1/p' "$ROOT/skills/ateam-mode/references/ports.md")
[ -n "$S" ] || fail "no skill bound to pr.review"
g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main "$@"; }
export MSTACK_SKILLS_DIR="$T/skills" XDG_CACHE_HOME="$T/cache"
C="$T/cache/mstack/upstream"

cat > "$T/gh" <<'EOF'
#!/usr/bin/env bash
case "$1 $2" in
  "auth status") exit "${GH_AUTH_RC:-0}" ;;
  "pr view") case "$*" in *isCrossRepository*) echo "${FORK:-false} forker bob" ;; *) echo "$LIVE_HEAD" ;; esac ;;
  "api user") echo me ;;
  "api --paginate") if [ "${EXISTING:-0}" = 1 ]; then echo 123; fi ;;
  "api --method") printf '%s\n' "$@" > "$FAKE_LOG"; echo https://example/review ;;
esac
EOF
chmod +x "$T/gh"
export GH="$T/gh" FAKE_LOG="$T/api-args"

# --- fixtures: an upstream, a user checkout with a feature worktree, a skills dir
g init -q --bare "$T/up.git"
g clone -q "$T/up.git" "$T/seed" 2>/dev/null
mkdir -p "$T/seed/.claude/skills/$S" "$T/seed/.claude/skills/other"
printf -- '---\nname: %s\ndescription: v1\n---\n' "$S" > "$T/seed/.claude/skills/$S/SKILL.md"
printf -- '---\nname: other\ndescription: v1\n---\n' > "$T/seed/.claude/skills/other/SKILL.md"
printf '#!/usr/bin/env bash\necho "pwd=$(pwd) validate=${REVIEW_AUTO_VALIDATE:-unset} args=$*"\n' > "$T/seed/.claude/skills/$S/fetch.sh"
chmod +x "$T/seed/.claude/skills/$S/fetch.sh"
g -C "$T/seed" add -A && g -C "$T/seed" commit -qm v1 && g -C "$T/seed" push -q origin main
push() { sed -i "s/description: .*/description: $1/" "$T/seed/.claude/skills/$S/SKILL.md"; g -C "$T/seed" commit -qam "$1"; g -C "$T/seed" push -q origin main; }
g clone -q "$T/up.git" "$T/checkout"
g -C "$T/checkout" worktree add -q -b feat "$T/checkout/.worktrees/feat"
mkdir "$T/skills"
ln -s "$T/checkout/.claude/skills/$S" "$T/skills/$S"
ln -s "$T/checkout/.worktrees/feat/.claude/skills/other" "$T/skills/other"
local_head=$(git -C "$T/checkout" rev-parse HEAD)

# --- sync-upstream-skills.sh
push v2
"$ROOT/scripts/sync-upstream-skills.sh" "$T/checkout" >/dev/null
snap1=$(dirname "$(dirname "$(dirname "$(readlink "$T/skills/$S")")")")
case "$snap1" in "$C/checkout-"*) ;; *) fail "link not retargeted into a snapshot: $snap1" ;; esac
grep -q v2 "$T/skills/$S/SKILL.md" || fail "link not at origin latest"
[ "$(readlink "$T/skills/other")" = "$T/checkout/.worktrees/feat/.claude/skills/other" ] || fail "feature-worktree pin was moved"
[ "$(git -C "$T/checkout" rev-parse HEAD)" = "$local_head" ] || fail "user checkout moved"

push v3
"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >/dev/null
grep -q v3 "$T/skills/$S/SKILL.md" || fail "--review-ports did not advance"
grep -q v2 "$snap1/.claude/skills/$S/SKILL.md" || fail "superseded snapshot changed under a running review"
touch -d '2 days ago' "$snap1/.superseded"
"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >/dev/null
[ ! -d "$snap1" ] || fail "day-old superseded snapshot not pruned"

mkdir "$T/empty"
out=$(MSTACK_SKILLS_DIR="$T/empty" "$ROOT/scripts/sync-upstream-skills.sh" --review-ports)
[ "$out" = "no pr.review or pr.validate skill is linked in $T/empty" ] || fail "empty skills dir: $out"
echo "ok sync"

# --- check.py: a snapshot at origin/HEAD is not a branch warning; a stale one is
out=$(cd "$ROOT" && python3 scripts/check.py --no-tests 2>&1 || true)
echo "$out" | grep -q "^WARN $S:" && fail "check.py warns on a snapshot at origin/HEAD"
snap=$(git -C "$(readlink -f "$T/skills/$S")" rev-parse --show-toplevel)
git -C "$snap" checkout -q --detach HEAD~1
out=$(cd "$ROOT" && python3 scripts/check.py --no-tests 2>&1 || true)
echo "$out" | grep -q "^WARN $S:" || fail "check.py silent on a snapshot behind origin"
git -C "$snap" checkout -q --detach origin/main
echo "ok check.py exemption"

# --- pr-review.sh
out=$("$ROOT/scripts/pr-review.sh" o/r#7 2>/dev/null)
snap=$(git -C "$(readlink -f "$T/skills/$S")" rev-parse --show-toplevel)
[ "$out" = "pwd=$snap validate=unset args=o/r#7" ] || fail "pr-review same-repo: $out"
out=$(FORK=true "$ROOT/scripts/pr-review.sh" 7 o/r 2>/dev/null)
[ "$out" = "pwd=$snap validate=0 args=7 o/r" ] || fail "fork PR code not gated: $out"
out=$(FORK=true ALLOW_FORK_CODE=1 "$ROOT/scripts/pr-review.sh" o/r#7 2>/dev/null)
[ "$out" = "pwd=$snap validate=unset args=o/r#7" ] || fail "ALLOW_FORK_CODE ignored: $out"
set +e
GH_AUTH_RC=1 "$ROOT/scripts/pr-review.sh" o/r#7 >/dev/null 2>&1; [ $? -eq 4 ] || fail "ran without gh auth"
"$ROOT/scripts/pr-review.sh" 'o/r#7;x' >/dev/null 2>&1; [ $? -eq 2 ] || fail "accepted a bad PR ref"
set -e
echo "ok pr-review"

# --- post-review.sh
sha=$(printf 'a%.0s' {1..40}) other=$(printf 'b%.0s' {1..40})
draft() { printf 'Reviewed head: %s\n\n%s\n' "$sha" "$1" > "$T/draft.md"; }
post() { LIVE_HEAD=$1 "$ROOT/scripts/post-review.sh" o/r 7 "$T/draft.md" "$2"; }
draft "body \$(touch $T/pwned)"

[ "$(post "$sha" COMMENT)" = https://example/review ] || fail "post did not return the url"
grep -qx "commit_id=$sha" "$FAKE_LOG" || fail "review not pinned to reviewed head"
grep -qx "event=COMMENT" "$FAKE_LOG" || fail "event not passed through"
grep -qx "body=@$T/draft.md" "$FAKE_LOG" || fail "body not passed as a file"
[ ! -e "$T/pwned" ] || fail "draft text was executed"
[ "$(EXISTING=1 REPOST=1 post "$sha" COMMENT)" = https://example/review ] || fail "REPOST=1 refused"
set +e
post "$other" COMMENT 2>/dev/null; [ $? -eq 3 ] || fail "posted although head moved"
post "$sha" MERGE 2>/dev/null; [ $? -eq 2 ] || fail "accepted an unknown event"
EXISTING=1 post "$sha" COMMENT 2>/dev/null; [ $? -eq 5 ] || fail "posted a second review of the same head"
LIVE_HEAD=$sha "$ROOT/scripts/post-review.sh" o/r '7/../x' "$T/draft.md" COMMENT 2>/dev/null; [ $? -eq 2 ] || fail "accepted a bad PR number"
draft "see /ho""me/someone/aiter/foo.py"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 6 ] || fail "posted a local path"
draft "tracked in SILO""TIGER-123"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 6 ] || fail "posted a ticket key"
sed -i 1d "$T/draft.md"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 2 ] || fail "posted a draft with no head line"
set -e
echo "ok post-review"
