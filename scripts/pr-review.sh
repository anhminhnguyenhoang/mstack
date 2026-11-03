#!/usr/bin/env bash
# usage: pr-review.sh <owner/repo#N | N [owner/repo]> [validation-report]
# Runs the pr.review skill's fetch step on origin's latest skills, inside a snapshot of the
# PR's own repo, so every tree check reads that repo. A repo that does not ship the review
# skills gets them linked in. A fork PR's code does not run unless ALLOW_FORK_CODE=1.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ENV_FILE=${MSTACK_ENV:-$HOME/.cursor/mstack/env.md}
env_skills_dir() { awk -F'|' '/^## /{s=/^## Skills/} s&&d==2{gsub(/^[ `]+|[ `]+$/,"",$2); if($2!="not set") print $2; exit} s&&d==1{d=2} s&&$2~/^ *Dir *$/{d=1}' "$ENV_FILE" 2>/dev/null | sed "s|^~|$HOME|"; }
SKILLS=${MSTACK_SKILLS_DIR:-$(env_skills_dir)}
SKILLS=${SKILLS:-$HOME/.claude/skills}
export MSTACK_SKILLS_DIR=$SKILLS
SKILL_FUNCTIONS="$ROOT/skills/ateam-mode/references/skill-functions.md"
GH=${GH:-gh}

case "${1:-}" in */*#*) repo=${1%#*} pr=${1##*#} ;; *) pr=${1:-} repo=${2:-ROCm/aiter} ;; esac
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && $pr =~ ^[0-9]+$ ]] || { echo "usage: pr-review.sh <owner/repo#N | N [owner/repo]> [report]" >&2; exit 2; }
grep -q baseRefOid <<<"$("$GH" pr view --help 2>&1)" || { echo "gh is too old for the review's fetch step: install gh 2.24 or later" >&2; exit 4; }
"$GH" auth status >/dev/null 2>&1 || { echo "gh is not signed in: run gh auth login, or set GH_TOKEN" >&2; exit 4; }

function_skill() { sed -n "s/^| \`pr\.$1\` |[^|]*| \`\([^\`]*\)\`.*/\1/p" "$SKILL_FUNCTIONS"; }
main_checkout() { dirname "$(git -C "$1" rev-parse --path-format=absolute --git-common-dir)"; }
. "$ROOT/scripts/upstream-remote.sh"
upstream_is() { local u; u=$(git -C "$1" remote get-url "$(upstream_remote "$1")" 2>/dev/null) || return 1; u=${u,,}; u=${u%.git}; [[ $u == *[:/]"${2,,}" ]]; }

# The local checkout whose upstream remote is $1: the Repos table of env.md, else a scan of $HOME.
checkout_of() {
  local p d found=()
  p=$(sed -n '/^## Repos/,/^## [^R]/p' "$ENV_FILE" 2>/dev/null | awk -F'|' -v r="$1" 'index(tolower($0), tolower(r)) { gsub(/^ +| +$/, "", $3); print $3; exit }')
  if [ "${p:0:1}" = "~" ]; then p="$HOME${p:1}"; fi
  if [ -n "$p" ] && upstream_is "$p" "$1"; then main_checkout "$p"; return; fi
  for d in "$HOME"/*/; do
    d=${d%/}
    if [ "$(git -C "$d" rev-parse --show-toplevel 2>/dev/null)" = "$d" ] && upstream_is "$d" "$1"; then found+=("$d"); fi
  done
  [ ${#found[@]} -eq 1 ] && { echo "${found[0]}"; return; }
  echo "need one local checkout of $1, found ${#found[@]}${found:+: ${found[*]}}. Set it in the Repos table with /setup-mstack env." >&2
  return 7
}

"$ROOT/scripts/sync-upstream-skills.sh" --review-functions >&2
review=$(function_skill review) validate=$(function_skill validate)
skill_top=$(git -C "$(readlink -f "$SKILLS/$review")" rev-parse --show-toplevel)
checkout=$(checkout_of "$repo") || exit 7

# The tree checks read the root's working tree, so it is origin's tip, not the skills snapshot,
# which stays put while the skills do. A link into the user's own worktree is a pin and wins.
case "$skill_top" in "${XDG_CACHE_HOME:-$HOME/.cache}/mstack/upstream/"*) pinned=0 ;; *) pinned=1 ;; esac
if [ "$pinned" = 1 ] && [ "$(main_checkout "$skill_top")" = "$checkout" ]; then
  root=$skill_top
else
  root=$("$ROOT/scripts/sync-upstream-skills.sh" --no-links "$checkout" | tail -1)
  root=${root##*: }
  # shortcut: the links follow the latest skills snapshot, so two reviews of one repo commit
  # that start on different skills versions share the newer one. Key the snapshot by both SHAs if that bites.
  for s in "$review" "$validate"; do
    p="$root/.claude/skills/$s"
    if [ -L "$p" ] || [ ! -d "$p" ]; then mkdir -p "${p%/*}" && ln -sfn "$(readlink -f "$SKILLS/$s")" "$p"; fi
  done
fi
echo "reviewing $repo#$pr in $root" >&2

info=$("$GH" pr view "$pr" --repo "$repo" --json isCrossRepository,headRepositoryOwner,author \
  --jq '"\(.isCrossRepository) \(.headRepositoryOwner.login) \(.author.login)"') || { echo "cannot read $repo#$pr from gh" >&2; exit 1; }
read -r fork owner author <<<"$info"
# Anything but an explicit `false` counts as a fork, so an odd gh answer never runs the PR's code.
if [ "$fork" != false ] && [ "${ALLOW_FORK_CODE:-0}" != 1 ]; then
  echo "fork PR from ${owner:-?} by ${author:-?} (isCrossRepository: ${fork:-unknown}): its code will not run. Ask the human, then rerun with ALLOW_FORK_CODE=1." >&2
  export REVIEW_AUTO_VALIDATE=0
fi

cd "$root"
exec "$root/.claude/skills/$review/fetch.sh" "$@"
