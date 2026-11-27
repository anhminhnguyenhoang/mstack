#!/usr/bin/env bash
# Run gh with the GH_TOKEN of the repo's login in the PR tool table of env.md.
#
#   gh-as.sh [-C dir] -- <gh args>
#
# Exit 2: usage. Exit 3: shell-guard.py login found no login for the repo. Exit 4: gh gave no token.
# Otherwise, the exit code of gh.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
usage() { echo "usage: gh-as.sh [-C dir] -- <gh args>" >&2; exit 2; }

dir=.
if [ "${1:-}" = -C ]; then
  [ $# -ge 2 ] || usage
  dir=$2
  shift 2
fi
[ "${1:-}" = -- ] && [ $# -ge 2 ] || usage
shift

login=$(python3 "$here/shell-guard.py" login "$dir") || {
  echo "gh-as: env.md names no login for the origin of $dir" >&2
  exit 3
}
token=$(gh auth token -u "$login") || token=
if [ -z "$token" ]; then
  echo "gh-as: gh gave no token for login $login. Sign in as $login with gh auth login, then retry." >&2
  exit 4
fi
GH_TOKEN=$token exec gh "$@"
