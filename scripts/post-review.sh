#!/usr/bin/env bash
# usage: post-review.sh <owner/repo> <pr> <draft.md> <COMMENT|REQUEST_CHANGES|APPROVE>
# Posts the draft as a PR review pinned to the head SHA the draft names on its first
# `Reviewed head: <sha>` line. Refuses when the head moved, when the draft leaks a local
# path or an internal ticket key, or when this user already reviewed that head (REPOST=1).
set -euo pipefail
GH=${GH:-gh}

repo=${1:-} pr=${2:-} draft=${3:-} event=${4:-}
[[ $repo =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && $pr =~ ^[0-9]+$ && -f $draft ]] || { echo "usage: post-review.sh <owner/repo> <pr> <draft.md> <event>" >&2; exit 2; }
case "$event" in COMMENT|REQUEST_CHANGES|APPROVE) ;; *) echo "event must be COMMENT, REQUEST_CHANGES, or APPROVE" >&2; exit 2 ;; esac
reviewed=$(sed -n 's/^Reviewed head: *\([0-9a-f]\{40\}\).*/\1/p' "$draft" | head -1)
[ -n "$reviewed" ] || { echo "$draft has no 'Reviewed head: <40-hex sha>' line" >&2; exit 2; }

# Same ticket-key pattern as TICKET_KEY in check.py.
if grep -nEi "/home/[A-Za-z0-9_.-]+/|${TMPDIR:-/tmp}/review-pr-|\bSILOTIGER-[0-9]+|\bROCM-3[0-9]+" "$draft" >&2; then
  echo "the draft leaks a local path or an internal ticket key (lines above). Edit it, then post." >&2; exit 6
fi

live=$("$GH" pr view "$pr" --repo "$repo" --json headRefOid --jq .headRefOid)
[ "$live" = "$reviewed" ] || { echo "head moved: reviewed $reviewed, live $live. Re-review before posting." >&2; exit 3; }

me=$("$GH" api user --jq .login)
if [ "${REPOST:-0}" != 1 ] && "$GH" api --paginate "repos/$repo/pulls/$pr/reviews" \
     --jq ".[] | select(.user.login == \"$me\" and .commit_id == \"$reviewed\") | .id" | grep -q .; then
  echo "$me already reviewed $reviewed on $repo#$pr. REPOST=1 to post again." >&2; exit 5
fi

"$GH" api --method POST "repos/$repo/pulls/$pr/reviews" \
  -f commit_id="$reviewed" -f event="$event" -F body=@"$draft" --jq .html_url
