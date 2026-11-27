#!/usr/bin/env bash
# Self-checks for scripts/protocol-touch.py and scripts/protocol-check.sh. The TLC part runs only
# when java and a tla2tools jar are available.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c advice.detachedHead=false "$@"; }
REAL_HOME=$(getent passwd "$(id -un)" | cut -d: -f6)
PT="$ROOT/scripts/protocol-touch.py" PC="$ROOT/scripts/protocol-check.sh"
PR="$T/protocol"; mkdir "$PR"; g init -q "$PR"
printf 'def kern(a, b):\n    num_stages = 2\n    acc = a + b\n    return acc\n' > "$PR/kernel.py"
g -C "$PR" add -A && g -C "$PR" commit -qm base
printf 'def kern(a, b):\n    num_stages = 3\n    acc = a + b\n    rocdl.s_barrier()\n    return acc\n' > "$PR/kernel.py"
g -C "$PR" commit -qam 'add a barrier and change the stage count'
rc=0; out=$("$PT" --repo "$PR" HEAD~1..HEAD) || rc=$?
[ "$rc" = 2 ] || fail "protocol-touch exit $rc on a barrier and a stage change, want 2"
grep -q '^protocol.check applies:$' <<<"$out" && grep -q '\[barrier\] + rocdl.s_barrier()' <<<"$out" && grep -q '\[stages\] + num_stages = 3' <<<"$out" || fail "protocol-touch hits: $out"
printf 'def kern(a, b):\n    num_stages = 3\n    acc = a * b\n    rocdl.s_barrier()\n    return acc\n' > "$PR/kernel.py"
printf 'use s_barrier here\n' > "$PR/notes.md"
g -C "$PR" add -A && g -C "$PR" commit -qm 'arithmetic only'
rc=0; out=$("$PT" --repo "$PR" HEAD~1..HEAD) || rc=$?
[ "$rc" = 0 ] && [ "$out" = "no sync change" ] || fail "protocol-touch on an arithmetic change: exit $rc, $out"
printf 'def kern(a, b):\n    num_stages = 3\n    acc = a * b\n    return acc\n' > "$PR/kernel.py"
g -C "$PR" commit -qam 'drop the barrier'
rc=0; out=$("$PT" --repo "$PR" HEAD~1..HEAD) || rc=$?
[ "$rc" = 2 ] && grep -q '\[barrier\] - rocdl.s_barrier()' <<<"$out" || fail "protocol-touch missed a removed barrier: exit $rc, $out"
rc=0; "$PT" --repo "$PR" HEAD~1 >/dev/null 2>&1 || rc=$?
[ "$rc" = 1 ] || fail "protocol-touch exit $rc on a range without .., want 1"
rc=0; "$PT" --repo "$T/none" HEAD~1..HEAD >/dev/null 2>&1 || rc=$?
[ "$rc" = 1 ] || fail "protocol-touch exit $rc on a missing repo, want 1"
REAL_ENV=${MSTACK_ENV:-$REAL_HOME/.cursor/mstack/env.md}
ENV_JAR=$(awk -F'|' '/^## TLA2tools/{s=1; next} /^## /{s=0} s && /^\|/ && $2 ~ /^ *tla2tools *$/ {p=$3; gsub(/^ +| +$/, "", p); print p; exit}' "$REAL_ENV" 2>/dev/null || true)
ENV_JAR=${ENV_JAR/#"~"/$REAL_HOME}
JAR=${TLA2TOOLS:-$ENV_JAR}
PP="$ROOT/skills/statechart/references/kernel-pingpong" SPEC="$ROOT/skills/statechart/references/kernel-pingpong/PingPong.tla"
if command -v java >/dev/null 2>&1 && [ -f "$JAR" ]; then
  printf '## TLA2tools\n\n| Resource | Path | Source |\n| --- | --- | --- |\n| tla2tools | %s | test |\n' "$JAR" > "$T/env.md"
  rc=0; out=$(env -u TLA2TOOLS MSTACK_ENV="$T/env.md" "$PC" "$SPEC" --config "$PP/nb1.cfg" --out "$T/pp1" --md 2>"$T/pp1.err") || rc=$?
  [ "$rc" = 1 ] || fail "protocol-check nb1 exit $rc, want 1: $(cat "$T/pp1.err")"
  grep -q 'NoOverwriteWhileRead breaks' <<<"$out" && grep -q 'The shortest path has 7 steps' <<<"$out" && grep -q '^```mermaid' <<<"$out" && grep -q '^### Protocol check' <<<"$out" || fail "protocol-check nb1 block: $out"
  rc=0; TLA2TOOLS="$JAR" "$PC" "$SPEC" --config "$PP/nb2.cfg" --out "$T/pp2" >"$T/pp2.out" 2>"$T/pp2.err" || rc=$?
  [ "$rc" = 0 ] || fail "protocol-check nb2 exit $rc, want 0: $(cat "$T/pp2.err")"
  holds=$(awk '/^## Rules that hold/{getline; print; exit}' "$T/pp2.out")
  [[ $holds == *NoOverwriteWhileRead* ]] || fail "protocol-check nb2 holds: $holds"
  printf 'not a jar\n' > "$T/fake.jar"
  SL="$ROOT/skills/statechart/references/search-loop"
  sl() { rc=0; out=$(TLA2TOOLS="$JAR" "$PC" "$SL/SearchLoop.tla" --config "$SL/$1.cfg" --view "$SL/view.mjs" --out "$T/sl-$1" 2>"$T/sl-$1.err") || rc=$?; }
  sl good; [ "$rc" = 0 ] && grep -q 'NeverKeepIncorrect, StopOnlyWhenDone' <<<"$out" || fail "search-loop good: exit $rc, $(cat "$T/sl-good.err")"
  sl plateau-stop; [ "$rc" = 1 ] && grep -q 'StopOnlyWhenDone breaks' <<<"$out" && ! grep -q 'NeverKeepIncorrect breaks' <<<"$out" || fail "search-loop plateau-stop: exit $rc"
  sl no-correctness-gate; [ "$rc" = 1 ] && grep -q 'NeverKeepIncorrect breaks' <<<"$out" && ! grep -q 'StopOnlyWhenDone breaks' <<<"$out" || fail "search-loop no-correctness-gate: exit $rc"
  PCMP="$ROOT/scripts/protocol-compare.py"
  rc=0; out=$(TLA2TOOLS="$JAR" "$PCMP" --base "$SPEC:$PP/nb1.cfg" --opt "$SPEC:$PP/nb2.cfg" --out "$T/cmp1" 2>&1) || rc=$?
  [ "$rc" = 0 ] && grep -q '| `NoOverwriteWhileRead` | breaks (7 steps) | holds |' <<<"$out" && grep -q 'Fixed by the optimization: NoOverwriteWhileRead' <<<"$out" || fail "protocol-compare nb1 to nb2: exit $rc, $out"
  rc=0; TLA2TOOLS="$JAR" "$PCMP" --base "$SPEC:$PP/nb2.cfg" --opt "$SPEC:$PP/nb1.cfg" --out "$T/cmp2" >/dev/null 2>&1 || rc=$?
  [ "$rc" = 1 ] || fail "protocol-compare missed a regression: exit $rc, want 1"
  rc=0; "$PCMP" --base "$T/none.tla" --opt "$T/none.tla" --out "$T/cmp3" >/dev/null 2>&1 || rc=$?
  [ "$rc" = 3 ] || fail "protocol-compare on a missing spec: exit $rc, want 3"
  rc=0; TLA2TOOLS="$T/fake.jar" "$PC" "$SPEC" --config "$PP/nb2.cfg" --out "$T/pp3" >/dev/null 2>"$T/pp3.err" || rc=$?
  [ "$rc" = 1 ] && grep -q sha256 "$T/pp3.err" && [ ! -e "$T/pp3" ] || fail "protocol-check accepted a jar with the wrong checksum (exit $rc)"
else
  echo "skip protocol-check: no java or tla2tools"
fi
echo "ok protocol"
