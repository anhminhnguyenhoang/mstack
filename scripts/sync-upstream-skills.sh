#!/usr/bin/env bash
# usage: sync-upstream-skills.sh <checkout>...
# For each checkout, keep a pristine worktree at origin's default branch and point every
# skills-dir link into that checkout at the same path in the worktree. Idempotent.
set -euo pipefail

SKILLS=${MSTACK_SKILLS_DIR:-$HOME/.claude/skills}
CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/mstack/upstream
mkdir -p "$CACHE"
exec 9>"$CACHE/.lock"
flock -n 9 || { echo "sync already running"; exit 0; }

for repo in "$@"; do
  common=$(git -C "$repo" rev-parse --path-format=absolute --git-common-dir)
  branch=$(git -C "$repo" symbolic-ref --short refs/remotes/origin/HEAD)
  branch=${branch#origin/}
  wt="$CACHE/$(basename "$(dirname "$common")")"

  git -C "$repo" fetch -q origin "$branch"
  if [ -d "$wt" ]; then
    git -C "$wt" checkout -q -f --detach "origin/$branch"
  else
    git -C "$repo" worktree add -q --detach "$wt" "origin/$branch"
  fi

  for link in "$SKILLS"/*; do
    [ -L "$link" ] || continue
    tgt=$(readlink -f "$link") || continue
    top=$(git -C "$tgt" rev-parse --show-toplevel 2>/dev/null) || continue
    [ "$(git -C "$top" rev-parse --path-format=absolute --git-common-dir)" = "$common" ] || continue
    ln -sfn "$wt/${tgt#"$top"/}" "$link"
  done
  echo "$(basename "$wt") at $(git -C "$wt" log -1 --format='%h %cd' --date=short) (origin/$branch)"
done
