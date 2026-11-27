#!/usr/bin/env python3
"""Checks a standalone HTML page against the dark-mode and self-contained rules. Exits 1 on a red check.

  html-check.py [--render] [--shot PNG] <page.html>
  html-check.py --rules

  --render     also load the page in headless Chromium with the recipe in skills/how/SKILL.md
               step 4: node $HTML_CHECK_PW/render.mjs, where HTML_CHECK_PW defaults to /tmp/pw
  --shot PNG   where --render saves its screenshot (default: html-check/<name>.png in the temp dir)
  --rules      print the RULES table and exit

Each rule prints PASS when it has no findings. Otherwise it prints one FAIL or WARN line per
finding. A warn rule never changes the exit code. The last line is RESULT.

Exit codes:
  0  no fail rule failed
  1  a fail rule failed, or the page is missing or empty
  2  usage error
  3  INCONCLUSIVE: no fail rule failed, and --render was asked for but cannot run
"""
import argparse
import collections
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from html.parser import HTMLParser

RENDER_TIMEOUT = 120
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}
REMOTE = re.compile(r"(?:https?:)?//", re.I)
REMOTE_CSS = re.compile(r"""(?:url\(\s*['"]?|@import\s+(?:url\(\s*)?['"]?)(?:https?:)?//""", re.I)
REMOTE_JS = re.compile(r"""\b(?:from|import)\s*\(?\s*['"](?:https?:)?//""")
SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script>", re.I | re.S)
STYLE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
CSS_BLOCK = re.compile(r"([^{}]+)\{([^{}]*)\}")
NOT_LIGHT = re.compile(r":not\(\s*\.light\s*\)")
DEFAULT_SELECTORS = {"html", "body", ":root"}
IGNORED_BACKGROUNDS = {"none", "transparent", "inherit", "initial", "unset"}
NAMED_COLOURS = {"black": "#000000", "white": "#ffffff"}
VAR = re.compile(r"var\(\s*(--[\w-]+)")
COLOUR = re.compile(r"#(?:[0-9a-f]{3}|[0-9a-f]{6})\b|rgba?\(\s*[\d.]+[\s,]+[\d.]+[\s,]+[\d.]+|\b(?:black|white)\b", re.I)
META_SCHEME = re.compile(r"""<meta\b[^>]*name\s*=\s*["']color-scheme["'][^>]*content\s*=\s*["'][^"']*\bdark\b""", re.I)
TOGGLE_CONTROL = re.compile(r"""<button\b|<input\b[^>]*type\s*=\s*["']?(?:checkbox|radio|button)""", re.I)
TOGGLE_CODE = re.compile(r"""classList\s*\.\s*(?:toggle|add|remove)\s*\(\s*['"]light['"]""")
GET_THEME = re.compile(r"""localStorage\s*\.\s*getItem\(\s*['"]theme['"]\s*\)""")
SET_THEME = re.compile(r"""localStorage\s*\.\s*setItem\(\s*['"]theme['"]\s*,""")
LOCAL_STORAGE = re.compile(r"\blocalStorage\b")
TRY_BEFORE = re.compile(r"\btry\s*$")
CATCH = re.compile(r"\s*catch\b")
DRAW = re.compile(
    r"fillStyle|strokeStyle|fillText|strokeText|shadowColor|addColorStop|\bfill\s*=|\bstroke\s*=|stop-color|flood-color"
    r"|\.style\.(?:fill|stroke)\b|setAttribute\(\s*['\"](?:fill|stroke)"
)
LIGHT = re.compile(
    r"#(?:fff|ffffff|000|000000|222|222222|eee|eeeeee)\b|\b(?:white|black)\b"
    r"|rgba?\(\s*(?:0|255)\s*,\s*(?:0|255)\s*,\s*(?:0|255)\s*[,)]",
    re.I,
)


class Unavailable(Exception):
    pass


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.loads = []

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for name, value in attrs:
            loads = name in ("src", "poster") or (name == "href" and tag == "link") or (name == "data" and tag == "object")
            if value and loads:
                self.loads.append((line, tag, name, value.strip()))


class Page:
    def __init__(self, text):
        self.text = text
        self.scripts = [(m.start(1), m.group(1)) for m in SCRIPT.finditer(text)]
        self.script_text = "\n".join(body for _, body in self.scripts)
        refs = Refs()
        refs.feed(text)
        self.loads = refs.loads
        self.scope = root_defaults_outside_light("\n".join(m.group(1) for m in STYLE.finditer(text)))
        self.errors = None
        self.png = None


def lineno(text, pos):
    return text.count("\n", 0, pos) + 1


def root_defaults_outside_light(css):
    background, scheme, custom = {}, {}, {}
    for m in CSS_BLOCK.finditer(CSS_COMMENT.sub("", css)):
        for raw in m.group(1).split(","):
            selector = " ".join(NOT_LIGHT.sub("", raw).split())
            if selector not in DEFAULT_SELECTORS:
                continue
            for decl in m.group(2).split(";"):
                prop, colon, value = decl.partition(":")
                prop, value = prop.strip().lower(), value.replace("!important", "").strip()
                if not colon:
                    continue
                if prop in ("background", "background-color"):
                    background[selector] = value
                elif prop == "color-scheme":
                    scheme[selector] = value
                elif prop.startswith("--"):
                    custom[prop] = value
    return {"background": background, "scheme": scheme, "custom": custom}


def resolve(value, custom):
    for _ in range(8):
        m = VAR.search(value)
        if not m:
            break
        value = custom.get(m.group(1), "")
    return value


def luminance(colour):
    colour = NAMED_COLOURS.get(colour.lower(), colour.lower())
    if colour.startswith("#"):
        h = colour[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    else:
        rgb = [float(n) for n in re.findall(r"[\d.]+", colour)[:3]]
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255


def close_of(body, i):
    depth = 0
    for j in range(i, len(body)):
        if body[j] == "{":
            depth += 1
        elif body[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return len(body)


def inside_try_with_catch(body, pos):
    depth = 0
    for i in range(pos - 1, -1, -1):
        if body[i] == "}":
            depth += 1
        elif body[i] == "{":
            if depth:
                depth -= 1
            elif TRY_BEFORE.search(body[max(0, i - 32):i]) and CATCH.match(body, close_of(body, i) + 1):
                return True
    return False


def unfilter(kind, line, prev, bpp):
    if kind == 0:
        return
    if kind not in (1, 2, 3, 4):
        raise ValueError(f"filter type {kind}")
    for i in range(len(line)):
        a = line[i - bpp] if i >= bpp else 0
        b = prev[i]
        c = prev[i - bpp] if i >= bpp else 0
        if kind == 1:
            pred = a
        elif kind == 2:
            pred = b
        elif kind == 3:
            pred = (a + b) // 2
        else:
            pred = paeth(a, b, c)
        line[i] = (line[i] + pred) & 0xFF


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def distinct_colours(path, limit=2):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG")
    pos, idat, head = 8, [], None
    while pos + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + size]
        pos += size + 12
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", body[:13])
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if head is None:
        raise ValueError("no IHDR chunk")
    width, height, depth, ctype, _, _, interlace = head
    channels = PNG_CHANNELS.get(ctype)
    if depth != 8 or channels is None or interlace:
        raise ValueError(f"unsupported PNG (bit depth {depth}, colour type {ctype}, interlace {interlace})")
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    colours, prev = set(), bytes(stride)
    for y in range(height):
        row = y * (stride + 1)
        line = bytearray(raw[row + 1:row + 1 + stride])
        unfilter(raw[row], line, prev, channels)
        for x in range(0, stride, channels):
            colours.add(bytes(line[x:x + channels]))
            if len(colours) >= limit:
                return colours
        prev = line
    return colours


def self_contained(page):
    out = [f"line {line}: <{tag} {name}> loads {value[:80]}"
           for line, tag, name, value in page.loads if REMOTE.match(value)]
    out += [f"line {lineno(page.text, m.start())}: CSS loads from a URL" for m in REMOTE_CSS.finditer(page.text)]
    out += [f"line {lineno(page.text, start + m.start())}: a script imports from a URL"
            for start, body in page.scripts for m in REMOTE_JS.finditer(body)]
    return out


def dark_default(page):
    scope = page.scope
    out, checked = [], 0
    for selector, value in scope["background"].items():
        value = resolve(value, scope["custom"])
        if value.lower() in IGNORED_BACKGROUNDS:
            continue
        checked += 1
        m = COLOUR.search(value)
        if not m:
            out.append(f"cannot read `{value}` on {selector}: use a hex or rgb() colour")
        elif luminance(m.group(0)) >= 0.5:
            out.append(f"default background {m.group(0)} on {selector} is light")
    if not checked:
        return ["no background on html, body, or :root outside .light, so the page starts light"]
    return out


def theme_toggle(page):
    out = []
    if not TOGGLE_CONTROL.search(page.text):
        out.append("no button or checkbox control")
    if not TOGGLE_CODE.search(page.script_text):
        out.append("no script adds, removes, or toggles class light")
    return out


def theme_storage(page):
    out = []
    if not GET_THEME.search(page.script_text):
        out.append("no localStorage.getItem('theme') call")
    if not SET_THEME.search(page.script_text):
        out.append("no localStorage.setItem('theme', ...) call")
    return out


def theme_try(page):
    return [f"line {lineno(page.text, start + m.start())}: localStorage is not inside a try block with a catch"
            for start, body in page.scripts for m in LOCAL_STORAGE.finditer(body)
            if not inside_try_with_catch(body, m.start())]


def color_scheme(page):
    if any("dark" in v.lower() for v in page.scope["scheme"].values()) or META_SCHEME.search(page.text):
        return []
    return ["no color-scheme with dark on html, body, or :root outside .light, and no meta color-scheme"]


def draw_light(page):
    out = []
    for n, line in enumerate(page.text.splitlines(), 1):
        m = LIGHT.search(line)
        if m and DRAW.search(line):
            out.append(f"line {n}: `{m.group(0)}` in drawing code: take the colour from the theme object")
    return out


def render_error(page):
    return [f"page error: {' '.join(str(e).split())[:200]}" for e in page.errors]


def render_blank(page):
    try:
        colours = distinct_colours(page.png)
    except (OSError, ValueError, IndexError, struct.error, zlib.error) as e:
        return [f"cannot read the screenshot: {e}"]
    return [] if len(colours) > 1 else ["the screenshot has one colour, so the page rendered blank"]


Rule = collections.namedtuple("Rule", "id level render text check")

RULES = [
    Rule("SELF_CONTAINED", "fail", False, "no script, stylesheet, image, frame, or media loads from a URL", self_contained),
    Rule("DARK_DEFAULT", "fail", False, "the background on html, body, or :root outside .light is dark", dark_default),
    Rule("THEME_TOGGLE", "fail", False, "a button or checkbox flips class light on the root element", theme_toggle),
    Rule("THEME_STORAGE", "fail", False, "the script reads and writes localStorage key theme", theme_storage),
    Rule("THEME_TRY", "fail", False, "every localStorage call sits in a try block with a catch", theme_try),
    Rule("COLOR_SCHEME", "fail", False, "color-scheme includes dark on the default background", color_scheme),
    Rule("DRAW_LIGHT", "warn", False, "no line with a canvas or SVG paint call has a hard-coded light or black colour", draw_light),
    Rule("RENDER_ERROR", "fail", True, "the headless page throws no page error", render_error),
    Rule("RENDER_BLANK", "fail", True, "the screenshot has at least two colours", render_blank),
]


def render_page(page_path, shot):
    pw = os.environ.get("HTML_CHECK_PW", "/tmp/pw")
    recipe = os.path.join(pw, "render.mjs")
    node = shutil.which("node")
    if node is None:
        raise Unavailable("node is not on PATH")
    if not os.path.isfile(recipe):
        raise Unavailable(f"no {recipe}: install the recipe in skills/how/SKILL.md step 4")
    os.makedirs(os.path.dirname(os.path.abspath(shot)), exist_ok=True)
    env = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=os.path.join(pw, "browsers"))
    url = pathlib.Path(page_path).resolve().as_uri()
    try:
        run = subprocess.run([node, recipe, url, shot], capture_output=True, text=True, env=env,
                             timeout=RENDER_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise Unavailable(f"render took more than {RENDER_TIMEOUT} s")
    if run.returncode:
        last = (run.stderr.strip().splitlines() or ["no stderr"])[-1]
        raise Unavailable(f"render exited {run.returncode}: {last}")
    try:
        return json.loads(run.stdout.strip().splitlines()[-1])["errors"]
    except (IndexError, KeyError, TypeError, ValueError):
        raise Unavailable("render printed no errors list")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", nargs="?")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--shot")
    ap.add_argument("--rules", action="store_true")
    args = ap.parse_args(argv)
    if args.rules:
        for rule in RULES:
            print(f"{rule.id}\t{rule.level}\t{'render' if rule.render else 'static'}\t{rule.text}")
        return 0
    if not args.page:
        ap.error("a page is required")
    try:
        text = pathlib.Path(args.page).read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    if not text.strip():
        print(f"FAIL FILE missing or empty: {args.page}")
        print("RESULT FAIL (1)")
        return 1
    page = Page(text)
    shot = args.shot or os.path.join(tempfile.gettempdir(), "html-check", pathlib.Path(args.page).stem + ".png")
    unavailable = None
    if args.render:
        try:
            page.errors = render_page(args.page, shot)
            page.png = shot
        except Unavailable as e:
            unavailable = str(e)
    fails = warns = 0
    for rule in RULES:
        if rule.render and page.errors is None:
            continue
        found = rule.check(page)
        if not found:
            print(f"PASS {rule.id}")
        for detail in found:
            print(f"{rule.level.upper()} {rule.id} {detail}")
            if rule.level == "fail":
                fails += 1
            else:
                warns += 1
    if unavailable:
        print(f"SKIP RENDER {unavailable}")
    if page.png:
        print(f"screenshot: {page.png}")
    if fails:
        print(f"RESULT FAIL ({fails})")
        return 1
    if unavailable:
        print("RESULT INCONCLUSIVE: --render could not run")
        return 3
    print(f"RESULT PASS ({warns} warn)" if warns else "RESULT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
