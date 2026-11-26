# Upstream

mstack tracks [pstack](https://github.com/cursor/plugins) at `pstack/`, MIT licensed.

| Item | Value |
|------|-------|
| Repo | https://github.com/cursor/plugins |
| Path | `pstack/` |
| Reviewed through | `9e278fe` (pstack 0.15.48) |
| Pristine import | `1491916` (pstack 0.15.20) |

To list the upstream commits after the reviewed point, with their mstack files, run `python3 scripts/pstack-updates.py`.

## Name map

| Upstream | mstack |
|----------|--------|
| `pstack` | `mstack` |
| `poteto-mode` | `ateam-mode` |
| `poteto-agent` | `ateam-agent` |
| `poteto-help` | `ateam-help` |
| `setup-pstack` | `setup-mstack` |

## Decisions

| Upstream commit | Decision | Reason | mstack commits |
|-----------------|----------|--------|----------------|
| `ab1f702` | ported | pstack 0.15.35 skill updates. Hunks are ported, adapted, or withheld one by one. | `git log --grep 'Upstream-Pstack: ab1f702'` |
| `34b1b7c`, `7c7bde7`, `740d2c0`, `519d36a`, `164ced1` | ported | The statechart skill, verbatim from pstack `9e278fe`, with the name map on the TLC recordings. The GPU kernel protocols section and the `tla2tools` resource are mstack's. | `git log --grep 'Upstream-Pstack: 34b1b7c'` |
| `c742dd6` | skipped | mstack has no orchestrate playbook. | none |
| `e73df47` | skipped | The commit edits a skill that mstack removed. | none |
| `a0b0ad9` | skipped | Changes the pstack README only. | none |
| `bf0c7cd` | partly ported | Ported the `sharpen` prototype line and the `reflect` synthesizer example. Skipped the one-file `why` (mstack keeps Jira, Confluence, and GitHub sources that `recall` reuses), the one-file `how` (about 14 readers and 2 role lines depend on it), the model defaults (mstack has its own model rule), and statechart. | `git log --grep 'Upstream-Pstack: bf0c7cd'` |
| `2f87c85` | partly adapted | Adapted the shorter `unslop`, `technical-writing`, and 10 principle bodies with the mstack kernel lines kept, the short Opening a PR text with PRs kept as drafts, the arena runner fallback, one ateam-mode trigger, and `worker.md` with mstack's Always-pause list. Skipped Babysit, multi-phase plan (mstack still runs `check_plan.py`), reflect without subagents, the short architect, Opus routing (mstack reads `hardest tasks`), and Orchestrate. | `git log --grep 'Upstream-Pstack: 2f87c85'` |
| `e58dd04`, `dd24b67` | skipped | Gemini arena seat. mstack has no Gemini seat. | none |
| `0b46ec3` | ported | Native Windows and TLC line ends. Kept in the verbatim statechart copy. | `git log --grep 'Upstream-Pstack: 0b46ec3'` |
| `2dd5c0c`, `9e278fe` | ported | New `/reframe` skill, verbatim. README and ateam-help rows added. The guide paragraph is not ported, because the mstack guide has no `/sharpen` section to place it after. | `git log --grep 'Upstream-Pstack: 2dd5c0c'` |

Each port commit ends with an `Upstream-Pstack: <sha>` trailer, so the lookup survives a squash merge.
