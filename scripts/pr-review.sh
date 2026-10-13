#!/usr/bin/env bash
# usage: pr-review.sh <owner/repo#N | N [owner/repo]> [validation-report]
# Runs the pr.review skill's fetch step on origin's latest skills, from the skill's own repo.
# A fork PR's code does not run unless ALLOW_FORK_CODE=1, which the human grants.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SKILLS=${MSTACK_SKILLS_DIR:-$HOME/.claude/skills}
GH=${GH:-gh}

case "${1:-}" in */*#*) repo=${1%#*} pr=${1##*#} ;; *) pr=${1:-} repo=${2:-ROCm/aiter} ;; esac
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && $pr =~ ^[0-9]+$ ]] || { echo "usage: pr-review.sh <owner/repo#N | N [owner/repo]> [report]" >&2; exit 2; }
"$GH" auth status >/dev/null 2>&1 || { echo "gh is not signed in: run gh auth login" >&2; exit 4; }

"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >&2
s=$(sed -n 's/^| `pr\.review` |[^|]*| `\([^`]*\)`.*/\1/p' "$ROOT/skills/ateam-mode/references/ports.md")
skill=$(readlink -f "$SKILLS/$s")

read -r fork owner author < <("$GH" pr view "$pr" --repo "$repo" --json isCrossRepository,headRepositoryOwner,author \
  --jq '"\(.isCrossRepository) \(.headRepositoryOwner.login) \(.author.login)"')
if [ "$fork" = true ] && [ "${ALLOW_FORK_CODE:-0}" != 1 ]; then
  echo "fork PR from $owner by $author: its code will not run. Ask the human, then rerun with ALLOW_FORK_CODE=1." >&2
  export REVIEW_AUTO_VALIDATE=0
fi

cd "$(git -C "$skill" rev-parse --show-toplevel)"
exec "$skill/fetch.sh" "$@"
