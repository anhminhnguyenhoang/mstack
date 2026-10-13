#!/usr/bin/env bash
# usage: sync-upstream-skills.sh [--no-links] <checkout>... | --review-ports
# Checks out origin's default branch of each checkout into a per-commit snapshot and points
# the skills-dir links into it. The snapshot is kept while the linked skill folders match. A review already running keeps the snapshot it started on.
# Links into a feature worktree are a deliberate pin and are left alone. --review-ports
# syncs the checkouts that ship the pr.review and pr.validate skills. --no-links only
# makes the snapshot. The last field of each output line is the snapshot path.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SKILLS=${MSTACK_SKILLS_DIR:-$HOME/.claude/skills}
CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/mstack/upstream
mkdir -p "$CACHE"
exec 9>"$CACHE/.lock"
flock -w 300 9 || { echo "sync lock busy for 300 s" >&2; exit 1; }

main_checkout() { dirname "$(git -C "$1" rev-parse --path-format=absolute --git-common-dir)"; }

links=1
if [ "${1:-}" = --no-links ]; then links=0; shift; fi
if [ "${1:-}" = --review-ports ]; then
  set --
  for s in $(sed -n 's/^| `pr\.\(review\|validate\)` |[^|]*| `\([^`]*\)`.*/\2/p' "$ROOT/skills/ateam-mode/references/ports.md"); do
    if [ -L "$SKILLS/$s" ]; then set -- "$@" "$(main_checkout "$(readlink -f "$SKILLS/$s")")"; fi
  done
  mapfile -t repos < <(printf '%s\n' "$@" | sed '/^$/d' | sort -u)
  [ ${#repos[@]} -gt 0 ] || { echo "no pr.review or pr.validate skill is linked in $SKILLS"; exit 0; }
  set -- "${repos[@]}"
fi

for repo in "$@"; do
  repo=$(main_checkout "$repo")
  common="$repo/.git"
  name=$(basename "$repo")
  branch=$(git -C "$repo" symbolic-ref --short refs/remotes/origin/HEAD)
  branch=${branch#origin/}
  git -C "$repo" fetch -q origin "$branch"
  sha=$(git -C "$repo" rev-parse "origin/$branch")
  hex12=$(printf '[0-9a-f]%.0s' {1..12})

  # Links into this repo's main checkout or its snapshots; a feature worktree is a pin.
  links_here=() paths=() cur=""
  for link in "$SKILLS"/*; do
    [ "$links" = 1 ] && [ -L "$link" ] || continue
    tgt=$(readlink -f "$link") || continue
    top=$(git -C "$tgt" rev-parse --show-toplevel 2>/dev/null) || continue
    [ "$(git -C "$top" rev-parse --path-format=absolute --git-common-dir)" = "$common" ] || continue
    case "$top" in
      "$repo") ;;
      "$CACHE/$name"-$hex12) cur=$top ;;
      *) continue ;;
    esac
    links_here+=("$link") paths+=("${tgt#"$top"/}")
  done

  # Upstream moves many times a day and the skills rarely do: keep the snapshot while they match.
  if [ -n "$cur" ] && git -C "$repo" diff --quiet "$(git -C "$cur" rev-parse HEAD)" "$sha" -- "${paths[@]}"; then
    wt=$cur
  else
    wt="$CACHE/$name-${sha:0:12}"
    [ -d "$wt" ] || git -C "$repo" worktree add -q --detach "$wt" "$sha"
  fi
  for link in "${links_here[@]}"; do
    tgt=$(readlink -f "$link"); top=$(git -C "$tgt" rev-parse --show-toplevel)
    ln -sfn "$wt/${tgt#"$top"/}" "$link"
  done

  # A superseded snapshot stays a day, so a review started on it can finish.
  for old in "$CACHE/$name"-$hex12; do
    [ -d "$old" ] && [ "$old" != "$wt" ] || continue
    [ "$(git -C "$old" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" = "$common" ] || continue
    [ -e "$old/.superseded" ] || touch "$old/.superseded"
    if [ -n "$(find "$old/.superseded" -mmin +1440)" ]; then git -C "$repo" worktree remove --force "$old"; fi
  done
  echo "$name at $(git -C "$wt" log -1 --format='%h %cd' --date=short), skills as origin/$branch ${sha:0:10}: $wt"
done
