---
name: ticket-init
description: "Load a Jira ticket into ~/<KEY>/ before any work. Writes ticket-raw.md, a brief of at most 150 words, and an acceptance predicate. Use for /ticket-init <KEY>, or when the user names a ticket key (ROCM-1234, SILOTIGER-1164) and no ~/<KEY>/ folder exists yet."
disable-model-invocation: true
---

# Ticket init

Turn a Jira key into a working folder and a checkable goal. This skill reads Jira. It never writes to Jira.

## 1. Resolve the key

Take the key from the argument or the user's message, such as `ROCM-31582`. Accept a browse URL and extract the key. With no key, ask for it.

## 2. Load the ticket

Use the Atlassian Jira MCP. The default is the `mcp-amd-hub-atlassian` namespace and its `jira_get_issue_clean` tool, with `comment_limit` set high enough to read every comment. Inspect the tool schema before the call. If the key is not found there, try the other Jira namespaces from `~/.cursor/mcp.json` (`JIRA_Cloud`, `SCET`, `PLAT`). Use `jira_download_attachments` or `jira_get_issue_images` only when the description points at an attachment you need.

If every namespace fails on auth, say which one and stop. Do not invent ticket content.

## 3. Write `~/<KEY>/ticket-raw.md`

Create `~/<KEY>/` if missing. Keep the raw text, with no summary and no edits, in this shape:

```
# <KEY>

**URL:** <browse URL>
**ID:** <id>
**Key:** <KEY>
**Summary:** <summary>
**Status:** <status>

## Description

<description as plain text>

## Comments

<author, date, body, one block per comment>
```

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
