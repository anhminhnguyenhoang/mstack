# Sourced. upstream_remote <checkout>: the remote that tracks the repo's PR target. That is the
# `(remote NAME)` in the PR target column of the checkout's env.md Repos row, when the checkout
# has that remote. Otherwise origin.
upstream_remote() {
  local name
  name=$(sed -n '/^## Repos/,/^## [^R]/p' "${ENV_FILE:-$HOME/.cursor/mstack/env.md}" 2>/dev/null |
    awk -F'|' -v home="$HOME" -v want="$1" '{ p = $3; gsub(/^ +| +$/, "", p); sub(/^~/, home, p); sub(/\/$/, "", p) }
      p == want && match($5, /\(remote [A-Za-z0-9_.-]+/) { print substr($5, RSTART + 8, RLENGTH - 8); exit }')
  if [ -n "$name" ] && git -C "$1" remote get-url "$name" >/dev/null 2>&1; then echo "$name"; else echo origin; fi
}
