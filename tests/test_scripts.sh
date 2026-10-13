#!/usr/bin/env bash
# Self-checks for scripts/sync-upstream-skills.sh, scripts/post-review.sh, and the
# check.py detached-at-origin exemption. Offline: fixtures are local repos and a fake gh.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
S=$(sed -n 's/^| `pr.review` |[^|]*| `\([^`]*\)`.*/\1/p' "$ROOT/skills/ateam-mode/references/ports.md")
[ -n "$S" ] || fail "no skill bound to pr.review"
g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main "$@"; }

# --- sync-upstream-skills.sh
g init -q --bare "$T/up.git"
g clone -q "$T/up.git" "$T/seed" 2>/dev/null
mkdir -p "$T/seed/.claude/skills/$S"
printf -- '---\nname: $S\ndescription: v1\n---\n' > "$T/seed/.claude/skills/$S/SKILL.md"
g -C "$T/seed" add -A && g -C "$T/seed" commit -qm v1 && g -C "$T/seed" push -q origin main
g clone -q "$T/up.git" "$T/checkout"
mkdir "$T/skills" && ln -s "$T/checkout/.claude/skills/$S" "$T/skills/$S"
local_head=$(git -C "$T/checkout" rev-parse HEAD)

sed -i 's/v1/v2/' "$T/seed/.claude/skills/$S/SKILL.md"
g -C "$T/seed" commit -qam v2 && g -C "$T/seed" push -q origin main

run_sync() { MSTACK_SKILLS_DIR="$T/skills" XDG_CACHE_HOME="$T/cache" "$ROOT/scripts/sync-upstream-skills.sh" "$T/checkout" >/dev/null; }
run_sync
[ "$(readlink "$T/skills/$S")" = "$T/cache/mstack/upstream/checkout/.claude/skills/$S" ] || fail "link not retargeted"
grep -q v2 "$T/skills/$S/SKILL.md" || fail "link not at origin latest"
[ "$(git -C "$T/checkout" rev-parse HEAD)" = "$local_head" ] || fail "user checkout moved"

sed -i 's/v2/v3/' "$T/seed/.claude/skills/$S/SKILL.md"
g -C "$T/seed" commit -qam v3 && g -C "$T/seed" push -q origin main
run_sync
grep -q v3 "$T/skills/$S/SKILL.md" || fail "second sync did not advance"
echo "ok sync"

# --- check.py: a worktree detached at origin/HEAD is not a branch warning
out=$(cd "$ROOT" && MSTACK_SKILLS_DIR="$T/skills" python3 scripts/check.py 2>&1 || true)
echo "$out" | grep -q "^WARN $S:" && fail "check.py warns on detached-at-origin"
git -C "$T/cache/mstack/upstream/checkout" checkout -q --detach HEAD~1
out=$(cd "$ROOT" && MSTACK_SKILLS_DIR="$T/skills" python3 scripts/check.py 2>&1 || true)
echo "$out" | grep -q "^WARN $S:" || fail "check.py silent on detached-behind-origin"
echo "ok check.py exemption"

# --- post-review.sh with a fake gh
sha=$(printf 'a%.0s' {1..40}) other=$(printf 'b%.0s' {1..40})
cat > "$T/gh" <<EOF
#!/usr/bin/env bash
case "\$1" in
  pr) echo "\${LIVE_HEAD}" ;;
  api) printf '%s\n' "\$@" > "$T/api-args"; echo https://example/review ;;
esac
EOF
chmod +x "$T/gh"
printf 'Reviewed head: %s\n\nbody $(touch %s/pwned)\n' "$sha" "$T" > "$T/draft.md"
post() { GH="$T/gh" LIVE_HEAD=$1 "$ROOT/scripts/post-review.sh" o/r 7 "$T/draft.md" "$2"; }

[ "$(post "$sha" COMMENT)" = https://example/review ] || fail "post did not return the url"
grep -qx "commit_id=$sha" "$T/api-args" || fail "review not pinned to reviewed head"
grep -qx "event=COMMENT" "$T/api-args" || fail "event not passed through"
grep -qx "body=@$T/draft.md" "$T/api-args" || fail "body not passed as a file"
[ ! -e "$T/pwned" ] || fail "draft text was executed"
set +e
post "$other" COMMENT 2>/dev/null; [ $? -eq 3 ] || fail "posted although head moved"
post "$sha" MERGE 2>/dev/null; [ $? -eq 2 ] || fail "accepted an unknown event"
sed -i 1d "$T/draft.md"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 2 ] || fail "posted a draft with no head line"
set -e
echo "ok post-review"
