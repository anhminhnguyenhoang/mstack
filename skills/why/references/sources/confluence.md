# Confluence pages

## What this source contains

- Design docs and RFCs written before the code
- Perf studies, roofline notes, and tuning logs
- Bring-up plans and release checklists
- Meeting notes and decision records
- Page history (each version and who changed it)
- Page comments and inline comments
- Labels, attachments, and the page tree

Confluence holds long-form rationale. A design doc can state the tradeoff that no PR body does, such as why one tile shape was picked over two others.

## How to search it

Pick the namespace first. Read the Jira table of `~/.cursor/mstack/env.md` and take the Atlassian namespace of the same site. Not every Atlassian namespace has Confluence tools. If the mapped one has none, look for another namespace for the same site. If none exists, report a gap.

Inspect the tool schema with `GetDynamicTools` before the first call. Typical read tools are:

- `confluence_search`, which takes plain text or CQL.
- `confluence_get_page`, by page ID or by title and space.
- `confluence_get_page_children` and `confluence_get_space_page_tree`.
- `confluence_get_page_history` and `confluence_get_page_diff`.
- `confluence_get_comments` and `confluence_get_labels`.
- `confluence_get_attachments`.

Work in this order:

1. **Linked pages first.** A ticket or PR may link a page. Fetch it by ID.
2. **Search by keyword.** Use the symbol, the op, the shape, and the design term. Try several phrasings.
3. **Read the whole page.** Read tables, footnotes, and the "alternatives considered" section.
4. **Read the comments.** Inline comments often hold the real objection and the answer.
5. **Check the history.** The version where a number or a decision changed is evidence of when it changed.
6. **Walk the tree.** Fetch the parent and the siblings of a page. An RFC often has a results page next to it.

```text
text ~ "tile size" AND space = "<SPACE>"
title ~ "RFC*" AND text ~ "split-k"
label = "design" AND lastModified >= "2025-01-01"
text ~ "\"waves per SIMD\"" AND type = page
```

Read only. Do not create, edit, move, or delete a page.

## What good evidence looks like here

- A section named "Alternatives considered" with a stated reason for the pick.
- A perf table with arch, dtype, shapes, and the reference side.
- A threshold with its derivation, such as "route to the small-M kernel when M is at most 64".
- A bring-up plan that lists the shapes the kernel must serve.
- An inline comment where a reviewer asks "why not X?" and the author answers.

## Common pitfalls

- **Plan against ship.** A doc states the plan. The code may differ. Compare the page date with the code's ship date.
- **Stale pages.** A page not edited for a long time may describe a dropped design. Check the last version.
- **Missing context in tables.** A number with no arch or commit is weak. Record what is missing.
- **Drafts and personal spaces.** A draft may never have been agreed. Note the space and the status.
- **Search recall.** Confluence search is fuzzy. A miss does not prove no page exists. Write the exact queries you ran.
- **Names.** A page may name a customer or an NDA model. Keep the name in the finding for the user. Do not copy it into a PR, a Jira comment, or chat.

## What to return

For each relevant page:

- Title, space, and page ID
- The rationale, quoted from the page or its comments (not paraphrased)
- Author, created date, last modified date, and the version that holds the quote
- Labels and the parent page
- Link to the page
