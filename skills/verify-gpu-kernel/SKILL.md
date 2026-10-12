---
name: verify-gpu-kernel
description: "Drive a GPU kernel the way CI does: resolve the host and container, lock one idle AMD GPU, run an aiter op_test or a FlyDSL pytest target, and write a correctness-and-perf JSON artifact into ~/<KEY>/. Use for /verify-gpu-kernel, whenever a playbook says to verify, reproduce, or benchmark on the real surface for aiter, FlyDSL, or Triton kernels on MI300X or MI355X."
---

# Verify GPU kernel

The control skill for kernel work. The surface is a GPU in a container on a shared host. Kernels run in a container. The host has no torch.

Every `TODO` below marks a fact not verified on this machine. Resolve it with the user or the host before you rely on it.

## Resolve the host

The host, container, repo path, and arch map is in [`env.md`](../ateam-mode/references/env.md).

Observed on the machine this skill was written on, by read-only commands:

| Fact | Value |
|---|---|
| Hostname | `smci355-ccs-aus-m01-21` |
| GPUs | 8 × AMD Instinct MI355X, arch `gfx950`, HIP index 0 to 7 |
| Host ROCm | 7.1.1 (`/opt/rocm` → `/opt/rocm-7.1.1`) |
| Host python | no `torch`. Use a container for anything that imports torch |
| Host tools | `docker`, `flock`, `rocm-smi`, `rocminfo`, `rocprofv3` (`~/.local/bin/rocprofv3`) |
| Repos | `~/aiter` (branch `main`), `~/FlyDSL` (branch `main`, remote `origin` is `ROCm/FlyDSL`) |
| Ticket folders | `~/<KEY>/`, with an optional `.devcontainer/devcontainer.json` |

- `TODO`: the SSH name for the MI355X host is `mi355x-tritoners`. No `~/.ssh/config` alias exists here, and `hostname` prints the name above. Confirm that `mi355x-tritoners` and this machine are the same host. If you reach the host by SSH, run `ssh mi355x-tritoners hostname` first.
- `TODO`: no MI300X (`gfx942`) host was observed. Name the host, its SSH alias, and its container before any `gfx942` run.
- `TODO`: `~/aiter` has remotes `origin` (`ROCm/aiter`, public) and `fhuizing` (`fhuizing/aiter`). Confirm which fork the owner pushes branches to, per **opening-a-pr**.

Check the arch every time, because a number from the wrong arch is not a number:

```bash
rocminfo 2>/dev/null | grep -m1 gfx
docker exec <container> bash -c 'rocminfo 2>/dev/null | grep -m1 gfx'
```

## Resolve the container

Prefer the container the ticket already names. Look in this order:

1. `~/<KEY>/.devcontainer/devcontainer.json`. The `--name=` entry in `runArgs` is the container name, and `workspaceMount` is the bind mount. `~/SILOTIGER-1164` and `~/ROCM-31582` each carry one.
2. `docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'` for a running container. Match by ticket key or image tag.
3. If none exists, ask the user which image to use. Do not pick an unrelated container.

Containers seen running here:

| Container | Image | Use |
|---|---|---|
| `silotiger-1164-mhc` | `silotiger-1164-mhc:rocm7.2.4` (torch 2.10.0+rocm7.2.4, HIP 7.2) | SILOTIGER-1164. Mounts `~/SILOTIGER-1164` at `/workspaces/SILOTIGER-1164` and `~/aiter` at `/workspaces/aiter`. Env: `PYTHONPATH=/workspaces/aiter`, `AITER_JIT_DIR=/tmp/silotiger-1164-aiter-jit`, `HIP_VISIBLE_DEVICES=0` |

Every other running container belongs to another user or another task. Never `docker exec` into it, stop it, or remove it.

- `TODO`: the container for FlyDSL work. `flydsl-dev` exists but is stopped. The container names `jdbba-flydsl` and `anguyenh-mla-reduce`, which `jdbba-autoresearch` and `optimize-mla-reduce-flydsl` use, do not exist here. Name the FlyDSL container and its repo mount path before a FlyDSL run, or build one with `build-flydsl` or `build-rocm-image`.
- `TODO`: the container path for `~/FlyDSL`. Only `~/aiter` is bind-mounted in the observed container.

Record the container's `torch.__version__`, `torch.version.hip`, and image tag in the artifact:

```bash
docker exec <container> python3 -c "import torch;print(torch.__version__, torch.version.hip)"
```

## Doctor

Run this first, and again whenever a result looks odd. It is read-only.

```bash
hostname
rocm-smi --showuse --showmemuse
rocm-smi --showpids
docker exec <container> bash -c 'rocminfo | grep -m1 gfx; echo $HIP_VISIBLE_DEVICES $AITER_JIT_DIR'
git -C ~/aiter log -1 --format='%h %s'; git -C ~/aiter status --short | head
git -C ~/FlyDSL log -1 --format='%h %s'; git -C ~/FlyDSL status --short | head
```

A GPU is usable when `rocm-smi` shows near-zero use and VRAM, and `--showpids` lists no KFD process on it. The `low-power state` warning on an idle GPU is normal. Stop and report when the doctor shows the wrong arch, a dirty repo you did not expect, or a missing container.

## Lock one idle GPU

Pick over a sampling window, not one reading, then hold a lock for the whole run. The picker and the lock convention come from **validate-kernel-pr**:

```bash
PICK=$(python3 ~/.claude/skills/validate-kernel-pr/pick-idle-gpu.py --samples 10 --interval 1 --quiet)
flock /tmp/gpu-$PICK.lock docker exec -e HIP_VISIBLE_DEVICES=$PICK <container> <command>
```

- Use one GPU id for both sides of a comparison.
- Run one benchmark per GPU at a time. Parallel worktrees may build and check ISA together. They queue for the GPU.
- Use a distinct `AITER_JIT_DIR` per side or per worktree. Never share one between a baseline and a candidate.
- `TODO`: the host is shared. The `flock` file coordinates only runs that use the same convention. Ask the team whether another convention applies, and treat a busy GPU as taken.
- If no GPU stays idle, stop and report `NO_GPU`. Do not benchmark on a busy GPU. A compile-only check (**isa-resource-diff**) still works.

## Run

Run the repo's own test target. Do not rewrite it.

| Repo | Command (inside the container, in the repo root) |
|---|---|
| aiter | `python3 op_tests/test_<op>.py` with the test's own `-d`, `-b`, `-s` flags. It prints a correctness-and-perf markdown table per the **aiter-op-test** skill |
| FlyDSL | `python3 -m pytest tests/kernels/<test>.py -q` |
| Triton kernel in aiter | The same `op_tests` script. Set `AITER_USE_SYSTEM_TRITON` as the container env sets it |
| One-off bench script | `python3 <script>`, with the interleaved-median pattern of `~/SILOTIGER-1164/bench_hip_triton_flydsl_graph.py` |

Set `GPU_ARCHS` (for example `gfx950`) when `aiter` import would otherwise call `rocminfo`. Clear JIT caches for a cold-compile comparison, per **benchmark-checklist**. For a tuned-config shape, follow **aiter-config-shape**.

Read the tables the test prints. Copy numbers from the output, not from memory.

## Write the artifact

Write `~/<KEY>/bench_<topic>.json` for ticket work, and `./bench_<topic>.json` otherwise. The file lives on the host path, so it survives the container. Use this shape and add fields only when needed:

```json
{
  "key": "<KEY>",
  "ts": "<ISO8601 UTC>",
  "host": "<hostname>",
  "container": "<name>",
  "image": "<image:tag>",
  "gpu": {"hip_index": 0, "arch": "gfx950", "name": "AMD Instinct MI355X"},
  "versions": {"rocm": "", "torch": "", "hip": "", "triton": ""},
  "repos": [{"path": "~/aiter", "sha": "", "dirty": false}],
  "command": "<exact command>",
  "correctness": {"passed": true, "rtol": 0, "atol": 0, "nan_count": 0, "shapes_checked": 0},
  "perf": [{"shape": "", "us_median": 0, "runs": 0, "min_us": 0, "max_us": 0, "regime": "cold-L2 | warm | hipGraph"}],
  "raw_output": "<path to the saved stdout>"
}
```

Save the full stdout beside it. The JSON must come from the run, never typed by hand.

## Proof standards

- Run the real kernel path on a GPU. A CPU fallback, an import check, or a compile does not prove it.
- Correctness comes before perf. A perf row next to a failed or unchecked correctness row is not a result.
- Confirm the arch, the GPU id, and the repo SHAs in the artifact match what you ran.
- A run with no idle GPU, a missing container, or an unreadable test output is `INCONCLUSIVE`, never a pass.

## Cleanup

- Release the `flock` by letting the command exit. Do not delete another user's lock file.
- Remove only what this run created: scratch files, its own `AITER_JIT_DIR`, its own worktrees.
- Keep `~/<KEY>/` artifacts. Cleanup never removes evidence.
- Never `docker rm`, `docker stop`, `pkill`, or `rocm-smi --reset*` on anything this run did not start.
