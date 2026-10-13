# Jira issues

## What this source contains

- Issues: summary, description, comments, and the status history
- Epics and sub-tasks (the broader goal against the tactical change)
- Issue links such as `blocks`, `relates to`, `duplicates`, and `caused by`
- Labels, components, and fix versions
- Remote links to PRs and Confluence pages
- Attachments such as logs and perf tables
- Development info: branches and PRs that the issue links to

Jira is where the forcing function usually lives. Examples are a shape that regressed, a model bring-up that needed a kernel, and a perf target for a release.

## How to search it

Pick the namespace first. Read the Jira table of `~/.cursor/mstack/env.md`. Map the ticket URL's site, or the key prefix of a bare key, to one namespace. If no row maps, report a gap and stop.

Inspect the tool schema with `GetDynamicTools` before the first call. Typical read tools are:

- `jira_get_issue_clean`, where present. It returns a plain-text description.
- `jira_get_issue`. Use `include` or `expand` for the changelog and remote links.
- `jira_search`, which takes JQL.
- `jira_get_issue_development_info`, where present. It lists linked branches and PRs.

Work in this order:

1. **Linked tickets first.** The seed commits and PRs may name keys such as `PROJ-123`. Fetch each one and read the comments, not only the description.
2. **Search by keyword.** Try several phrasings of the symbol, the op, and the shape.
3. **Walk the tree.** Fetch the parent epic of a sub-task. Fetch the issues it links.
4. **Check labels and fix versions.** They hint at the type of motivation and at the deadline.
5. **Read the attachments list.** A perf table attached to a ticket is often the only record of the number.

```text
text ~ "split-k" AND project = PROJ ORDER BY updated DESC
text ~ "tile" AND labels = perf AND created >= -730d
parent = PROJ-123
issue in linkedIssues(PROJ-123)
labels in (regression, perf-regression) AND text ~ "gfx950"
fixVersion = "<release>" AND component = "<component>"
```

Read only. Do not post a comment, change a status, or edit a field. Those writes need the human, per Autonomy in `ateam-mode`.

## What good evidence looks like here

- A description that states the problem: "decode shapes with small M ran 30% below the reference on gfx950".
- A comment that records a decision: "cap the tile at 128 because 256 spills past the VGPR limit".
- A `caused by` link from a regression ticket to the change that introduced it.
- A parent epic such as a model bring-up or a release perf target.
- A fix version that ties the work to a deadline.
- An attached table with shapes, arch, and numbers.

## Common pitfalls

- **Scope drift.** The ticket may be closed and reopened with a new scope. Read the whole history.
- **Template text.** A filled "Why" field with generic words ("improve performance") is not an answer.
- **Stale tickets.** Compare the ticket date with the ship date of the code.
- **Duplicate chains.** Follow `duplicates` links back to the canonical ticket.
- **Numbers without context.** A perf number with no arch, shape, or commit says little. Record what is missing.
- **Access.** A ticket you cannot open is a gap. Do not guess its content.
- **Names.** A ticket may name a customer or an NDA model. Keep the name in the finding for the user. Do not copy it into a PR, a Jira comment, or chat.

## What to return

For each relevant ticket:

- Key and title
- The motivation, quoted from the description or a comment (not paraphrased)
- Labels, components, fix version, parent, and linked issues
- Reporter, assignee, created date, and resolved date
- Link to the ticket
