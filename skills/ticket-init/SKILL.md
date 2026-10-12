---
name: ticket-init
description: "Load a Jira ticket into ~/<KEY>/ before any work. Writes ticket-raw.md, a brief of at most 150 words, and an acceptance predicate. Use for /ticket-init <KEY>, or when the user names a ticket key (ROCM-1234, SILOTIGER-1164) and no ~/<KEY>/ folder exists yet."
disable-model-invocation: true
---

# Ticket init

Turn a Jira key into a working folder and a checkable goal. This skill reads Jira. It never writes to Jira.

## 1. Resolve the key and the site

Take the key from the argument or the user's message, such as `ROCM-31582`. With no key, ask for it. The key alone does not name the Jira site. Resolve the site before any Jira call:

- A browse URL names the site. Extract the key from it.
- A bare key uses the project-prefix map in the Jira table of `~/.cursor/mstack/env.md` (written by `/setup-mstack env`).
- An unknown prefix, or a missing file, means stop. Ask the user for the browse URL, or to run `/setup-mstack env`. Do not try namespaces at random.

## 2. Load the ticket

Use the MCP namespace the Jira table maps to the site. Inspect the tool schema before the call. Use `jira_get_issue_clean` where that namespace has it, with `comment_limit` set high enough to read every comment. Elsewhere use `jira_get_issue` and read every comment. Use `jira_download_attachments` or `jira_get_issue_images` only when the description points at an attachment you need.

If the mapped namespace returns not-found, say so and ask the user. Try one other namespace only when the user agrees.

If the mapped namespace fails on auth, say which one and stop. Do not invent ticket content.

## 3. Write `~/<KEY>/ticket-raw.md`

Create `~/<KEY>/` if missing. Keep the raw text, with no summary and no edits, in this shape:

```
# <KEY>

**URL:** <browse URL>
**Site:** <site base URL>
**MCP:** <namespace used for the load>
**ID:** <id>
**Key:** <KEY>
**Summary:** <summary>
**Status:** <status>

## Description

<description as plain text>

## Comments

<author, date, body, one block per comment>
```

Later steps that touch Jira, such as Deliver, use the `**MCP:**` namespace.

Add each custom field that carries content (such as an AI insight) under its own `##` heading. Never overwrite an existing `ticket-raw.md`. Save the new load as `ticket-raw.<date>.md` and diff the two.

## 4. Write the brief and the predicate

Write `~/<KEY>/brief.md` with these parts, at most 150 words in total:

- **Ask.** What the ticket wants, in one sentence.
- **Scope.** The repos, kernels, shapes, and GPU arch it names (for example `gfx942`, `gfx950`). Say `not stated` for each one the ticket leaves out.
- **Deadline and customer impact.** As stated in the ticket.
- **Predicate.** One acceptance test that can pass or fail: a command and the number or output that counts as done. If the ticket gives none, propose one and mark it `proposed, needs human OK`.

Label each claim from the ticket as `stated`. Label your own reading as `inferred`.

## 5. Reply

Give the folder path, the brief, and the route: Bug fix, Kernel hillclimb, Repro audit, or Investigation, per the Ticket playbook (`../ateam-mode/playbooks/ticket.md`). If the ticket names a customer or an NDA model, say so. That tightens what may leave the machine, per the Autonomy section of `ateam-mode`.
