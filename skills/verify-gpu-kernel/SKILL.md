---
name: verify-gpu-kernel
description: "Run one command on one locked AMD GPU in the right container, and write a correctness-and-perf JSON artifact into the ticket folder. The command is an aiter op_test, a FlyDSL pytest target, or a bench harness, which may interleave A and B itself. Use for /verify-gpu-kernel, whenever a playbook says to verify, reproduce, or benchmark on the real surface for aiter, FlyDSL, or Triton kernels on MI300X or MI355X. Comparing two git revisions is the pr.validate port, not this skill."
---

# Verify GPU kernel

The control skill for kernel work, bound to the `bench.run` port. The surface is a GPU in a container on a shared host. Kernels run in a container. The host has no torch.

## Scope

```
host ──► container ──► one locked GPU ──► one command ──► one artifact
```

- One command, on one GPU, under one lock, with one artifact.
- The command may interleave A and B itself, as a frozen hillclimb harness does. This skill runs it once and records what it prints.
- Comparing two git revisions, such as the base and the head of a PR, is the `pr.validate` port. Do not rebuild that comparison here. Ports resolve in [`ports.md`](../ateam-mode/references/ports.md).

## Resolve the host

Read `~/.cursor/mstack/env.md`, the machine-local file that `/setup-mstack env` writes. Its Hosts table gives the host, SSH alias, arch, and GPU count. The rules are in [`env.md`](../ateam-mode/references/env.md). A GPU run needs the `repos` resource, and ticket work needs `tickets` ([`resources.md`](../ateam-mode/references/resources.md)).

- If the file is missing, stop and ask the user to run `/setup-mstack env`.
- If the run needs an arch with no host in the table, or a fact you need is `not set`, stop and ask. Do not pick a host by guess.
- To reach a host by SSH, run `ssh <alias> hostname` first and match the result to the table.

Check the arch every time, because a number from the wrong arch is not a number:

```bash
rocminfo 2>/dev/null | grep -m1 gfx
docker exec <container> bash -c 'rocminfo 2>/dev/null | grep -m1 gfx'
```

## Resolve the container

Prefer the container the ticket already names. Look in this order:

1. `<tickets>/<KEY>/.devcontainer/devcontainer.json`, when the `tickets` resource is set. The `--name=` entry in `runArgs` is the container name, and `workspaceMount` is the bind mount.
2. The repo's default container and mount path in the Repos table of `~/.cursor/mstack/env.md`.
3. `docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'` for a running container in the env file's Containers table. Match by ticket key or image tag.
4. If none exists, or the default is `not set`, ask the user which container or image to use, or build one through the `env.build` port. Do not pick an unrelated container.

Only the containers in the env file's Containers table are the user's. Every other container belongs to another user or another task. Never `docker exec` into it, stop it, or remove it. A stopped container of the user's may be started only with the user's OK.

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
git -C <repo path> log -1 --format='%h %s'; git -C <repo path> status --short | head
```

Run the last line once for each repo row in the Repos table. The `<repo path>` is that row's path.

A GPU is usable when `rocm-smi` shows near-zero use and VRAM, and `--showpids` lists no KFD process on it. The `low-power state` warning on an idle GPU is normal. Stop and report when the doctor shows the wrong arch, a dirty repo you did not expect, or a missing container.

## Lock one idle GPU

Pick over a sampling window, not one reading, then hold a lock for the whole run. Read the picker command and the lock from the GPU lock table of `~/.cursor/mstack/env.md`. The Picker cell prints one HIP index. The Lock cell is the lock prefix, with `<id>` for that index. When either cell is `not set`, stop and ask. Never fall back to a path from memory.

```bash
PICK=$(<Picker cell>)
<Lock cell, with $PICK for <id>> docker exec -w <wt> -e PYTHONPATH=<pythonpath> -e HIP_VISIBLE_DEVICES=$PICK <container> <command>
```

- `<wt>` is the container path of the worktree under test, or of the repo root when there is no worktree, per the Worktree paragraph of [`opening-a-pr.md`](../ateam-mode/playbooks/opening-a-pr.md).
- `<pythonpath>` is `<wt>` for aiter and for a Triton kernel in aiter. For FlyDSL it is `<wt>/python:<wt>/build-fly/python_packages`.

- Run one command per GPU at a time. Parallel worktrees may build and check ISA together. They queue for the GPU.
- Give the run its own `AITER_JIT_DIR`, and each worktree its own. A command that interleaves A and B gives each side its own.
- Run both sides of a comparison on the same GPU id.
- The host is shared. A lock file coordinates only runs that use the same convention. Treat a busy GPU as taken, lock or no lock.
- If no GPU stays idle, stop and report `NO_GPU`. Do not benchmark on a busy GPU. A compile-only check (the `isa.diff` port) still works.

## Check the import

Run this before the first command of a worktree. It prints the package path and does not import the package, so no JIT build runs. Run it from `/`, not from `<wt>`. `python3 -c` puts the cwd on `sys.path`, so a check from `<wt>` passes even when `PYTHONPATH` is missing.

```bash
docker exec -w / -e PYTHONPATH=<pythonpath> <container> python3 -c "import importlib.util as u; print(u.find_spec('aiter').origin)"
```

Use `flydsl` in place of `aiter` for FlyDSL. The path must start with `<wt>/`. If it does not, stop and report it. The run would test another checkout. Python puts the script's directory on `sys.path`, not the cwd, and the JIT builds the sources of the package it imported.

## Run

Run the repo's own test target. Do not rewrite it.

| Repo | Command (inside the container, in `<wt>`, with the `PYTHONPATH` above) |
|---|---|
| aiter | `python3 op_tests/test_<op>.py` with the test's own `-d`, `-b`, `-s` flags. It prints a correctness-and-perf markdown table per the `test.author` port |
| FlyDSL | `python3 -m pytest tests/kernels/<test>.py -q` |
| Triton kernel in aiter | The same `op_tests` script. Set `AITER_USE_SYSTEM_TRITON` as the container env sets it |
| Bench harness or one-off script | `python3 <script>`. It may interleave A and B itself, as a frozen hillclimb harness does |

Set `GPU_ARCHS` (for example `gfx950`) when `aiter` import would otherwise call `rocminfo`. Clear JIT caches for a cold-compile run, per **benchmark-checklist**. For a tuned-config shape, follow the `config.tune` port.

Read the tables the test prints. Copy numbers from the output, not from memory.

## Write the artifact

Write `<tickets>/<KEY>/bench_<topic>.json` for ticket work, and `./bench_<topic>.json` otherwise. The file lives on the host path, so it survives the container. Use this shape and add fields only when needed:

```json
{
  "key": "<KEY>",
  "ts": "<ISO8601 UTC>",
  "host": "<hostname>",
  "container": "<name>",
  "image": "<image:tag>",
  "gpu": {"hip_index": 0, "arch": "gfx950", "name": "AMD Instinct MI355X"},
  "versions": {"rocm": "", "torch": "", "hip": "", "triton": ""},
  "repos": [{"path": "<repo path>", "sha": "", "dirty": false}],
  "command": "<exact command>",
  "imports": {"<aiter or flydsl>": "<find_spec origin>"},
  "correctness": {"passed": true, "rtol": 0, "atol": 0, "nan_count": 0, "snr_db": null, "shapes_checked": 0},
  "perf": [{"shape": "", "us_median": 0, "runs": 0, "min_us": 0, "max_us": 0, "regime": "cold-L2 | warm | hipGraph"}],
  "raw_output": "<path to the saved stdout>"
}
```

`snr_db` is the lowest SNR over the shapes checked. It is required for an fp8, fp4, or mxfp4 output, per **principle-correctness-before-speed**, and `null` otherwise. An A/B command adds a `side` field to each `perf` row. Save the full stdout beside it. The JSON must come from the run, never typed by hand.

## Proof standards

- Run the real kernel path on a GPU. A CPU fallback, an import check, or a compile does not prove it.
- Correctness comes before perf. A perf row next to a failed or unchecked correctness row is not a result.
- Confirm the arch, the GPU id, and the repo SHAs in the artifact match what you ran.
- The `imports` path sits under the worktree you meant to test. A run that imported another checkout is `INCONCLUSIVE`.
- A run with no idle GPU, a missing container, or an unreadable test output is `INCONCLUSIVE`, never a pass.

## Cleanup

- Release the `flock` by letting the command exit. Do not delete another user's lock file.
- Remove only what this run created: scratch files, its own `AITER_JIT_DIR`, its own worktrees.
- Keep the ticket folder's artifacts. Cleanup never removes evidence.
- Never `docker rm`, `docker stop`, `pkill`, or `rocm-smi --reset*` on anything this run did not start.
