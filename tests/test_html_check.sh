#!/usr/bin/env bash
# Self-checks for scripts/html-check.py: each static rule against a fixture page, the --rules table,
# and the --render plumbing through a fake recipe. The real Chromium render runs only when the
# recipe and a browser are installed. Offline.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $*" >&2; exit 1; }
HC="$ROOT/scripts/html-check.py"
FX="$T/fx"
mkdir -p "$FX"
REAL_PW=${HTML_CHECK_PW:-/tmp/pw}

cat > "$FX/pass.html" <<'EOF'
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>fixture</title>
<style>
:root { --bg: #14161a; --fg: #e3e6ea; color-scheme: dark; }
html, body { background: var(--bg); color: var(--fg); font: 14px sans-serif; }
html:not(.light) body { background: var(--bg); }
html.light { --bg: #ffffff; --fg: #1d2330; color-scheme: light; }
button#theme { position: fixed; top: 8px; right: 8px; }
</style>
</head>
<body>
<button id="theme" type="button">theme</button>
<canvas id="c" width="200" height="60"></canvas>
<svg width="60" height="20"><rect width="60" height="20" fill="currentColor"></rect></svg>
<script>
const T = { fg: '#e3e6ea', bar: '#1f2430' };
const root = document.documentElement;
function readTheme() {
  try { return localStorage.getItem('theme'); } catch (e) { return null; }
}
function saveTheme(v) {
  try { localStorage.setItem('theme', v); } catch (e) {}
}
function applyTheme(light) {
  root.classList.toggle('light', light);
  saveTheme(light ? 'light' : 'dark');
}
applyTheme(readTheme() === 'light');
document.getElementById('theme').addEventListener('click', () => applyTheme(!root.classList.contains('light')));
const ctx = document.getElementById('c').getContext('2d');
ctx.fillStyle = T.fg;
ctx.fillRect(0, 0, 200, 60);
</script>
</body>
</html>
EOF

mk() { sed "$2" "$FX/pass.html" > "$FX/$1.html"; cmp -s "$FX/pass.html" "$FX/$1.html" && fail "fixture $1: the sed edit changed nothing"; true; }
mk fail-external 's#</head>#<script src="https://cdn.example.com/lib.js"></script>\n<link rel="stylesheet" href="//fonts.example.com/x.css">\n<style>.x { background: url(https://cdn.example.com/a.png); }</style>\n<script>import("https://cdn.example.com/m.js");</script>\n</head>#'
mk fail-dark 's/html, body { background: var(--bg);/html, body { background: #ffffff;/'
mk fail-toggle "s/root.classList.toggle('light', light);/root.dataset.mode = light ? 'light' : 'dark';/"
mk fail-storage 's/localStorage.setItem/sessionStorage.setItem/'
mk fail-try "s/try { return localStorage.getItem('theme'); } catch (e) { return null; }/return localStorage.getItem('theme');/"
mk fail-scheme 's/ color-scheme: dark; }/ }/'
mk warn-draw "s/ctx.fillStyle = T.fg;/ctx.fillStyle = '#000';/"
mk error-page 's#</body>#<script>throw new Error("boom")</script>\n</body>#'

cat > "$FX/blank-real.html" <<'EOF'
<!doctype html>
<html><head><style>html, body { background: #14161a; color-scheme: dark; }</style></head><body></body></html>
EOF
: > "$FX/empty.html"

fail_ids() {
  printf '%s\n' "$1" | sed -n 's/^FAIL \([A-Z_]*\).*/\1/p' | sort -u | paste -sd' ' -
}

# expect_run PAGE WANT_RC WANT_IDS [flags...] runs html-check on $FX/PAGE.html and sets $out.
expect_run() {
  local page=$1 want_rc=$2 want_ids=$3 rc=0
  shift 3
  out=$("$HC" "$@" "$FX/$page.html" 2>&1) || rc=$?
  [ "$rc" = "$want_rc" ] || fail "$page: exit $rc, want $want_rc: $out"
  [ "$(fail_ids "$out")" = "$want_ids" ] || fail "$page: FAIL ids [$(fail_ids "$out")], want [$want_ids]: $out"
}

expect_run pass 0 ""
grep -q '^PASS DARK_DEFAULT$' <<<"$out" && grep -q '^PASS THEME_TRY$' <<<"$out" || fail "pass page: PASS lines missing: $out"
! grep -q '^WARN' <<<"$out" || fail "pass page has a warning: $out"
expect_run fail-external 1 SELF_CONTAINED
[ "$(grep -c '^FAIL SELF_CONTAINED' <<<"$out")" = 4 ] || fail "fail-external: want 4 loads, got: $out"
expect_run fail-dark 1 DARK_DEFAULT
expect_run fail-toggle 1 THEME_TOGGLE
expect_run fail-storage 1 THEME_STORAGE
expect_run fail-try 1 THEME_TRY
expect_run fail-scheme 1 COLOR_SCHEME
expect_run warn-draw 0 ""
grep -q '^WARN DRAW_LIGHT line [0-9]*: `#000` in drawing code' <<<"$out" || fail "warn-draw: no DRAW_LIGHT warning: $out"

"$HC" --rules | grep -q $'^RENDER_BLANK\tfail\trender\t' || fail "--rules lacks the render rows"
rc=0; "$HC" >/dev/null 2>&1 || rc=$?
[ "$rc" = 2 ] || fail "no page argument: exit $rc, want 2"
rc=0; out=$("$HC" "$FX/nope.html" 2>&1) || rc=$?
[ "$rc" = 1 ] && grep -q '^FAIL FILE missing or empty' <<<"$out" || fail "missing file: exit $rc: $out"
rc=0; out=$("$HC" "$FX/empty.html" 2>&1) || rc=$?
[ "$rc" = 1 ] && grep -q '^FAIL FILE' <<<"$out" || fail "empty file: exit $rc: $out"

if ! command -v node >/dev/null 2>&1; then
  echo "skip --render plumbing: node is not on PATH"
else
  python3 - "$T" "$HC" <<'PY' || fail "PNG writer or decoder check"
import importlib.util, struct, sys, zlib
sys.dont_write_bytecode = True
out, hc_path = sys.argv[1], sys.argv[2]

def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

def filter_row(kind, cur, prev, bpp):
    res = bytearray(len(cur))
    for i, x in enumerate(cur):
        a = cur[i - bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i - bpp] if i >= bpp else 0
        if kind == 0:
            p = 0
        elif kind == 1:
            p = a
        elif kind == 2:
            p = b
        elif kind == 3:
            p = (a + b) // 2
        else:
            q = a + b - c
            pa, pb, pc = abs(q - a), abs(q - b), abs(q - c)
            p = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
        res[i] = (x - p) & 0xFF
    return res

def write(name, w, h, pixel):
    bpp = 4
    raw = bytearray()
    prev = bytearray(w * bpp)
    for y in range(h):
        row = bytearray()
        for x in range(w):
            row += bytes(pixel(x, y))
        kind = y % 5
        raw += bytes([kind]) + filter_row(kind, row, prev, bpp)
        prev = row
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))
    with open(f"{out}/{name}", "wb") as f:
        f.write(data)

write("blank.png", 40, 30, lambda x, y: (20, 22, 26, 255))
write("content.png", 40, 30, lambda x, y: (227, 230, 234, 255) if 10 <= x < 30 and 8 <= y < 20 else (20, 22, 26, 255))
mixed = lambda x, y: ((x * 37 + y * 91) % 256, (x * x + y) % 256, (x ^ y) % 256, 255)
write("mixed.png", 40, 30, mixed)

spec = importlib.util.spec_from_file_location("html_check", hc_path)
hc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hc)
want = {bytes(mixed(x, y)) for x in range(40) for y in range(30)}
assert hc.distinct_colours(f"{out}/mixed.png", limit=10**9) == want
PY
  mkdir -p "$T/fakepw"
  cat > "$T/fakepw/render.mjs" <<'EOF'
import fs from 'fs';
const [url, out] = process.argv.slice(2);
fs.copyFileSync(process.env.FAKE_PNG, out);
console.log(JSON.stringify({ errors: process.env.FAKE_ERRORS ? [process.env.FAKE_ERRORS] : [] }));
EOF
  export HTML_CHECK_PW="$T/fakepw" FAKE_PNG="$T/content.png"
  expect_run pass 0 "" --render --shot "$T/shot.png"
  grep -q '^PASS RENDER_ERROR$' <<<"$out" && grep -q '^PASS RENDER_BLANK$' <<<"$out" || fail "render pass: PASS lines missing: $out"
  grep -q "^screenshot: $T/shot.png$" <<<"$out" && [ -f "$T/shot.png" ] || fail "render pass: no screenshot: $out"

  export FAKE_ERRORS="ReferenceError: boom is not defined"
  expect_run pass 1 RENDER_ERROR --render --shot "$T/shot.png"
  unset FAKE_ERRORS

  export FAKE_PNG="$T/blank.png"
  expect_run pass 1 RENDER_BLANK --render --shot "$T/shot.png"
  export FAKE_PNG="$T/mixed.png"
  expect_run pass 0 "" --render --shot "$T/shot.png"
  unset FAKE_PNG

  export HTML_CHECK_PW="$T/nopw" FAKE_PNG="$T/content.png"
  rc=0; out=$("$HC" --render --shot "$T/shot.png" "$FX/pass.html" 2>&1) || rc=$?
  [ "$rc" = 3 ] || fail "no recipe: exit $rc, want 3: $out"
  grep -q '^RESULT INCONCLUSIVE' <<<"$out" && grep -q '^SKIP RENDER no ' <<<"$out" || fail "no recipe: wrong message: $out"
  expect_run fail-storage 1 THEME_STORAGE --render --shot "$T/shot.png"
  unset FAKE_PNG HTML_CHECK_PW
fi

PW=$REAL_PW
if command -v node >/dev/null 2>&1 && [ -f "$PW/render.mjs" ] && compgen -G "$PW/browsers/chromium*" >/dev/null; then
  export HTML_CHECK_PW="$PW"
  expect_run pass 0 "" --render --shot "$T/real.png"
  expect_run error-page 1 RENDER_ERROR --render --shot "$T/real.png"
  rc=0; out=$("$HC" --render --shot "$T/real.png" "$FX/blank-real.html" 2>&1) || rc=$?
  [ "$rc" = 1 ] && grep -q '^FAIL RENDER_BLANK' <<<"$out" && ! grep -q '^FAIL RENDER_ERROR' <<<"$out" || fail "real blank page: exit $rc: $out"
  unset HTML_CHECK_PW
else
  echo "skip real Chromium render: needs node, $PW/render.mjs, and $PW/browsers/chromium* (install per skills/how/SKILL.md step 4)"
fi

echo "ok html-check"
