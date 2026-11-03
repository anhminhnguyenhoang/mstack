# Upstream

mstack tracks [pstack](https://github.com/cursor/plugins) at `pstack/`, MIT licensed.

| Item | Value |
|------|-------|
| Repo | https://github.com/cursor/plugins |
| Path | `pstack/` |
| Reviewed through | `1ba91fc` (pstack 0.15.36) |
| Pristine import | `1491916` (pstack 0.15.20) |

List the upstream commits after the reviewed point:

```bash
git -C /tmp/cursor-plugins log --oneline 1ba91fc..origin/main -- pstack
```

## Decisions

| Upstream commit | Decision | Reason | mstack commits |
|-----------------|----------|--------|----------------|
| `ab1f702` | ported | pstack 0.15.35 skill updates. Hunks are ported, adapted, or withheld one by one. | `git log --grep 'Upstream-Pstack: ab1f702'` |
| `34b1b7c`, `7c7bde7`, `740d2c0`, `519d36a`, `164ced1` | skipped | mstack has no statechart skill. | none |
| `c742dd6` | skipped | mstack has no orchestrate playbook. | none |
| `e73df47` | skipped | The commit edits a skill that mstack removed. | none |
| `a0b0ad9` | skipped | Changes the pstack README only. | none |

Each port commit ends with an `Upstream-Pstack: <sha>` trailer, so the lookup survives a squash merge.

The name map for porting is in the Upstream section of [`README.md`](./README.md).
