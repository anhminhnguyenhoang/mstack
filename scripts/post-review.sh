#!/usr/bin/env bash
# usage: post-review.sh <owner/repo> <pr> <draft.md> <COMMENT|REQUEST_CHANGES|APPROVE>
# Posts the draft as a PR review pinned to the head SHA the draft names on its first
# `Reviewed head: <sha>` line. Refuses when the PR head moved since that review.
set -euo pipefail
GH=${GH:-gh}

repo=$1 pr=$2 draft=$3 event=$4
case "$event" in COMMENT|REQUEST_CHANGES|APPROVE) ;; *) echo "event must be COMMENT, REQUEST_CHANGES, or APPROVE" >&2; exit 2 ;; esac
reviewed=$(sed -n 's/^Reviewed head: *\([0-9a-f]\{40\}\).*/\1/p' "$draft" | head -1)
[ -n "$reviewed" ] || { echo "$draft has no 'Reviewed head: <40-hex sha>' line" >&2; exit 2; }

live=$("$GH" pr view "$pr" --repo "$repo" --json headRefOid --jq .headRefOid)
[ "$live" = "$reviewed" ] || { echo "head moved: reviewed $reviewed, live $live. Re-review before posting." >&2; exit 3; }

"$GH" api --method POST "repos/$repo/pulls/$pr/reviews" \
  -f commit_id="$reviewed" -f event="$event" -F body=@"$draft" --jq .html_url
