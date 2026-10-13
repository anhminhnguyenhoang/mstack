---
name: create-verification-skill
description: "Generate a repo-local verification skill for a GPU kernel library such as an aiter or FlyDSL checkout: one feature file per op family for the correctness gate, the frozen perf harness, and the ISA resource check, all driven on one locked GPU. Use for /create-verification-skill, 'make a verify skill for aiter or FlyDSL', 'map the op tests of this repo', or when a kernel library has no scripted way to prove correctness, perf, and resources."
disable-model-invocation: true
---

# Create a verification skill

A kernel library needs a scripted way to prove its ops: a correctness gate, a perf number, and a resource check. This skill generates that as a repo-local skill, `.cursor/skills/verify-<lib>/`. The next agent reads the output cold, mid-task, and has never seen the repo.

Non-kernel surfaces, such as a CLI, a service, or a browser app, are out of scope.

```
repos resource ──► inventory op families ──► feature map ──► verify-<lib> skill
                       │                          │                │
                  op tests, pytest         correctness / perf / ISA │
                                                                    ▼
                                              prove once on one locked GPU (bench.run)
```

## 1. Interview the repo

Answer from the checkout. Ask the user only for what you cannot observe.

- **Library.** Read the path, the container, and the path in the container from the `repos` resource. Never write them into the generated skill. When `repos` is not set, stop and ask for `/setup-mstack env`.
- **Arch.** Read the target arch (`gfx942` or `gfx950`) from inside the container. Note each op that has an arch gate.
- **Op families.** List the families, such as GEMM, attention, MoE, norm, and quant. For each, find the entry points:
  - aiter: `op_tests/test_*.py` and its flags (`-d`, `-b`, `-s`, shapes).
  - FlyDSL: the pytest targets under `tests/kernels/`.
  - Triton kernels in aiter: the same `op_tests` scripts.
- **Correctness gate.** Per family: the torch reference and its dtype, the `rtol` and `atol`, the shapes, the edge cases (small M, partial tiles, dtypes), and how the test counts NaN.
- **Perf.** Per family: the frozen harness or the perf table of the op test, the reference side (torch, Triton, or a vendor library), the regime (cold-L2, warm, `hipGraph`), and the run count.
- **Resources.** Per family: the test command that dumps ISA, for the `isa.diff` port.
- **Gaps.** An op with no test is a gap. Write the test through the `test.author` port, or list the gap in the map.

If the checkout does not build or import as it is, fix that first or report it exactly. A skill written against a broken base teaches wrong steps.

## 2. Generate the skill

Write `.cursor/skills/verify-<lib>/SKILL.md`. The frontmatter has `name: verify-<lib>` and a `description` that names the library, the op families, and when to use it. Without frontmatter the skill never registers. Each section below comes from what the interview found. Leave no placeholder.

- **Launch.** There is no server. Launch means take one GPU lock and build the kernel once inside its container, through the `bench.run` port. Cite the port. Do not restate its lock rule.
- **Doctor.** Cite the `bench.run` doctor. Add the checks that belong to the library: the repo SHA, the build is present, and the arch matches the gate of each op.
- **Drive.** Real commands from this repo for each family: test paths, flags, shapes. Prefer stable handles (flags, test IDs, shape lists) over positions.
- **Evidence.** Each run writes its artifact through `bench.run`. Write it to the ticket folder when the `tickets` resource is set and the work has a ticket. Write it to the work dir otherwise. State the proof standards:
  - Correctness comes before perf. A perf row without a passing correctness row on the same run is not a result.
  - Copy every number from the saved stdout.
  - State the perf regime on every row.
  - State a speedup or a percent of peak with its source (**principle-respect-the-roofline**, **principle-explain-the-number**).
- **Cleanup.** Remove only what the run created: scratch files, its own JIT directory, its own worktrees. Never remove the artifacts. Never kill by process name.
- **Helpers.** Any script that the skill ships is executable. Its invocation is shown in the skill body.

## 3. Seed the feature map

Create `.cursor/skills/verify-<lib>/features/README.md` and one file per feature. Follow [`references/feature-map-example/`](references/feature-map-example/).

```
op family ──┬─► <family>-correctness.md   allclose gate, edge cases, NaN, negative control
            ├─► <family>-perf.md          frozen harness, reference side, percent of peak, artifact
            └─► <family>-isa.md           VGPR, SGPR, spills, scratch, LDS, base vs head
```

- Cover the top 3 to 5 op families first. Skip a feature file only when the family has no entry point, and list the gap in the README.
- Each file has the four H2s of the example: `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, and `Gotchas`.
- A correctness file keeps a negative control that must fail. A gate that cannot fail tests nothing.
- A perf file keeps the reference side in the same run, and freezes the harness with its hash.
- An ISA file runs the `isa.diff` port. It compiles only and needs no GPU. A GPU run still goes through `bench.run`.
- If the seed lacks a precondition, the journey reports a failure, and the reason goes in that file's `Gotchas`. Never weaken a journey to make it pass.

The map is the maintained source. A proof that drives one entry point is incomplete when the map lists others.

## 4. Prove the generated skill once

Run its own instructions end to end:

```
bench.run lock ──► doctor ──► drive ONE correctness feature ──► artifact ──► cleanup ──► artifact still there
```

- Drive one mapped feature. One is enough. The map lets later runs cover the rest.
- After cleanup, confirm the artifact exists at its named location. A cleanup that removes the proof fails this step.
- Fix what fails. Run the cleanup after each failed attempt.
- A skill that was never run is a draft, not a deliverable.
- If you proved it on a stand-in, list each setup step the stand-in did that the target will not. Examples: a container for a fresh host, `gfx942` for `gfx950`, a smaller GPU count. Those steps stay unverified.
- A run with no idle GPU, no container, or an unreadable output is `INCONCLUSIVE`. Report it. Do not mark the skill proved.

## 5. Offer the maintenance loop

Point the user at `/maintain-verification-skill`. Suggest a cadence only when they ask.
