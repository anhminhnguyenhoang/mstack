---
name: how
description: "Use for \"how does X work\", code walkthroughs before changing something, and placement / ownership / layering questions (\"where should this live\", \"which package owns this\", \"is this the right layer\"). Explains subsystem architecture, runtime flow, onboarding mental models. Use why for motivation."
disable-model-invocation: true
---

# How

Explore the codebase to answer "how does X work?" questions. Produce architectural explanations at the level of a senior engineer onboarding onto a subsystem, enough to build a working mental model, not so much that it reads like annotated source code.

Every spawn is a Task subagent with `subagent_type: generalPurpose`. Explorers set `readonly: true`. The explainer sets `readonly: false` (agent mode), because it writes its document to a file. Explorers use the `how explorer` line in the `mstack-models.mdc` rule (default `claude-sonnet-5-5-high`), and every explainer uses the `how explainer` line (default `claude-opus-5-5-xhigh`). Set `model` to that line's value, or to the default if the rule or the line is missing. Leave `model` unset when the value is `auto` or `inherit-parent`. If the Task tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message.

## 0. Check the `kb` resource

Read the `kb` resource when it is set. Pick the role that fits the question. Read the KB index recorded in the env file, then the index of that role's folder, then the note. When a note covers the question, cite it and explore only the gap. Pass the note paths to every explorer and explainer. When `kb` or the role is missing or `not set`, say so in one line, skip this step, and ask once per session whether the user has one (`../ateam-mode/references/resources.md`).

## 1. Assess complexity

If the scope is ambiguous, state your interpretation and explore. The user can redirect.

- **Simple** (a single module, a small utility, a narrow question such as "how does function X work"): no explorers. Spawn one explainer under the Explainer contract below, built from `references/explainer-prompt.md` without the explorer-findings section. Then run steps 4 and 5.
- **Complex** (a subsystem spanning multiple files or services, a cross-cutting feature, a full architectural overview): go to step 2.

When in doubt, take the simple path.

## 2. Explore (complex only)

Decompose the question into 2 to 4 angles, each a distinct slice of the subsystem. Spawn all explorers in a single message, each with `references/explorer-prompt.md` and its angle filled in.

## 3. Synthesize (complex only)

Once all explorers have returned, spawn one explainer under the Explainer contract below, with `references/explainer-prompt.md` and every explorer's findings filled in.

## Explainer contract

- Fill `{OUTPUT_PATH}` with an absolute path to `how-<slug>.md`. Use the ticket folder in ticket work, and the work dir otherwise.
- Keep the template's Final message section. The explainer writes the document to `{OUTPUT_PATH}` and returns the `PATH:` line plus a 3-line summary. It does not return the document.
- Read the file at `{OUTPUT_PATH}` before you present anything. If the file is missing or has no sections, spawn one fresh explainer with the same prompt. If that also fails, report the failure and stop.
- Do not ask an explainer to paste the document in a later message.

## 4. Verify HTML pages

Run this step only when the output ships as a standalone HTML page, such as an explain page. The Cursor browser blocks `file://` pages, so render the page with headless Chromium and check the screenshot before you present it.

1. Install once: `mkdir -p /tmp/pw && cd /tmp/pw && npm init -y && npm i playwright@1 && PLAYWRIGHT_BROWSERS_PATH=/tmp/pw/browsers npx playwright install chromium-headless-shell`.
2. Save `/tmp/pw/render.mjs`:

```js
import { chromium } from 'playwright';
const [url, out] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
await page.goto(url);
await page.waitForTimeout(500);
await page.screenshot({ path: out, fullPage: true });
console.log(JSON.stringify({ errors }));
await browser.close();
```

3. Render: `PLAYWRIGHT_BROWSERS_PATH=/tmp/pw/browsers node /tmp/pw/render.mjs file:///abs/page.html /abs/page.png`
4. If the launch fails on a missing `.so` and you have no root, fetch its package and load it. Find the missing libraries with `ldd /tmp/pw/browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell | grep 'not found'`. For each one: `cd /tmp/pw && apt-get download <pkg> && dpkg -x <pkg>_*.deb libs && export LD_LIBRARY_PATH=/tmp/pw/libs/usr/lib/x86_64-linux-gnu`. Known mappings: `libgbm.so.1` is in `libgbm1`, and `libwayland-server.so.0` is in `libwayland-server0`.
5. Open the PNG with the Read tool. Fix any layout break or any entry in `errors`, then render again. Ship only a page with empty `errors` and a screenshot that reads right.
6. Run `python3 <plugin>/scripts/html-check.py --render <page.html>`, where `<plugin>` is the mstack plugin root, two directories above this SKILL.md. Fix every FAIL line, then run it again.

## 5. Present

Present the document read from `{OUTPUT_PATH}`. Light edits for clarity or context from the conversation are fine. Do not rewrite it. Give the path with it.

## Output format

The explanation uses the sections defined in `references/explainer-prompt.md`, dropping any that do not apply: Overview, Key Concepts, How It Works, Where Things Live, Gotchas.
