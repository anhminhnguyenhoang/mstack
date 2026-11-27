#!/usr/bin/env bash
# Update this mstack checkout, then check it. Stops at the first failing step.
#
#   mstack-update.sh [--backup-dir DIR]
#
# Steps:
#   1. Preflight: this checkout is a git repo on main.
#   2. WIP backup: the untracked and uncommitted files go to DIR/mstack-wip-<date>.tgz.
#      DIR defaults to ~/.cursor/mstack/backups. The checkout keeps every file.
#   3. git pull --ff-only origin main
#   4. python3 scripts/check.py
#   5. bash tests/test_scripts.sh
#   6. python3 scripts/find-resources.py. Its remotes lines show the stale Repos rows.
#
# Exit 0: steps 1 to 5 pass, and step 6 exits 0 or 2.
# Exit 1: a step failed. Stderr names the step, with the backup when one was made.
# Preflight and argument errors print only their reason.
# Restore a backup: tar -xzf DIR/mstack-wip-<date>.tgz -C <checkout>
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
BACKUP_DIR="$HOME/.cursor/mstack/backups"
BACKUP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --backup-dir) BACKUP_DIR=${2:?"--backup-dir needs a path"}; shift 2 ;;
    *) echo "mstack-update: unknown argument: $1" >&2; exit 1 ;;
  esac
done
cd "$ROOT" || exit 1

fail() {
  echo "mstack-update: stopped at $1.${BACKUP:+ WIP backup: $BACKUP}" >&2
  exit 1
}

step() {
  local name=$1
  shift
  echo "== $name"
  "$@" || fail "$name"
}

backup() {
  local list stamp out rc
  list=$(mktemp) || return 1
  { git ls-files -z --others --exclude-standard; git diff --name-only -z HEAD; } |
    while IFS= read -r -d '' f; do
      if [ -e "$f" ]; then printf '%s\0' "$f"; fi
    done | sort -zu > "$list"
  if [ ! -s "$list" ]; then
    rm -f "$list"
    echo "no untracked or uncommitted files"
    return 0
  fi
  stamp=$(date +%Y-%m-%d-%H%M%S)
  out="$BACKUP_DIR/mstack-wip-$stamp.tgz"
  mkdir -p "$BACKUP_DIR" && tar --null -czf "$out" -T "$list"
  rc=$?
  rm -f "$list"
  [ "$rc" = 0 ] || return 1
  BACKUP=$out
  echo "backup: $BACKUP"
}

[ "$(git rev-parse --show-toplevel 2>/dev/null)" = "$ROOT" ] || { echo "mstack-update: $ROOT is not a git checkout" >&2; exit 1; }
branch=$(git branch --show-current)
[ "$branch" = main ] || { echo "mstack-update: the checkout is on '$branch', not main" >&2; exit 1; }

step "WIP backup" backup
step "git pull --ff-only" git pull --ff-only origin main
step "check.py" python3 scripts/check.py
step "tests" bash tests/test_scripts.sh
echo "== remotes (find-resources.py)"
out=$(python3 scripts/find-resources.py)
rc=$?
grep '^remotes' <<<"$out"
[ "$rc" = 0 ] || [ "$rc" = 2 ] || fail "find-resources.py (exit $rc)"
echo "mstack-update: done${BACKUP:+, WIP backup: $BACKUP}"
