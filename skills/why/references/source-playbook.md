# Source playbooks

The why skill spawns one investigator per available evidence category. Each reads one source playbook below. For another MCP in the same category, adapt the closest playbook.

| Category | Playbook | Tools it documents |
|---|---|---|
| Code history | [`code-archaeology.md`](./sources/code-archaeology.md) | local git, in-repo files |
| Source control and PRs | [`github.md`](./sources/github.md) | `gh`, GitHub MCP |
| Issue tracker | [`jira.md`](./sources/jira.md) | Jira (Atlassian MCP) |
| Long-form documents | [`confluence.md`](./sources/confluence.md) | Confluence (Atlassian MCP) |
| Chat | [`slack.md`](./sources/slack.md) | Slack MCP |

Cross-cutting:

- [`incident-postmortem.md`](./sources/incident-postmortem.md). Add this if the target code looks defensive (masked tails, bounds clamps, arch gates, fallback dispatch, NaN or inf guards, workspace-size checks, perf regression guards, retry or timeout handling).

Kernel-relevant examples of what each category answers:

| Question | Where the answer usually lives |
|---|---|
| Why does this kernel use this tile size? | A comment or test (code history), then the PR body bench table (source control and PRs), then a tuning page (long-form documents) |
| Why does this dispatch threshold exist? | The commit that added it (code history), the review thread (source control and PRs), the ticket with the failing shape (issue tracker) |
| Why was this perf regression guard added? | The PR that added the check (source control and PRs), the regression ticket (issue tracker), the chat thread (chat) |
| Why is this path gated to one arch? | The commit message (code history), the issue with the missing instruction (source control and PRs) |
