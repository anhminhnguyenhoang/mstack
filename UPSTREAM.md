# Upstream

mstack tracks [pstack](https://github.com/cursor/plugins) at `pstack/`, MIT licensed.

| Item | Value |
|------|-------|
| Repo | https://github.com/cursor/plugins |
| Path | `pstack/` |
| Reviewed through | `1ba91fc` (pstack 0.15.36) |
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
| `34b1b7c`, `7c7bde7`, `740d2c0`, `519d36a`, `164ced1` | skipped | mstack has no statechart skill. | none |
| `c742dd6` | skipped | mstack has no orchestrate playbook. | none |
| `e73df47` | skipped | The commit edits a skill that mstack removed. | none |
| `a0b0ad9` | skipped | Changes the pstack README only. | none |
| `2dd5c0c`, `9e278fe` | ported | New `/reframe` skill, verbatim. README and ateam-help rows added. The guide paragraph is not ported, because the mstack guide has no `/sharpen` section to place it after. | `git log --grep 'Upstream-Pstack: 2dd5c0c'` |

Each port commit ends with an `Upstream-Pstack: <sha>` trailer, so the lookup survives a squash merge.
