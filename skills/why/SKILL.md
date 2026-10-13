---
name: why
description: "Use for 'why does X work this way', 'why does this kernel use this tile size', 'why does this dispatch threshold exist', 'why was this perf guard added', design rationale, regressions, or postmortems. Discovers available MCPs and queries each evidence category (code history, source control and PRs, issue tracker, long-form docs, chat) in parallel, with an incident lens for defensive code, then returns a cited read on decisions and tradeoffs. Use how for runtime behavior."
disable-model-invocation: true
---

# Why

Investigate the motivation and intent behind code. The companion `how` skill answers what the code does and how it works. `why` answers what forces led to its shape.

Each spawn below names a role line in the `mstack-models.mdc` rule and a default. Set `model` to that line's value, or to the default if the rule or the line is missing. Leave `model` unset when the value is `auto` or `inherit-parent`. If the Task tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message.

Every spawn is `generalPurpose` with `readonly: false` (agent mode). **Do not use readonly/Ask mode.** It strips MCP access, which disables the MCP-backed investigators and the synthesizer's citation spot-checks. Investigators still shouldn't write anything.

## Operating posture

Operate as a **careful and precise investigator**. Be honest about what you know vs what you're inferring. Read `references/epistemics.md` for the full confidence framework and phrasing guide. The synthesizer must follow it.

## Step 1. Understand the target and the question

The **target** is usually a chunk of code, a kernel, a pattern, or a named design decision. The **question** is usually a design rationale, a tradeoff, a motivating edge case, an external constraint, dead code, or a broad history sweep.

Examples of kernel questions:

- Why does this kernel use a 128 by 128 tile?
- Why does the dispatcher send small M to a different kernel, and why at this threshold?
- Why was this perf regression guard added, and why at this tolerance?
- Why is this path gated to `gfx950`?
- Why does this tail tile keep a mask?

If the target is vague ("why do we do it this way?" with no clear referent), make your best guess from conversation context (open files, recent edits, cursor location, what was just discussed). State your interpretation briefly so the user can redirect if you're off, then proceed.

## Step 2. Establish the code anchor

Before spawning investigators, build the seed context inline: file paths and line ranges, key symbols (functions, classes, constants), the last few commits touching the target, PR numbers from merge commits (pattern `(#1234)` in the subject line), and any linked ticket IDs. Run `git blame -L <start>,<end> <file>` for last-touch commits, `git log --follow -p -- <file>` for full history with patches through renames, `git log --oneline -20 -- <file>` for recent commits with PR numbers visible, and `git log -1 --format=%B <commit>` to extract PR numbers. Then pull the PR bodies and discussion for any substantive commit: `gh pr view <number> --json title,body,author,createdAt,mergedAt,labels,closingIssuesReferences,comments,reviews`. On an MCP path, use `pull_request_read` instead, per [`pr-tool.md`](../ateam-mode/references/pr-tool.md). This anchor goes to every investigator and to the synthesizer.

## Step 3. Spawn parallel investigators

**Default to the full parallel investigation.** The goal is a complete coverage map, not a minimal one. Record empty results. Don't skip the search.

### Discovery

Before spawning investigators, list the available MCPs from the Cursor environment. Use the available-tools map when present. Otherwise inspect the `mcps/` directory Cursor exposes for enabled MCP servers.

Map each available source to one evidence category:

1. Code history (local git and in-repo files)
2. Source control and PRs (GitHub)
3. Issue tracker (Jira)
4. Long-form documents (Confluence)
5. Chat (Slack)

Incidents are not a category. They add incident-focused queries inside any category. Append `references/sources/incident-postmortem.md` to the investigator of any category when the target is defensive.

Code history is always available through local git. Source control and PRs is always available through `gh` or, when `gh` is not signed in, the GitHub MCP namespace that the PR tool table of `~/.cursor/mstack/env.md` maps to the repo. For the issue tracker and long-form documents, pick the Atlassian namespace of the ticket's site from the Jira table of the same file. For chat, use the Slack MCP. Classify any other MCP by its name, server instructions, tool names, and resource descriptors. If an MCP could fit more than one category, choose the one that matches its primary evidence. Record ambiguous cases in the coverage map.

Spawn one investigator per category that has a source, all in a single message so they run concurrently, each owning exactly one tool or MCP. Don't ask one agent to cover multiple MCPs. `model`: the `why investigators` line, default `claude-sonnet-5-5-high`.

Each investigator's prompt is `references/investigator-prompt.md` filled in, plus:
- the category playbook `references/sources/<source>.md` for the selected source, listed in `references/source-playbook.md`
- `references/sources/incident-postmortem.md` **if the target code looks defensive** (masked tails, bounds clamps, arch gates, fallback dispatch, NaN or inf guards, workspace-size checks, perf regression guards, retry or timeout handling)
- the code anchor and the user's original question

### Investigator roster, one per available evidence category

Each category below is best at finding one kind of "why", shown after "Best at". Use it to know what to expect back, to name a gap when a category returns empty, and, only in the rare provably-irrelevant case, to justify a skip.

1. **Code history** (`git log -S`, `git blame`, in-repo comments, tests, tuned configs). Always spawn. Best at *the exact change that introduced a constant, a gate, or a guard*, and at the edge cases that tests encode.
2. **Source control and PRs** (GitHub PRs, review threads, issues, CI checks). Always spawn. Best at *implementation-time rationale captured during review*, such as the bench table in a PR body or the reviewer's "why not X?".
3. **Issue tracker** (Jira). Best at *the forcing function*: a shape that regressed, a model bring-up, a release perf target. Strongest when the why is external to engineering.
4. **Long-form documents** (Confluence). Best at *design rationale written out before it became code*, such as an RFC, a perf study, or a tuning log.
5. **Chat** (Slack). Best at *real-time deliberation that never reached a doc*. Especially important when the PR, ticket, and doc trail is thin.

### When to skip an investigator

Only with an **explicit, written justification** that goes in the final Sources Consulted. Two valid reasons:

- **No MCP is available for that category** in this environment. Flag it as a gap, not a choice: "Chat skipped. No matching MCP available, so the conversational record was not searchable."
- **The source is provably irrelevant**, not just "probably irrelevant." A high bar: "Long-form documents skipped. Target is a one-line fix in a test helper."

If your scope assessment suggests a single-commit trivial target where the PR description already contains the complete answer, you may answer inline **only after** confirming all five category searches would be redundant. Say so. This should be rare.

## Step 4. Synthesize

Spawn one synthesizer. `model`: the `why synthesizer` line, default `claude-opus-5-5-xhigh`. It gets:
1. The investigator findings, including any null results and any categories skipped with justification
2. The code anchor
3. The user's original question
4. The epistemics framework from `references/epistemics.md`
5. The synthesizer prompt template from `references/synthesizer-prompt.md`

## Step 5. Present

Present the synthesizer's output to the user. You may lightly edit for clarity or add context from the conversation, but **do not rewrite the confidence language**.

## Output format

The structure is the one in `references/synthesizer-prompt.md`: The Question, The Code in Question, What We Found, What We Can Reasonably Infer, Competing Hypotheses, What We Don't Know, Sources Consulted, Confidence Summary. Adapt as needed, but keep the confidence separation intact, and keep Sources Consulted as one line per investigator, including the ones that returned nothing or were skipped, with the reason.

After Sources Consulted, if the user's `why` question is a precursor to changing this code, convert the lineage findings into a Preserve / Change / Avoid / Risk constraint set for planning the change.

## Common failure modes to avoid

- **Recency bias**. Assuming the most recent commit is authoritative. The current shape is often the result of many earlier decisions. Trace back.
