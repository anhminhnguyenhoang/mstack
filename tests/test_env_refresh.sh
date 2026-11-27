#!/usr/bin/env bash
# Offline checks for find-resources.py remote refresh and mstack-update.sh.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c advice.detachedHead=false "$@"; }
H="$T/home"
mkdir -p "$H"
export HOME="$H" XDG_CACHE_HOME="$T/cache"

# --- find-resources.py: each Repos row of the env file against git remote -v
FR="$ROOT/scripts/find-resources.py" FRD="$T/fr"
mkdir -p "$FRD/hm/.cursor/mstack" "$FRD/repos"
for r in ok changed renamed bare unset; do g init -q "$FRD/repos/$r"; done
g -C "$FRD/repos/ok" remote add origin git@example.test:o/ok.git
g -C "$FRD/repos/changed" remote add origin git@example.test:o/new.git
g -C "$FRD/repos/renamed" remote add public git@example.test:o/renamed.git
g -C "$FRD/repos/unset" remote add origin git@example.test:o/unset.git
cat > "$FRD/hm/.cursor/mstack/env.md" <<EOF
# mstack environment

## Repos

| Repo | Path | Push remote (name, scheme) | PR target | Default container | Path in container | Source |
| --- | --- | --- | --- | --- | --- | --- |
| ok | $FRD/repos/ok | origin (ssh) = git@example.test:o/ok | o/ok | not set | not set | user |
| changed | $FRD/repos/changed | origin (ssh) = git@example.test:o/old.git | o/changed | not set | not set | user |
| renamed | $FRD/repos/renamed | origin (ssh) = git@example.test:o/renamed.git | o/renamed | not set | not set | user |
| gone | $FRD/repos/gone | origin (ssh) = git@example.test:o/gone.git | o/gone | not set | not set | user |
| empty |  | origin (ssh) = git@example.test:o/x.git | o/empty | not set | not set | user |
| unset | $FRD/repos/unset | not set | o/unset | not set | not set | detected |
| bare | $FRD/repos/bare | not set | o/bare | not set | not set | detected |

## Git

| Branch prefix | Public push | Source |
| --- | --- | --- |
| anguyenh | never | user |
EOF
rc=0; out=$(cd "$FRD/repos/ok" && HOME="$FRD/hm" python3 "$FR" --root "$FRD/hm" --time-limit 5) || rc=$?
[ "$rc" = 2 ] || fail "find-resources exit $rc with stale Repos rows, want 2: $out"
for line in "remotes/ok: ok: origin git@example.test:o/ok.git, matches the record" \
  "remotes/changed: changed: origin recorded git@example.test:o/old.git, live git@example.test:o/new.git" \
  "remotes/renamed: missing-remote: origin recorded, not in git remote -v" \
  "remotes/unset: unrecorded: push remote not set, live origin git@example.test:o/unset.git" \
  "remotes/bare: not set: push remote not set" \
  "remotes: 5 stale of 7 Repos rows"; do
  grep -qxF "$line" <<<"$out" || fail "find-resources line missing: $line"
done
grep -qxF "remotes/gone: no-checkout: path $FRD/repos/gone is not a git checkout" <<<"$out" || fail "find-resources lacks the no-checkout row"
grep -qxF "remotes/empty: no-checkout: path not set is not a git checkout" <<<"$out" || fail "find-resources checked the cwd for an empty path"
rc=0; (cd "$FRD/repos/ok" && HOME="$FRD/hm" python3 "$FR" --root "$FRD/hm" --json > "$FRD/out.json") || rc=$?
[ "$rc" = 2 ] || fail "find-resources --json exit $rc, want 2"
python3 - "$FRD/out.json" <<'PY' || fail "find-resources --json remotes: $(cat "$FRD/out.json")"
import json, sys
r = json.load(open(sys.argv[1]))["remotes"]
assert {x["repo"]: x["status"] for x in r["rows"]} == {"ok": "ok", "changed": "changed", "renamed": "missing-remote", "gone": "no-checkout", "empty": "no-checkout", "unset": "unrecorded", "bare": "not set"}, r["rows"]
assert r["status"] == "stale" and [x["repo"] for x in r["stale"]] == ["changed", "renamed", "gone", "empty", "unset"], r["stale"]
c = {x["repo"]: x for x in r["rows"]}
assert c["changed"]["recorded"] == "git@example.test:o/old.git" and c["changed"]["live"] == "git@example.test:o/new.git", c["changed"]
assert c["ok"]["recorded"] == "git@example.test:o/ok" and c["ok"]["live"] == "git@example.test:o/ok.git", c["ok"]
assert c["unset"]["live_remotes"] == {"origin": "git@example.test:o/unset.git"}, c["unset"]
PY
printf '## Repos\n| Repo | Path | Push remote (name, scheme) |\n|---|---|---|\n| ok | %s | origin (ssh) = git@example.test:o/ok.git |\n| bare | %s | not set |\n' "$FRD/repos/ok" "$FRD/repos/bare" > "$FRD/clean.md"
rc=0; out=$(python3 "$FR" --root "$FRD/hm" --env "$FRD/clean.md" --time-limit 5) || rc=$?
[ "$rc" = 0 ] && grep -qxF "remotes: 0 stale of 2 Repos rows" <<<"$out" || fail "clean env: exit $rc: $out"
rc=0; out=$(python3 "$FR" --root "$FRD/hm" --env "$FRD/none.md" --time-limit 5) || rc=$?
[ "$rc" = 0 ] && grep -qxF "remotes: not found" <<<"$out" || fail "missing env: exit $rc: $out"
rc=0; python3 "$FR" --bogus >/dev/null 2>&1 || rc=$?
[ "$rc" = 1 ] || fail "find-resources bad flag exit $rc, want 1"
echo "ok find-resources"
# --- mstack-update.sh: WIP backup, ff-only pull, check, tests, then the stale Repos rows
MU="$T/mu" MUG="GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t"
mu_new() {  # mu_new <case>
  local d="$MU/$1"
  mkdir -p "$d/hm/.cursor/mstack"
  g init -q --bare "$d/remote.git"
  g clone -q "$d/remote.git" "$d/seed" 2>/dev/null
  mkdir -p "$d/seed/scripts" "$d/seed/tests" "$d/seed/docs"
  cp "$ROOT/scripts/mstack-update.sh" "$ROOT/scripts/find-resources.py" "$d/seed/scripts/"
  chmod +x "$d/seed/scripts/mstack-update.sh"
  printf '%s\n' 'import os, sys' 'open(os.environ["MU_LOG"], "a").write("check\n")' 'sys.exit(1 if os.environ.get("MU_FAIL") == "check" else 0)' > "$d/seed/scripts/check.py"
  printf '%s\n' 'echo tests >> "$MU_LOG"' '[ "${MU_FAIL:-}" != tests ]' > "$d/seed/tests/test_scripts.sh"
  echo base > "$d/seed/docs/local.md"
  g -C "$d/seed" add -A && g -C "$d/seed" commit -qm base && g -C "$d/seed" push -q origin main
  g clone -q "$d/remote.git" "$d/checkout"
  g init -q "$d/repo" && g -C "$d/repo" remote add origin git@example.test:o/new.git
  printf '## Repos\n| Repo | Path | Push remote (name, scheme) |\n|---|---|---|\n| mu | %s | origin (ssh) = git@example.test:o/old.git |\n' "$d/repo" > "$d/hm/.cursor/mstack/env.md"
}
mu_upstream() {  # mu_upstream <case>
  echo new > "$MU/$1/seed/docs/new.md"
  g -C "$MU/$1/seed" add -A && g -C "$MU/$1/seed" commit -qm 'docs: new' && g -C "$MU/$1/seed" push -q origin main
}
mu_run() {  # mu_run <case> [VAR=value...]; sets $rc and $out
  local c=$1; shift
  rc=0
  out=$(cd "$MU/$c/checkout" && env $MUG HOME="$MU/$c/hm" MU_LOG="$MU/$c/calls.log" "$@" scripts/mstack-update.sh --backup-dir "$MU/$c/backups" 2>&1) || rc=$?
}
mu_new a; mu_upstream a
D="$MU/a/checkout"
echo local-edit >> "$D/docs/local.md"
echo staged > "$D/staged.txt" && git -C "$D" add staged.txt
echo notes > "$D/notes.txt"
mu_run a
[ "$rc" = 0 ] || fail "mstack-update exit $rc: $out"
[ "$(git -C "$D" rev-parse HEAD)" = "$(git -C "$MU/a/seed" rev-parse HEAD)" ] || fail "pull did not reach the upstream head"
[ "$(ls "$MU/a/backups" | grep -c '^mstack-wip-.*\.tgz$')" = 1 ] || fail "no single WIP backup: $(ls "$MU/a/backups" 2>&1)"
[ "$(tar -tzf "$MU/a"/backups/mstack-wip-*.tgz | sort | paste -sd' ')" = "docs/local.md notes.txt staged.txt" ] || fail "WIP backup holds: $(tar -tzf "$MU/a"/backups/mstack-wip-*.tgz | paste -sd' ')"
grep -q local-edit "$D/docs/local.md" && [ -e "$D/notes.txt" ] || fail "the checkout lost its WIP"
[ "$(paste -sd' ' "$MU/a/calls.log")" = "check tests" ] || fail "check and tests did not run once each: $(cat "$MU/a/calls.log")"
grep -qxF "remotes/mu: changed: origin recorded git@example.test:o/old.git, live git@example.test:o/new.git" <<<"$out" || fail "stale row not shown: $out"
mu_new b; mu_upstream b
D="$MU/b/checkout"
echo notes > "$D/notes.txt"
echo mine > "$D/docs/local.md" && g -C "$D" commit -qam 'local: edit'
git -C "$D" config pull.rebase true
before=$(git -C "$D" rev-parse HEAD)
mu_run b
[ "$rc" = 1 ] && grep -q "stopped at git pull --ff-only" <<<"$out" || fail "diverged checkout: exit $rc: $out"
[ "$(git -C "$D" rev-parse HEAD)" = "$before" ] || fail "a diverged pull changed the checkout"
[ ! -e "$MU/b/calls.log" ] || fail "check or tests ran after a failed pull"
[ "$(ls "$MU/b/backups" | grep -c '^mstack-wip-')" = 1 ] && grep -q "WIP backup: $MU/b/backups/" <<<"$out" || fail "WIP was not backed up before the failed pull: $out"
mu_new c; mu_upstream c
mu_run c MU_FAIL=check
[ "$rc" = 1 ] && grep -q "stopped at check.py" <<<"$out" || fail "check.py failure: exit $rc: $out"
[ "$(paste -sd' ' "$MU/c/calls.log")" = "check" ] || fail "tests ran after check.py failed"
! grep -q '^remotes' <<<"$out" || fail "find-resources ran after check.py failed"
mu_new d; mu_upstream d
mu_run d MU_FAIL=tests
[ "$rc" = 1 ] && grep -q "stopped at tests" <<<"$out" || fail "tests failure: exit $rc: $out"
[ "$(paste -sd' ' "$MU/d/calls.log")" = "check tests" ] || fail "tests step did not run after check.py"
! grep -q '^remotes' <<<"$out" || fail "find-resources ran after tests failed"
mu_new e; git -C "$MU/e/checkout" checkout -q -b side
mu_run e
[ "$rc" = 1 ] && grep -q "is on 'side', not main" <<<"$out" || fail "branch preflight: exit $rc: $out"
[ ! -e "$MU/e/backups" ] && [ ! -e "$MU/e/calls.log" ] || fail "a step ran on a branch that is not main"
rc=0; "$ROOT/scripts/mstack-update.sh" --bogus >/dev/null 2>&1 || rc=$?
[ "$rc" = 1 ] || fail "mstack-update bad flag exit $rc, want 1"
echo "ok mstack-update"
