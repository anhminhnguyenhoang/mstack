### Ticket

**You own the ticket's outcome. Plan, route, review, deliver.** For work that starts from a Jira key such as `ROCM-31582` or `SILOTIGER-1164`. The ticket's folder is `~/<KEY>/`. Every artifact for the ticket lives there.

1. Run `/ticket-init <KEY>`. It loads the ticket through the Atlassian Jira MCP and writes `~/<KEY>/ticket-raw.md`, a brief of at most 150 words, and the acceptance predicate. Read all three before you route. If the folder already exists, read `ticket-raw.md`, `notes/`, and any `comment-draft-*.md` first and continue from them.
2. Check the brief against the ticket. The predicate must be a command or a number that can pass or fail. If it is not, fix it or ask the human the one question that settles it.
3. Route by the predicate:
   - A defect to reproduce and fix → **Bug fix**.
   - A kernel metric to improve against a target → **Kernel hillclimb** (`playbooks/kernel-hillclimb.md`).
   - A claim to verify, or a version matrix to run → **Repro audit** (`playbooks/repro-audit.md`).
   - A question about a number, a design, or feasibility → **Investigation**, with **benchmark-checklist** on every number.
   - A profiling artifact from the customer or a teammate → **Trace forensics**.
4. Keep artifacts in `~/<KEY>/`. Use `decision.tsv` for the decision log, `bench_*.json` for harness output, `notes/` for root causes and review notes, and `patches/` for diffs against repos you do not own. Repo changes go in a worktree of the target repo (`~/aiter`, `~/FlyDSL`), never in the ticket folder.
5. Run **Deliver**. A finding becomes `~/<KEY>/comment-draft-<topic>.md`.

**Reply:** the ticket key, the predicate and whether it holds, the artifact folder, and the draft or PR the human reviews next.
