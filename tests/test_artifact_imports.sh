#!/usr/bin/env bash
# artifact.py keys each package's import origin as origin_<pkg>, so a package whose name is also a
# version key (flydsl) keeps both its version and its origin, and the surface gate sees the origin.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
VS="$ROOT/skills/verify-gpu-kernel/scripts"
RUN="$T/run"; mkdir -p "$RUN"
printf '[snr_db=28.40] fp8 out\n[aiter] q[checkAllclose atol=0.01 rtol=0.01 passed~]\n' > "$RUN/stdout.log"
echo "tests/kernels/test_x.py" > "$RUN/cmd.txt"
for i in 1 2 3 4 5; do printf '| m | us | TB/s |\n|---|---|---|\n| 1 | 1%s | 4.%s |\n' "$i" "$i" > "$RUN/r$i.log"; done
"$VS/gate.py" "$RUN/stdout.log" 0 --json "$RUN/gate.json" >/dev/null || fail "gate.py on a passing log"
"$VS/perf.py" --col us --key m --regime warm --rate-col TB/s --peak 8.0 --peak-source spec "$RUN"/r*.log > "$RUN/perf.json" || fail "perf.py"

facts() { printf 'feature=x\nhost=h\ncontainer=c\nimage=i\nhip_index=6\narch=gfx950\narch_expected=gfx950\nrepo=/r\nwt=/w/t\npkg=%s\nflydsl=0.4.1\n%s\nsha=abc\ndirty=0\njit_dir=/tmp/j\nsnr_required=1\n' "$1" "$2" > "$RUN/facts.env"; }
art() { "$VS/artifact.py" "$RUN" "$T/a.json" >/dev/null || fail "artifact.py ($1)"; }
field() { python3 -c 'import json,sys; a=json.load(open(sys.argv[1])); print(eval(sys.argv[2], {}, {"a": a}))' "$T/a.json" "$1"; }

facts flydsl 'origin_flydsl=/w/t/python/flydsl/__init__.py'; art flydsl
[ "$(field 'a["imports"].get("flydsl")')" = "/w/t/python/flydsl/__init__.py" ] || fail "flydsl origin not in imports: $(field 'a["imports"]')"
[ "$(field 'a["versions"]["flydsl"]')" = "0.4.1" ] || fail "flydsl version lost: $(field 'a["versions"]')"
"$VS/gates.py" "$T/a.json" >/dev/null || fail "gates.py failed a FlyDSL run imported from under wt"

facts flydsl 'origin_flydsl=/site-packages/flydsl/__init__.py'; art "flydsl outside wt"
set +e; "$VS/gates.py" "$T/a.json" >/dev/null; rc=$?; set -e
[ "$rc" = 1 ] || fail "gates.py passed a FlyDSL run imported from outside wt (rc $rc)"

facts aiter 'origin_aiter=/w/t/aiter/__init__.py'; art aiter
"$VS/gates.py" "$T/a.json" >/dev/null || fail "gates.py failed an aiter run imported from under wt"
echo "ok artifact imports"
