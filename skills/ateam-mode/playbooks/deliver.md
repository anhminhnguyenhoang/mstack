### Deliver

**You own the handoff. The output decides the channel.** Invoked at the end of every other playbook. A PR is one channel, not the default.

1. Classify the output: `code`, `finding`, or `both`. A finding is a measured result, a diagnosis, a feasibility note, or a repro verdict.
2. `code` → run **Opening a PR** for the repo the change belongs to.
3. `finding` → write `<tickets>/<KEY>/comment-draft-<topic>.md`. Outside a ticket, write it in the working directory. Use this shape, then apply `/technical-writing` and `/unslop`:
   - Title as `## <the result, in one line>`, then `**TL;DR:**` in 1–2 sentences.
   - `### Why`. The question the ticket asked and why the work answers it.
   - `### Result`. The numbers with unit, run count, and spread. A table when there are two or more variants. A kernel optimization result carries S* (the kept levers), its ablation table, and the gain over B.
   - `### Evidence`. Setup (GPU, image, ROCm, torch, repo SHAs), the command that reproduces it, artifact paths, and an evidence label (measured, inferred, guess) on each claim. Caveats go here. A kernel optimization result adds the retired list, each lever with its class, root cause, and `Retry if` condition, from the lever doc (`references/lever-doc.md`).
   - `### Next`. The action you recommend, and what stays open.
4. `both` → open the PR first. Link it in the draft's `### Evidence`.
5. Stop at the draft. The human reads and approves it. Post to Jira only after that, per the Autonomy pause list. Post only through the namespace in the `**MCP:**` line of `<tickets>/<KEY>/ticket-raw.md`. Never post, edit, or transition a ticket on your own.
6. In ticket work, update `<tickets>/<KEY>/STATUS.md` before the reply. Format: Ticket playbook.
7. The work may have produced a durable lesson: a lever that worked or failed with its root cause, a hardware fact, or a method. Offer the `kb.capture` port (`../references/ports.md`) only when the lesson passes the `kb` resource's own rules for what belongs there, which its index file states: it holds without this machine, ticket, or chat, and it cites a public source. The ticket record (lever doc, `STATUS.md`, numbers, shapes) stays in the ticket folder. Offer it with the source paths, in the reply. Run it only after the user says yes. The Autonomy pause on customer or NDA text still applies on top of the capture skill's own leak check. It writes to a git repo the user owns. Without a configured `kb` resource, skip this step, write `skipped kb: not set` in the reply, and ask once per session whether the user has a knowledge base (`../references/resources.md`).

**Reply:** the channel you chose and why, the PR link or the draft path, and the open decision for the human.
