# Incident & postmortem context

- **Jira**: look for tickets with labels such as `incident`, `regression`, `perf-regression`, `postmortem-action-item`. Check issue links of type `caused by`.
- **Confluence**: search for postmortem and RCA pages near the dates the target code was added.
- **GitHub**: look for issues and PRs titled "regression", "revert", or "hotfix". A revert followed by a re-land with a new reason is a strong signal. A perf or accuracy CI gate added in the same PR is another.
- **Slack**: search incident and escalation channels around the same dates, and search the failing shape or error string.
- **Git**: commits that say "fix for incident", "add guard", "mask the tail", or "restrict to gfx942" point at a defensive reason.

Defensive kernel code often has this shape: a masked tail, a bounds clamp, an arch gate, a fallback dispatch, a NaN or inf guard, a workspace-size check, or a perf regression test. The guard usually follows one failing run. Look for that run.
