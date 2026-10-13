#!/usr/bin/env bash
# Self-checks for the review scripts, the plugin hook, and the check.py detached-at-origin
# exemption. Offline: fixtures are local repos and a fake gh.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
PORTS="$ROOT/skills/ateam-mode/references/ports.md"
S=$(sed -n 's/^| `pr.review` |[^|]*| `\([^`]*\)`.*/\1/p' "$PORTS")
V=$(sed -n 's/^| `pr.validate` |[^|]*| `\([^`]*\)`.*/\1/p' "$PORTS")
[ -n "$S" ] && [ -n "$V" ] || fail "no skill bound to pr.review or pr.validate"
g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c advice.detachedHead=false "$@"; }
H="$T/home" C="$T/cache/mstack/upstream"
mkdir -p "$H" "$T/skills"
export HOME="$H" MSTACK_SKILLS_DIR="$T/skills" XDG_CACHE_HOME="$T/cache" GH="$T/gh" FAKE_LOG="$T/payload.json"

cat > "$T/gh" <<'EOF'
#!/usr/bin/env bash
case "$*" in
  "pr view --help"*) if [ "${OLD_GH:-0}" = 0 ]; then echo "  baseRefOid"; fi ;;
  "auth status"*) exit "${GH_AUTH_RC:-0}" ;;
  *isCrossRepository*) echo "${FORK:-false} forker bob" ;;
  *"pulls/7 "*) echo "$LIVE_HEAD" ;;
  "api user"*) echo me ;;
  *"--method POST"*) while [ $# -gt 0 ]; do if [ "$1" = --input ]; then cp "$2" "$FAKE_LOG"; fi; shift; done; echo https://example/review ;;
  *pulls/7/files*) printf '%s\n' '["src/a.py","@@ -1,2 +1,4 @@\n ctx\n+new1\n+new2\n ctx2\n@@ -8,1 +10,2 @@\n ctx3\n+new3"]' ;;
  *pulls/7/reviews*) if [ "${EXISTING:-0}" = 1 ]; then printf 'me\t%s\n' "$LIVE_HEAD"; fi ;;
esac
EOF
chmod +x "$T/gh"

# --- fixtures: upstream o/r ships the review skills, upstream o/k does not
skill() { mkdir -p "$1/.claude/skills/$2"; printf -- '---\nname: %s\ndescription: v1\n---\n' "$2" > "$1/.claude/skills/$2/SKILL.md"; }
for r in r k; do g init -q --bare "$T/remotes/o/$r.git"; g clone -q "$T/remotes/o/$r.git" "$T/seed-$r" 2>/dev/null; done
skill "$T/seed-r" "$S"; skill "$T/seed-r" "$V"; skill "$T/seed-r" other; skill "$T/seed-k" kskill
printf '#!/usr/bin/env bash\necho "pwd=$(pwd) validate=${REVIEW_AUTO_VALIDATE:-unset} args=$*"\n' > "$T/seed-r/.claude/skills/$S/fetch.sh"
printf '#!/usr/bin/env bash\n[ "${FAIL_GATE:-}" != "$1" ]\n' > "$T/seed-r/.claude/skills/$S/triage.py"
printf '\n## Step 8 — Verdict\n\n```bash\n"$SKILLS_ROOT/%s/triage.py" card "$WORK/card.md" || exit 1\n"$SKILLS_ROOT/%s/triage.py" independent "$WORK/independent.txt" "$WORK/card.md" || exit 1\n```\n' "$S" "$S" >> "$T/seed-r/.claude/skills/$S/SKILL.md"
chmod +x "$T/seed-r/.claude/skills/$S/fetch.sh" "$T/seed-r/.claude/skills/$S/triage.py"
for r in r k; do g -C "$T/seed-$r" add -A && g -C "$T/seed-$r" commit -qm v1 && g -C "$T/seed-$r" push -q origin main; done
push() { sed -i "s/description: .*/description: $1/" "$T/seed-r/.claude/skills/$S/SKILL.md"; g -C "$T/seed-r" commit -qam "$1"; g -C "$T/seed-r" push -q origin main; }
g clone -q "$T/remotes/o/r.git" "$H/checkout"
g clone -q "$T/remotes/o/k.git" "$H/kcheckout"
g -C "$H/checkout" worktree add -q -b feat "$H/checkout/.worktrees/feat"
ln -s "$H/checkout/.claude/skills/$S" "$T/skills/$S"
ln -s "$H/checkout/.claude/skills/$V" "$T/skills/$V"
ln -s "$H/checkout/.worktrees/feat/.claude/skills/other" "$T/skills/other"
ln -s "$H/kcheckout/.claude/skills/kskill" "$T/skills/kskill"
local_head=$(git -C "$H/checkout" rev-parse HEAD)
snap_of() { git -C "$(readlink -f "$T/skills/$1")" rev-parse --show-toplevel; }

# --- sync-upstream-skills.sh
push v2
"$ROOT/scripts/sync-upstream-skills.sh" "$H/checkout" >/dev/null
snap1=$(snap_of "$S")
case "$snap1" in "$C/checkout-"*) ;; *) fail "link not retargeted into a snapshot: $snap1" ;; esac
grep -q v2 "$T/skills/$S/SKILL.md" || fail "link not at origin latest"
[ "$(readlink "$T/skills/other")" = "$H/checkout/.worktrees/feat/.claude/skills/other" ] || fail "feature-worktree pin was moved"
[ "$(git -C "$H/checkout" rev-parse HEAD)" = "$local_head" ] || fail "user checkout moved"

push v3
"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >/dev/null
grep -q v3 "$T/skills/$S/SKILL.md" || fail "--review-ports did not advance"
grep -q v2 "$snap1/.claude/skills/$S/SKILL.md" || fail "superseded snapshot changed under a running review"
touch -d '2 days ago' "$snap1/.superseded"
"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >/dev/null
[ ! -d "$snap1" ] || fail "day-old superseded snapshot not pruned"
[ "$(readlink "$T/skills/kskill")" = "$H/kcheckout/.claude/skills/kskill" ] || fail "--review-ports moved a link of another repo"
snap3=$(snap_of "$S")
echo unrelated > "$T/seed-r/README"; g -C "$T/seed-r" add README; g -C "$T/seed-r" commit -qm unrelated; g -C "$T/seed-r" push -q origin main
"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >/dev/null
[ "$(snap_of "$S")" = "$snap3" ] || fail "new snapshot although the skills did not change"
mkdir -p "$H/other"; g clone -q "$T/remotes/o/k.git" "$H/other/checkout"
osnap=$("$ROOT/scripts/sync-upstream-skills.sh" --no-links "$H/other/checkout" | tail -1); osnap=${osnap##*: }
push v4
"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >/dev/null
grep -q v4 "$T/skills/$S/SKILL.md" || fail "skills change did not make a new snapshot"
[ -d "$osnap" ] && [ ! -e "$osnap/.superseded" ] || fail "prune touched a snapshot of another repo with the same name"

mkdir "$T/empty"
out=$(MSTACK_SKILLS_DIR="$T/empty" "$ROOT/scripts/sync-upstream-skills.sh" --review-ports)
[ "$out" = "no pr.review or pr.validate skill is linked in $T/empty" ] || fail "empty skills dir: $out"
echo "ok sync"

# --- plugin hook: runs from the plugin root, with or without CURSOR_PLUGIN_ROOT
hook=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["hooks"]["sessionStart"][0]["command"])' "$ROOT/hooks/hooks.json")
for how in var cwd; do
  rm -rf "$H/.cache"
  if [ $how = var ]; then (cd /tmp && CURSOR_PLUGIN_ROOT="$ROOT" sh -c "$hook" >/dev/null); else (cd "$ROOT" && env -u CURSOR_PLUGIN_ROOT sh -c "$hook" >/dev/null); fi
  for _ in $(seq 50); do grep -q "^checkout at" "$H/.cache/mstack/upstream/sync.log" 2>/dev/null && break; sleep 0.2; done
  grep -q "^checkout at" "$H/.cache/mstack/upstream/sync.log" || fail "plugin hook did not sync ($how)"
  flock "$C/.lock" true
done
echo "ok hook"

# --- check.py: a snapshot whose skill matches origin/HEAD is not a branch warning; a stale one is
echo unrelated2 > "$T/seed-r/README"; g -C "$T/seed-r" commit -qam unrelated2; g -C "$T/seed-r" push -q origin main
"$ROOT/scripts/sync-upstream-skills.sh" --review-ports >/dev/null
[ "$(git -C "$(snap_of "$S")" rev-parse HEAD)" != "$(git -C "$H/checkout" rev-parse origin/main)" ] || fail "fixture: snapshot should trail origin"
out=$(cd "$ROOT" && python3 scripts/check.py --no-tests 2>&1 || true)
echo "$out" | grep -q "^WARN $S:" && fail "check.py warns on a snapshot whose skill matches origin/HEAD"
snap=$(snap_of "$S")
g -C "$snap" checkout -q --detach HEAD~1
out=$(cd "$ROOT" && python3 scripts/check.py --no-tests 2>&1 || true)
echo "$out" | grep -q "^WARN $S:" || fail "check.py silent on a snapshot behind origin"
g -C "$snap" checkout -q --detach origin/main
echo "ok check.py exemption"

# --- pr-review.sh
snap=$(snap_of "$S")
out=$("$ROOT/scripts/pr-review.sh" o/r#7 2>/dev/null) || fail "pr-review o/r exit $?"
[ "$out" = "pwd=$snap validate=unset args=o/r#7" ] || fail "repo that ships the skills: $out"
out=$("$ROOT/scripts/pr-review.sh" o/k#7 2>/dev/null) || fail "pr-review o/k exit $?, no runnable review in its snapshot"
kroot=${out#pwd=}; kroot=${kroot%% *}
case "$kroot" in "$C/kcheckout-"*) ;; *) fail "o/k not reviewed in its own snapshot: $out" ;; esac
[ "$(readlink -f "$kroot/.claude/skills/$S")" = "$(readlink -f "$T/skills/$S")" ] || fail "review skill not linked into o/k"
[ "$(readlink -f "$kroot/.claude/skills/$V")" = "$(readlink -f "$T/skills/$V")" ] || fail "validate skill not linked into o/k"
[ "$(readlink "$T/skills/kskill")" = "$H/kcheckout/.claude/skills/kskill" ] || fail "reviewing o/k moved its skill links"
out=$(FORK=true "$ROOT/scripts/pr-review.sh" 7 o/r 2>/dev/null)
[ "$out" = "pwd=$snap validate=0 args=7 o/r" ] || fail "fork PR code not gated: $out"
out=$(FORK=null "$ROOT/scripts/pr-review.sh" o/r#7 2>/dev/null)
[ "$out" = "pwd=$snap validate=0 args=o/r#7" ] || fail "an odd isCrossRepository ran the PR's code: $out"
out=$(FORK=true ALLOW_FORK_CODE=1 "$ROOT/scripts/pr-review.sh" o/r#7 2>/dev/null)
[ "$out" = "pwd=$snap validate=unset args=o/r#7" ] || fail "ALLOW_FORK_CODE ignored: $out"
g clone -q "$T/remotes/o/k.git" "$H/kcopy"
set +e
"$ROOT/scripts/pr-review.sh" o/k#7 >/dev/null 2>&1; [ $? -eq 7 ] || fail "picked one of two checkouts of o/k"
"$ROOT/scripts/pr-review.sh" o/missing#7 >/dev/null 2>&1; [ $? -eq 7 ] || fail "ran with no checkout of the repo"
GH_AUTH_RC=1 "$ROOT/scripts/pr-review.sh" o/r#7 >/dev/null 2>&1; [ $? -eq 4 ] || fail "ran without gh auth"
OLD_GH=1 "$ROOT/scripts/pr-review.sh" o/r#7 >/dev/null 2>&1; [ $? -eq 4 ] || fail "ran on a gh without baseRefOid"
"$ROOT/scripts/pr-review.sh" 'o/r#7;x' >/dev/null 2>&1; [ $? -eq 2 ] || fail "accepted a bad PR ref"
set -e
mkdir -p "$H/.cursor/mstack"
printf '## Repos\n| Repo | Path | Push remote | PR target |\n|---|---|---|---|\n| k | ~''/kcopy | origin, ssh | o/k main |\n\n## Git\n' > "$H/.cursor/mstack/env.md"
out=$("$ROOT/scripts/pr-review.sh" o/k#7 2>/dev/null) || fail "env.md Repos row not used: exit $?"
case "$out" in "pwd=$C/kcopy-"*) ;; *) fail "env.md Repos row not used: $out" ;; esac
echo "ok pr-review"

# --- panel-gate.py
sha=$(printf 'a%.0s' {1..40}) other=$(printf 'b%.0s' {1..40})
G="$ROOT/scripts/panel-gate.py"
red() { if "$@" >/dev/null 2>&1; then fail "gate stayed green: ${*:2}"; fi; }
work() {
  mkdir -p "$1"
  printf 'diff --git a/src/a.py b/src/a.py\n+new1\n' > "$1/pr.diff"
  printf '{"title": "Fix the a.py bound", "body": "Because b"}' > "$1/pr_meta.json"
  printf 'Review (advisory): ⚠️ NEEDS WORK\nValidation (deterministic): N/A — no runtime surface changed\nPerf (advisory): N/A — no runtime surface changed\n\n⚠️ first card finding\n📝 second card finding\n' > "$1/card.md"
  printf 'MERGE TARGET: base\n  read base files from there, or: git -C %s show base:<path>\n' "$(snap_of "$S")" > "$1/merge_target.txt"
}
W="$T/work"; work "$W"
pa=$("$G" prompt "$W" A)
grep -q "Fix the a.py bound" "$pa" && grep -q "+new1" "$pa" || fail "blind prompt lacks the intent or the diff"
! grep -q "card finding" "$pa" || fail "blind prompt leaks the card"
red "$G" refute-prompt "$W" A
printf 'nonce: wrong\n### 1. [warning] x\n' | red "$G" record "$W" A
nA=$(cat "$W/panel/A.nonce")
printf 'nonce: %s\n### 1. **[critical]** Overflow in a.py\nThere are no findings beyond this.\n### 2. Unlabeled finding\n' "$nA" | red "$G" record "$W" A
printf 'nonce: %s\n- Overflow in a.py (critical)\nOtherwise no findings.\n' "$nA" | red "$G" record "$W" A
printf 'Here is my review.\n\n`nonce: %s`\n## Findings\n### 1. **[Warning]**: Off by one in a.py\n### 2. [nit] Naming\n' "$nA" | "$G" record "$W" A >/dev/null || fail "a preamble before the nonce, or a bold heading, was refused"
[ "$(cut -f1,2 "$W/panel/A.ids" | tr '\t\n' ' ;')" = "A1 Warning;A2 nit;" ] || fail "loose headings not parsed: $(cat "$W/panel/A.ids")"
pr=$("$G" refute-prompt "$W" A)
grep -q "first card finding" "$pr" && grep -q "second card finding" "$pr" || fail "refute prompt lacks the card findings"
nR=$(cat "$W/panel/A.refute.nonce")
printf 'nonce: %s\nSURVIVED -- opened src/a.py: the bound is wrong\n' "$nR" | red "$G" record-refute "$W" A
printf 'nonce: %s\nSURVIVED -- opened src/a.py: the bound is wrong\nKILLED -- opened src/a.py: the name is fine\n' "$nR" | "$G" record-refute "$W" A >/dev/null
[ "$(wc -l < "$W/independent.txt")" = 2 ] || fail "independent.txt not written from the reader"
merged() { printf 'Reviewed head: %s\nReview (advisory): ⚠️ NEEDS WORK\n%s\nPerf (advisory): N/A — no runtime surface changed\n\n%s\n## Inline\n### src/a.py:2\non new1 [src: panel:A1]\n' "$sha" "${2:-Validation (deterministic): N/A — no runtime surface changed}" "$1" > "$T/draft.md"; }
merged "⚠️ first card finding [src: card, panel:A1]"
red "$G" merge "$W" "$T/draft.md"
echo "A2 DROPPED -- too short" > "$W/panel/dispositions.txt"; red "$G" merge "$W" "$T/draft.md"
echo "A2 DROPPED -- a naming nit outside what this PR changes" > "$W/panel/dispositions.txt"
merged "⚠️ first card finding [src: card, panel:A1]
📝 an untagged finding"; red "$G" merge "$W" "$T/draft.md"
merged "⚠️ first card finding [src: card, panel:A1, panel:A9]"; red "$G" merge "$W" "$T/draft.md"
merged "⚠️ first card finding [src: card, panel:A1]" "Validation (deterministic): PASS"; red "$G" merge "$W" "$T/draft.md"
merged "$(for i in 1 2 3 4 5 6; do echo "📝 note $i [src: card, panel:A1]"; done)"; red "$G" merge "$W" "$T/draft.md"
merged "⚠️ first card finding [src: card, panel:A1]"
FAIL_GATE=independent red "$G" merge "$W" "$T/draft.md"
FAIL_GATE=card red "$G" merge "$W" "$T/draft.md"
merged "⚠️ first card finding [src: card, panel:A1]
- 🔴 an untagged bullet finding"; red "$G" merge "$W" "$T/draft.md"
merged "⚠️ first card finding [src: card, panel:A1]"
"$G" merge "$W" "$T/draft.md" >/dev/null || fail "merge gate red on a complete draft"
[ "$(cat "$T/draft.md.gate")" = "$(sha256sum "$T/draft.md" | cut -d' ' -f1)" ] || fail "merge did not stamp the draft"
W3="$T/work3"; work "$W3"; "$G" prompt "$W3" A >/dev/null
printf 'nonce: %s\n### 1. [warning] Off by one in a.py\n### 2. [nit] Naming\n' "$(cat "$W3/panel/A.nonce")" | "$G" record "$W3" A >/dev/null
cp "$W/independent.txt" "$W/panel/dispositions.txt" "$W3/" && mv "$W3/dispositions.txt" "$W3/panel/"
red "$G" merge "$W3" "$T/draft.md"
W2="$T/work2"; work "$W2"; merged "⚠️ first card finding [src: card]"
red "$G" merge "$W2" "$T/draft.md" --no-panel "docs only, no code changed"
cp "$W/independent.txt" "$W2/"
red "$G" merge "$W2" "$T/draft.md" --no-panel "short"
"$G" merge "$W2" "$T/draft.md" --no-panel "docs only, no code changed" >/dev/null || fail "--no-panel with a reader stayed red"
W4="$T/work4"; work "$W4"; printf 'Validation (deterministic): N/A — no runtime surface changed\n\n⚠ plain sign\n- 🔴 bullet\n' > "$W4/card.md"
"$G" prompt "$W4" A >/dev/null; printf 'nonce: %s\nNo findings.\n' "$(cat "$W4/panel/A.nonce")" | "$G" record "$W4" A >/dev/null || fail "a bare no-findings reply was refused"
grep -q "⚠ plain sign" "$("$G" refute-prompt "$W4" A)" && grep -q "bullet" "$W4/panel/A.refute.prompt" || fail "card findings without U+FE0F or behind a bullet were missed"
W5="$T/work5"; work "$W5"; printf 'Review (advisory): ✅ NO FINDINGS\nValidation (deterministic): N/A — no runtime surface changed\nPerf (advisory): N/A — no runtime surface changed\n' > "$W5/card.md"
"$G" prompt "$W5" A >/dev/null; printf 'nonce: %s\nno findings\n' "$(cat "$W5/panel/A.nonce")" | "$G" record "$W5" A >/dev/null
"$G" refute-prompt "$W5" A >/dev/null || fail "refute-prompt red on a clean card"
grep -q "^NONE AVAILABLE -- " "$W5/independent.txt" || fail "clean card: independent.txt does not say none available"
printf 'Reviewed head: %s\nReview (advisory): ✅ NO FINDINGS\nValidation (deterministic): N/A — no runtime surface changed\nPerf (advisory): N/A — no runtime surface changed\n' "$sha" > "$T/clean.md"
"$G" merge "$W5" "$T/clean.md" >/dev/null || fail "a clean PR cannot pass the merge gate"
echo "ok panel-gate"

# --- post-review.py
draft() { printf 'Reviewed head: %s\n\n%s\n' "$sha" "$1" > "$T/draft.md"; sha256sum "$T/draft.md" | cut -d' ' -f1 > "$T/draft.md.gate"; }
post() { LIVE_HEAD=$1 "$ROOT/scripts/post-review.py" o/r 7 "$T/draft.md" "$2"; }
payload() { python3 -c 'import json,sys;print(eval(sys.argv[2], {}, {"p": json.load(open(sys.argv[1]))}))' "$FAKE_LOG" "$1"; }
draft "body \$(touch $T/pwned) [src: card]
## Inline
### src/a.py:2
on new1 [src: panel:A1]
### src/a.py:2-3
on both new lines
### src/a.py:4-10
spans the gap between hunks
### src/a.py:9
not in the diff
### other.py:1
not a changed file"

[ "$(post "$sha" COMMENT 2>/dev/null)" = https://example/review ] || fail "post did not return the url"
[ "$(payload 'p["commit_id"]')" = "$sha" ] || fail "review not pinned to reviewed head"
[ "$(payload 'p["event"]')" = COMMENT ] || fail "event not passed through"
[ "$(payload '[(c["path"], c.get("start_line"), c["line"], c["side"]) for c in p["comments"]]')" = "[('src/a.py', None, 2, 'RIGHT'), ('src/a.py', 2, 3, 'RIGHT')]" ] || fail "inline comments wrong: $(payload 'p["comments"]')"
[ "$(payload '"### Outside the diff" in p["body"] and "**src/a.py:9** not in the diff" in p["body"] and "**other.py:1**" in p["body"] and "**src/a.py:4-10** spans the gap between hunks" in p["body"]')" = True ] || fail "out-of-diff comments not moved into the body"
[ "$(payload '"## Inline" not in p["body"] and "on new1" not in p["body"]')" = True ] || fail "inline section left in the body"
[ ! -e "$T/pwned" ] || fail "draft text was executed"
[ "$(payload '"[src:" not in p["body"] and all("[src:" not in c["body"] for c in p["comments"])')" = True ] || fail "source tags were posted"
[ "$(EXISTING=1 REPOST=1 post "$sha" COMMENT 2>/dev/null)" = https://example/review ] || fail "REPOST=1 refused"
set +e
post "$other" COMMENT 2>/dev/null; [ $? -eq 3 ] || fail "posted although head moved"
post "$sha" MERGE 2>/dev/null; [ $? -eq 2 ] || fail "accepted an unknown event"
EXISTING=1 post "$sha" COMMENT 2>/dev/null; [ $? -eq 5 ] || fail "posted a second review of the same head"
LIVE_HEAD=$sha "$ROOT/scripts/post-review.py" o/r '7/../x' "$T/draft.md" COMMENT 2>/dev/null; [ $? -eq 2 ] || fail "accepted a bad PR number"
draft "see /ho""me/someone/aiter/foo.py"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 6 ] || fail "posted a local path"
draft "tracked in SILO""TIGER-123"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 6 ] || fail "posted a ticket key"
printf '# local only\nsecret-model-[0-9]+\n' > "$H/.cursor/mstack/leak-patterns.txt"
draft "tuned for Secret-Model-7"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 6 ] || fail "posted a name from leak-patterns.txt"
draft "tuned for a public model"; post "$sha" COMMENT >/dev/null 2>&1; [ $? -eq 0 ] || fail "leak-patterns.txt blocked a clean draft"
rm "$T/draft.md.gate"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 8 ] || fail "posted a draft with no merge stamp"
draft "stamped text"; echo "edited after the gate" >> "$T/draft.md"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 8 ] || fail "posted a draft edited after its stamp"
sed -i 1d "$T/draft.md"; post "$sha" COMMENT 2>/dev/null; [ $? -eq 2 ] || fail "posted a draft with no head line"
set -e
echo "ok post-review"
