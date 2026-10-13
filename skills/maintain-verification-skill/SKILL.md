---
name: maintain-verification-skill
description: "Periodic pass that keeps the verification skill of a kernel library honest: detect new or renamed op tests, removed shapes, changed tolerances, new gfx942 or gfx950 gates, stale reference baselines, and harness drift, then re-prove each feature on one locked GPU and report drift per op family. Use for /maintain-verification-skill, 'audit the verify skill', 'did the op tests change', 'is the aiter or FlyDSL verify map stale'."
disable-model-invocation: true
---

# Maintain a verification skill

A feature map rots when the library changes. This skill is the upkeep loop for a skill that `/create-verification-skill` generated for an aiter or FlyDSL checkout. The unit of rigor is the op family. Cover every family from source, and re-prove every feature on the GPU.

```
locate ──► index ──► source wave ──► reconcile ──► live pass ──► triage ──► ship or stop
                     (1 reader per    (drift          (bench.run,
                      op family)       table)          1 locked GPU)
```

## Outcomes

Pick one, and say which:

- **clean**: every family got source and live coverage, and nothing is worth shipping. No branch, no PR.
- **changed**: one PR ships proven corrections to the map, the harness, or the docs.
- **blocked**: coverage could not finish, or a proven fix could not ship safely. Say what blocked it.

## Edit scope

Edit only the verification skill's own directory: its `SKILL.md`, `features/`, and the harness scripts it owns. Never edit kernel code during a pass. A behavior that the map describes and the library no longer has is one of two things. Doc drift: fix the map. A kernel regression: report it, and do not hide it in the docs.

## Drift kinds

| Drift | Signal | Fix |
|---|---|---|
| New op test | A test file or pytest target that the map does not list | Add the entry point to its family, or a new family |
| Renamed or moved test | A mapped path that no longer exists | Update the path. Check the flags too |
| Removed shape | A mapped shape that the test no longer runs or refuses | Remove it from the map. Say why |
| Changed tolerance | `rtol` or `atol` in the test differs from the map or the artifact | Report it. A looser tolerance is a finding, not a silent update |
| New arch gate | A test or an op that now runs only on `gfx942` or only on `gfx950` | Record the gate in the family file. Mark the feature unreachable on the other arch |
| Stale reference baseline | The reference side or the recorded numbers differ from a fresh run | Re-measure the reference in the same run. Update only from a run |
| Harness drift | The hash of the frozen harness differs from the recorded hash | Report it. A change breaks the comparison with old numbers. Re-baseline both sides |
| Resource baseline | The ISA table of the base differs from the recorded one | Re-capture through the `isa.diff` port |

## Pass

0. **Locate the target.** Find the verification skill, usually `.cursor/skills/verify-*/` in a checkout from the `repos` resource. Several candidates: ask which. None: stop, and point at `/create-verification-skill`.

1. **Index hygiene.** Read the map README. Glob its sibling files. Fix missing, extra, duplicate, or dead entries.

2. **Source wave.** One read-only subagent for each op family, launched together. Each reads the family's op test, the kernel entry, and the git history of both since the last pass. The last pass is the SHA that the map README records. When it records none, use the last commit of the map directory. Each returns:
   - the family summary
   - the entry points
   - drift, by kind from the table, or none, with citations
   - one live recipe

   Children never run a GPU job and never edit files.

3. **Reconcile.** Merge the recipes into as few states as practical. Spot-check each cited drift. Do not re-prove a clean claim. Sweep the churn of the test directories and the config files for an op that has no family. Require a concrete path before you call one missing.

4. **Live pass.** Required even when the source looks clean. Re-prove each feature through the `bench.run` port, on one locked GPU, one command at a time. The ISA features go through the `isa.diff` port. Three rules hold for the whole pass:
   - Run the `bench.run` doctor before the first run and after any failed run. A busy GPU or a wrong arch stops the run.
   - Artifacts survive every cleanup. Check them at their named location.
   - Each run removes its own scratch files and JIT directory. Failed attempts included.

   A doctor failure that comes from skill drift is drift. Fix it under the edit scope, and retry once. A feature is `verified-unreachable` only with the unmet prerequisite and the command tried, for example an arch gate on the wrong host. A missing prerequisite in the map is drift. With no idle GPU, report `NO_GPU`. That is `INCONCLUSIVE`, never a pass. Re-run each harness fix on the GPU before it ships.

5. **Triage.** Apply the Drift kinds table. A test that fails or a number that drops with no drift in the map is a kernel regression. Record it for the user. Keep it out of the PR. For a perf drop, name the limit and rule out a measurement artifact (**principle-explain-the-number**).

6. **Ship or stop.** For changed: one PR of proven corrections. Re-read every changed file first. Prepare it per the Opening a PR playbook. A PR to a public upstream opens as a draft, after the user says yes. For clean or blocked: no PR. Report the outcome and the coverage.

## Report

```
family        drift                      live result            action
GEMM          tolerance 1e-2 -> 5e-2     pass / fail / NO_GPU   map fix / finding
attention     new gfx950 gate            unreachable on gfx942  map fix
...
```

Give one row for each op family. State the outcome, the SHAs, the arch, and the unreachable prerequisites. Keep run notes in a scratch location. Do not commit them.
