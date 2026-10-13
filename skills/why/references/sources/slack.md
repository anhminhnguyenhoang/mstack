# Slack conversations

## What this source contains

- Channel threads where kernel tuning, perf regressions, and dispatch choices were argued
- Posted bench tables and trace screenshots
- Links to PRs, tickets, and pages, with the reaction to each
- Incident and escalation threads
- Reviewer and author exchanges that never reached the PR

## How to search it

Slack MCP tools vary. Check which Slack MCP is available and inspect its tool schema first. It may require `mcp_auth`. If authentication fails, stop and report the gap.

1. **Author-bounded search.** Search messages from the PR author around the PR merge date. This narrows the scope and often finds the answer.
2. **PR URL search.** Slack often links PRs when they're reviewed or discussed. Search for the PR URL (or just `/pull/<number>`).
3. **Error string search.** If the code handles a specific error, search for the error string. Incident threads often contain it.
4. **Ticket key search.** Search each key from the anchor, such as `PROJ-123`. Threads that cite a key often explain the ask behind it.
5. **Symbol and shape search.** Search the kernel name, the constant, the arch (`gfx942`, `gfx950`), and the shape. Perf threads use these words.

## Common pitfalls

- **Channel archaeology limits.** Old messages may be gone because of retention policies. If you can't find anything before a certain date, note the retention limit.
- **Unsearched DMs.** Many decisions happen in DMs that aren't searchable. You'll miss them. That's a known limitation.
- **Speculative jokes as "decisions."** Slack is casual. "Lol just do the thing" isn't a decision, even if it preceded the commit. Look for considered discussion.
- **Context collapse in single messages.** Without the thread, a single message often reads differently than in context. Always fetch threads.
- **Numbers without a run.** A number in chat may have no commit, arch, or shape. Record what is missing. Do not treat it as a measurement.
- **Names.** A thread may name a customer or an NDA model. Keep the name in the finding for the user. Do not copy it into a PR, a Jira comment, or chat.
- **Auth failures.** If the MCP isn't authenticated, stop. Don't make up findings. Report that Slack wasn't searchable.

## What to return

For each relevant thread:

- Channel, date, and permalink
- The key messages, quoted verbatim with the author
- The thread's links to PRs, tickets, and pages
- Whether the thread ended in a decision or only in discussion
