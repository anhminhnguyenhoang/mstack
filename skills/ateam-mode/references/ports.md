# Ports

A port is a capability that a playbook needs, named `area.capability`, such as `trace.analyze`. Playbooks, mstack skills, and docs name ports. This file alone binds each port to the skills that serve it. A skill rename, merge, or removal edits only this file.

The bound skills live outside the plugin, in `<name>/SKILL.md` under the directory of the `skills` resource (`resources.md`). `$MSTACK_SKILLS_DIR` overrides that directory. Read the bound skill before you apply it. mstack cites a skill and never restates its facts. When this file and a skill disagree, the skill wins, and this file gets the fix in its own PR.

`python3 scripts/check.py` enforces the rule:

- Every bound skill resolves to a `SKILL.md` with a `name` and a `description`.
- Every installed skill is bound below or listed under Ignored.
- No other mstack file names a bound skill. The exceptions are `skills/setup-mstack/SKILL.md`, `scripts/check.py`, and `archive/`. mstack's own skills may be named anywhere.

`/setup-mstack env` runs the same check and records the result in the Skills table of `~/.cursor/mstack/env.md`. With no `skills` resource, the check skips with a note and does not fail.

## Bindings

A playbook step names the port, as in "the `isa.diff` port". Resolve it here when the step runs.

| Port | When | Skill | Selection rule |
|---|---|---|---|
| `kernel.write` | A new kernel from a requirement, a Triton port to FlyDSL, a new MFMA or copy atom, or an opus HIP kernel | `flydsl-tile-programming`, `flydsl-kernel-authoring`, `opus-kernel-best-practice`, `add-target-atom-op` | A FlyDSL kernel: `flydsl-tile-programming` is the procedure, and `flydsl-kernel-authoring` is the reference it leans on. An opus HIP kernel: `opus-kernel-best-practice`. A new atom in a backend dialect: `add-target-atom-op`. |
| `kernel.cleanup` | A behavior-preserving cleanup of a kernel or its shared helpers | `flydsl-kernel-code-cleanup`, `kernel-code-cleanup` | By repo. aiter, a kernel under `aiter/ops/flydsl/`: `flydsl-kernel-code-cleanup`. FlyDSL: `kernel-code-cleanup`. The skill's verification loop is the proof step of Refactoring. |
| `kernel.debug` | A kernel gives wrong numbers, NaN, or inf, crashes, hits an illegal address, or corrupts memory | `debug-flydsl-kernel`, `oob-detection` | Wrong numbers, NaN, inf, a crash, or a compile error in a FlyDSL kernel: `debug-flydsl-kernel`. An illegal address, silent corruption, or suspect address math in any kernel: `oob-detection`. |
| `perf.bisect` | A kernel got slower, and the commit that did it is unknown | `bisect-perf-regression` | Only binding. |
| `isa.diff` | A change may have moved VGPR, SGPR, spills, scratch, or LDS. Compile-only, no GPU | `isa-resource-diff` | Only binding. Run it before any benchmark. |
| `compiler.knob` | A compile hint, a function attribute, or an `-mllvm` flag, and the proof that it reached codegen. Reading the IR or ISA the compiler produced | `llvm` | Only binding. Resource deltas are `isa.diff`. |
| `lever.menu` | Pick the next lever for a kernel, or close a gap to a reference | `cdna-kernel-opt`, `gemm-optimization`, `lds-optimization`, `prefetch-data-load`, `chiplet-xcd-remap`, `optimize-mla-reduce-flydsl`, `optimize-mla-reduce-traversal-flydsl` | `cdna-kernel-opt` first. Its diagnosis names the bottleneck class. Then the specialised menu for that class: GEMM structure `gemm-optimization`, LDS conflicts `lds-optimization`, exposed load latency in a loop `prefetch-data-load`, low cross-block L2 reuse `chiplet-xcd-remap`. `mla_reduce` on `gfx942` only: `optimize-mla-reduce-flydsl` for the accumulate loop, then `optimize-mla-reduce-traversal-flydsl` after those levers converge. Each of the two runs its own loop for that kernel. |
| `trace.capture` | Capture an ATT trace, a `rocprofv3` kernel trace, or PMC counters | `capture-kernel-trace`, `analyze-att-trace` | Default: `capture-kernel-trace`. In the WaveScope loop, capture through a `.wavescope/profiles.json` profile, per `capture-profile.md` in `analyze-att-trace`. |
| `trace.analyze` | Why a kernel is slow: stall hotspots, occupancy, L2 and HBM efficiency | `kernel-trace-analysis` | Only binding. It gives the hotspot plan, occupancy, and the PMC L2 analysis. Stall type to fix: its step 6. |
| `trace.annotate` | Publish trace findings for the human to verify in WaveScope, or read the human's `notes.json` reply | `analyze-att-trace` | Only binding. The WaveScope CLI, `att annotations write`, and the `notes.json` contract are in it. |
| `bench.run` | Run one command on one locked GPU in the right container, and write the artifact | `verify-gpu-kernel` | mstack's own skill. Two git revisions are `pr.validate`. |
| `pr.validate` | Compare the base and the head of a kernel PR on a locked GPU, with a report | `validate-kernel-pr` | Only binding. |
| `pr.review` | An advisory review of an aiter or FlyDSL PR | `review-pr` | Only binding. Hand it the `pr.validate` report when one exists. |
| `api.check` | A FlyDSL public API change, or a release candidate | `api-stability`, `release-api-check` | A PR, a branch, a kernel, or a consuming module: `api-stability`. A release candidate against published releases: `release-api-check`. |
| `test.author` | Write or extend an aiter `op_tests/test_*.py` | `aiter-op-test` | Only binding. |
| `config.tune` | Add or merge tuned config CSVs under `aiter/configs`, or fix a duplicate-shape collision | `aiter-config-shape` | Only binding. |
| `style.gate` | Before a commit or a push: the repo's CI style gate | `format-code` | Only binding. Each repo's own gate commands are in its row of the Opening a PR table (`../playbooks/opening-a-pr.md`). |
| `env.build` | Build FlyDSL, or a ROCm image with aiter and FlyDSL | `build-flydsl`, `build-rocm-image` | FlyDSL into an existing container or host: `build-flydsl`. A new image on a remote host: `build-rocm-image`. Pushing a shared image pauses for the human, per Autonomy. |
| `opus.build` | The first-call JIT build wall of an aiter opus module, or a new opus module | `opus-module-build-optimization` | Only binding. Template compile time inside one kernel is `kernel.write`. |
| `kb.capture` | Save a durable lesson to the `kb` resource: a lever with its root cause, a hardware fact, or a method | `kb-add-topic` | Only binding. Needs the `kb` resource. Offer it, and run it only after the user says yes. |

## Order of checks for a perf change

```
isa.diff        seconds, no GPU      regress? ──► reject, no benchmark
    │ clean
    ▼
bench.run       one locked GPU, vetted by benchmark-checklist
    │ plateau
    ▼
trace.capture ──► trace.analyze ──► lever.menu ──► next lever
                       │
                       └──► trace.annotate   findings the human verifies in WaveScope
```

## Rules

- Run the cheapest port that can settle the question first.
- A skill bound to one kernel and one arch applies only there. For any other kernel, run Kernel hillclimb (`../playbooks/kernel-hillclimb.md`) and borrow its levers. Confirm the arch before you trust a number from it.
- Correctness gates every perf number (**principle-correctness-before-speed**).
- A port whose skill is missing or malformed, or a `skills` resource that is `not set`, stops the step. Tell the user and point them at `/setup-mstack env`. Do not work around it.

## Ignored

Installed skills that no port binds. One line each, as ``- `<name>`: <reason>.`` The check reads this list.

None.
