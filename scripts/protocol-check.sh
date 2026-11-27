#!/usr/bin/env bash
# usage: protocol-check.sh SPEC.tla [--config F] [--view F] [--out DIR] [--md]
# --md prints a paste-ready block after the run: the repro line, the breaks, holds, and not-checked
# sections of report.md, and chart.mmd in a mermaid fence. The exit code is statechart's.
set -eo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SC="$ROOT/skills/statechart/scripts"
ENV_FILE=${MSTACK_ENV:-$HOME/.cursor/mstack/env.md}

fail() { echo "protocol-check: $*" >&2; exit 1; }

env_jar() {
  [ -f "$ENV_FILE" ] || return 0
  awk -F'|' '
    /^## TLA2tools[ \t]*$/ { s = 1; next }
    /^## / { s = 0 }
    s && /^\|/ {
      c = $2; gsub(/^[ `]+|[ `]+$/, "", c)
      if (c == "tla2tools") { p = $3; gsub(/^[ `]+|[ `]+$/, "", p); if (p != "not set") print p; exit }
    }' "$ENV_FILE" | sed "s|^~|$HOME|"
}

[ -x "$SC/statechart" ] || fail "no statechart at $SC/statechart"
jar=${TLA2TOOLS:-$(env_jar)}
if [ -n "$jar" ]; then
  [ -f "$jar" ] || fail "tla2tools jar not found: $jar"
  pin=$(sed -n 's/.*checksum=sha256:\([0-9a-f]\{64\}\).*/\1/p' "$SC/run.ts" | sed -n '1p')
  [ -n "$pin" ] || fail "no sha256 pin in $SC/run.ts"
  if command -v sha256sum >/dev/null 2>&1; then have=$(sha256sum "$jar" | cut -d' ' -f1)
  else have=$(shasum -a 256 "$jar" | cut -d' ' -f1); fi
  [ "$have" = "$pin" ] || fail "$jar has sha256 $have, but run.ts pins $pin. Use the tla2tools 1.7.4 jar."
  export TLA2TOOLS=$jar
else
  echo "protocol-check: no TLA2TOOLS and no tla2tools row in $ENV_FILE, so statechart uses mise" >&2
fi

md=0; args=()
for arg in "$@"; do
  if [ "$arg" = --md ]; then md=1; else args+=("$arg"); fi
done

spec=""; out=""; prev=""
for arg in "${args[@]}"; do
  case $prev in
    --out) out=$arg ;;
    --config|--view) ;;
    *)
      case $arg in
        --out=*) out=${arg#--out=} ;;
        --*) ;;
        *) [ -n "$spec" ] || spec=$arg ;;
      esac ;;
  esac
  prev=$arg
done

if [ "$md" = 0 ]; then
  exec "$SC/statechart" "${args[@]}"
fi

repro_out=""
if [ -z "$out" ]; then
  out=${spec%.tla}-chart
  repro_out=" --out <new folder>"
fi
rc=0
"$SC/statechart" "${args[@]}" 1>&2 || rc=$?

repro="scripts/protocol-check.sh"
for arg in "${args[@]}"; do repro+=" $(printf '%q' "$arg")"; done
printf '### Protocol check\n\n'
printf 'Repro: `%s%s`\n' "$repro" "$repro_out"
if [ "$rc" -le 1 ] && [ -f "$out/report.md" ]; then
  printf '\n'
  awk '
    /^## / { keep = ($0 ~ / breaks$/ || $0 ~ /^## Rules (that hold|not checked)$/); if (keep) print "##" $0; next }
    keep { print }
  ' "$out/report.md"
  if [ -f "$out/chart.mmd" ]; then
    printf '\n```mermaid\n%s\n```\n' "$(cat "$out/chart.mmd")"
  fi
else
  printf '\nNo report: the check exited %s.\n' "$rc"
fi
exit "$rc"
