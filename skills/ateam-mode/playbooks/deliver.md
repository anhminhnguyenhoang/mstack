### Deliver

**You own the handoff. The output decides the channel.** Invoked at the end of every other playbook. A PR is one channel, not the default.

1. Classify the output: `code`, `finding`, or `both`. A finding is a measured result, a diagnosis, a feasibility note, or a repro verdict.
2. `code` → run **Opening a PR** for the repo the change belongs to.
3. `finding` → write `~/<KEY>/comment-draft-<topic>.md`. Outside a ticket, write it in the working directory. Use this shape, then apply `/technical-writing` and `/unslop`:
   - Title as `## <the result, in one line>`, then `**TL;DR:**` in 1–2 sentences.
   - `### Why`. The question the ticket asked and why the work answers it.
   - `### Result`. The numbers with unit, run count, and spread. A table when there are two or more variants.
   - `### Evidence`. Setup (GPU, image, ROCm, torch, repo SHAs), the command that reproduces it, artifact paths, and an evidence label (measured, inferred, guess) on each claim. Caveats go here.
   - `### Next`. The action you recommend, and what stays open.
4. `both` → open the PR first. Link it in the draft's `### Evidence`.
5. Stop at the draft. The human reads and approves it. Post to Jira only after that, per the Autonomy pause list. Post only through the namespace in the `**MCP:**` line of `~/<KEY>/ticket-raw.md`. Never post, edit, or transition a ticket on your own.

**Reply:** the channel you chose and why, the PR link or the draft path, and the open decision for the human.
