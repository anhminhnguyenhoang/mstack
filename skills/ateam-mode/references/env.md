### Kernel environment

Where kernel work runs. Read this before a GPU run, a worktree, or a PR. The **verify-gpu-kernel** skill owns the commands. This file owns the map.

```
host ──► container ──► repo path ──► test command ──► arch
```

| Host | Container | Repo on host | Repo in container | Test command | Arch |
|---|---|---|---|---|---|
| `smci355-ccs-aus-m01-21` (8 GPUs) | `silotiger-1164-mhc` (running) | `~/aiter` | `/workspaces/aiter` | `python3 op_tests/test_<op>.py` | `gfx950` (MI355X) |
| same | `silotiger-1164-mhc` | `~/aiter/.worktrees/<name>` | `/workspaces/aiter/.worktrees/<name>` | same, with `PYTHONPATH` set to the worktree | `gfx950` |
| same | `TODO` FlyDSL container (`flydsl-dev` exists, stopped) | `~/FlyDSL` | `TODO` mount path | `python3 -m pytest tests/kernels/<test>.py -q` | `gfx950` |
| same | `rocm-31582-sdpa` (defined in `~/ROCM-31582/.devcontainer`, not created on this host) | `~/ROCM-31582` | `/workspaces/ROCM-31582` | `python3 repro_version_matrix.py` | `gfx950` |
| `TODO` MI300X host | `TODO` | `TODO` | `TODO` | `TODO` | `gfx942` |

Sources.

- The host row, the container list, the mounts, and the arch come from `hostname`, `rocm-smi`, `docker ps`, `docker inspect silotiger-1164-mhc`, and `rocminfo` on this host.
- `TODO`: the SSH name `mi355x-tritoners`. It is not in `~/.ssh/config` here. Confirm it is the host above.
- `TODO`: the MI300X (`gfx942`) host. `optimize-mla-reduce-flydsl` names a container `anguyenh-mla-reduce` on GPU 5, ROCm 7.2.4, with a worktree at `/home/anguyenh/aiter-worktrees/prod-fold`. None of these exist on this host. Fill the row from the real host.
- `jdbba-autoresearch` names a container `jdbba-flydsl`. It does not exist on this host either.

Rules.

- The host has no torch. Run every test and benchmark in the container, never on the bare host.
- A container sees only its bind mounts. A path outside a mount is invisible to it.
- Use `HIP_VISIBLE_DEVICES` to pick the GPU, one per run. The container default is GPU 0, which is not necessarily idle.
- Give each worktree and each side of a comparison its own `AITER_JIT_DIR`.
- Check the arch from inside the container (`rocminfo | grep -m1 gfx`) before you trust a number.
- A ticket's scripts, artifacts, and notes live in `~/<KEY>/`, mounted at `/workspaces/<KEY>`.
