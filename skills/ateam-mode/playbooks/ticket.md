### Ticket

**You own the ticket's outcome. Plan, route, review, deliver.** For work that starts from a Jira key such as `PROJ-123`. The ticket's folder is `<tickets>/<KEY>/`, with `<tickets>` from the `tickets` resource (`../references/resources.md`). Every artifact for the ticket lives there. When the `tickets` row is `not set`, stop and ask.

1. Run `/ticket-init <KEY>`. It loads the ticket through the Atlassian Jira MCP and writes `<tickets>/<KEY>/ticket-raw.md`, a brief of at most 150 words, and the acceptance predicate. Read all three before you route. If the folder already exists, `/ticket-init` runs resume mode. Read `STATUS.md` first, then `ticket-raw.md`, `notes/`, and any `comment-draft-*.md`, and continue from them.
2. Check the brief against the ticket. The predicate must be a command or a number that can pass or fail. If it is not, fix it or ask the human the one question that settles it.
3. Route by the predicate:
   - A new kernel, a Triton port, or tuned configs to add goes to **Feature** (`playbooks/feature.md`). Its kernel steps use the `kernel.write`, `test.author`, and `config.tune` skill functions.
   - A PR to review goes to **PR review** (`playbooks/pr-review.md`).
   - A defect to reproduce and fix goes to **Bug fix**.
   - A kernel metric to improve against a target goes to **Kernel hillclimb** (`playbooks/kernel-hillclimb.md`).
   - A claim to verify, or a version matrix to run, goes to **Repro audit** (`playbooks/repro-audit.md`).
   - A redesign whose ceiling is unknown, or a feasibility question about a target, goes to **Bound probe** (`playbooks/bound-probe.md`).
   - A question about a number, a design, or feasibility goes to **Investigation**, with **benchmark-checklist** on every number.
   - A profiling artifact from the customer or a teammate goes to **Trace forensics**.
4. Keep artifacts in the ticket folder. Use `decision.tsv` for the decision log, `bench_*.json` for harness output, `notes/` for root causes and review notes, and `patches/` for diffs against repos you do not own. Repo changes go in a worktree of the target repo (from the `repos` resource), never in the ticket folder.
5. Run **Deliver**. A finding becomes `<tickets>/<KEY>/comment-draft-<topic>.md`.

#### STATUS.md

`<tickets>/<KEY>/STATUS.md` says where the ticket stands. A fresh chat reads it before anything else. It is a pointer hub. Link artifacts, never copy them. Overwrite the whole file on every update. Keep it to about 40 lines. Label a line `inferred` when no artifact backs it.

Parts, in this order:

- **Updated.** Date, and the playbook that wrote it.
- **Ask and predicate.** The ask in one sentence. The predicate. Whether it holds now: `measured` or `not yet`.
- **Best result.** The number with unit, and the artifact that holds it.
- **Open work.** One line per lever or task, with status: `open`, `running`, `done`, `dropped`. For kernel work, link the lever document `<tickets>/<KEY>/<topic>-opt.md`. Do not copy its rows.
- **Drafts awaiting approval.** The `comment-draft-*.md` files the human has not approved, and any PR draft.
- **Branches and worktrees.** Path, branch, SHA, and the container it runs in.
- **For the human.** Blockers and open questions. Write `none` when empty.
- **Next step.** One action.

**Reply:** the ticket key, the predicate and whether it holds, the artifact folder, and the draft or PR the human reviews next.
