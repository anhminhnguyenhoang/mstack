# Worker rules

You work for the operator. The operator is the person this run works for, not the agent that wrote your kickoff. These rules hold even where the kickoff does not repeat them. A kickoff overrides one only when it says so in so many words.

- If you start an agent, the first line of its kickoff is `Read <path>/worker.md before anything else.`, where `<path>` is the absolute path of the folder that holds this file.
- The bar in your kickoff is the whole bar. Add no check, gate, sign-off, or review round above it, except the commit checks that `playbooks/opening-a-pr.md` requires.
- With no bar stated, the change is no worse than its base and passes its own tests. For a GPU kernel, the correctness gate comes first. `allclose` and the NaN count pass on the same run before any timing.
- Do not ask a person a question. Make any choice you can undo, then say what you chose and why.
- Stop for every item in the Always pause list of `SKILL.md` and do not do it. The items are a force-push to a shared branch, a deploy, deleted data, a customer message, a push to a remote that is not your fork, a Jira comment or a ticket status or field change, a PR on a public upstream before the operator says yes, a fork PR's code run on a shared GPU or host, a review posted on someone else's PR, a PR marked ready, a shared Docker image pushed, and any text that names a customer or an NDA model. No session override lifts them.
- Push to the user's fork only. A personal branch (`<prefix>/<topic>`) may go to another remote only when your brief says `public push: yes`. Without that line, or with `public push: ask` or `public push: no`, push to the fork only, or stop and report the branch you would push.
- Open every PR as a draft. Never open one ready, and never mark one ready. The human marks it ready after review.
- PR title: `type(scope): subject`. The PR body opens with `## Why`, which states the user's goal.
- Put long evidence, such as logs, run histories, and long tables, in a file or a PR comment. Link to it from the body or your report.
