# Lever doc

The record of a three-phase lever search (**Kernel hillclimb**, `playbooks/kernel-hillclimb.md`). It lives at `<tickets>/<KEY>/<topic>-opt.md`. Outside a ticket, keep it in the work dir.

Update the doc in place as levers change status. The decision log is the append-only history. The doc is the current state.

## Layout

1. Header. Kernel, arch, GPU, dtypes, shapes with their production mix, metric, target, noise floor, and B (commit SHA and metric). Then `Hard limits`, one line per WaveScope `constraint` note, or `none`.
2. Lever table.
3. Combo table.
4. Ablation table for S*.
5. Retired list.

## Lever table

One row per lever. IDs are `L1`, `L2`, and so on, or the owner's own scheme.

```
| ID | Lever | Screen Δ vs B | Class | In S* | Marginal Δ in S* | Why it failed | Retry if | Evidence |
```

- **ID.** Stable. Never reused.
- **Lever.** The name from the `lever.menu` skill function and the knob or edit, in one line.
- **Screen Δ vs B.** Median change against B with the spread, in the harness metric. For a lever added in Phase 3, the change against the S* of that time, marked `vs S*1`, `vs S*2`.
- **Class.** Empty for a winner. A failure class for a loser.
- **In S\*.** `yes`, `no`, or `-` when not yet decided.
- **Marginal Δ in S\*.** Metric without the lever minus the metric of S*, from the ablation. `-` outside S*.
- **Why it failed.** The root cause in one line. Empty for a winner.
- **Retry if.** The condition that makes a retry worth it, or `no`.
- **Evidence.** A path or SHA to the trace, ISA diff, counter table, or bench log, or a WaveScope note id. Never prose.

Example rows, from a past lever search.

```
| L2 | Direct MFMA-layout loads (`DIRECT_LOADS`) | slower past noise at large T | premise-wrong | no | - | 0 `s_barrier` in the main loop; the lanes of one row touch several cache lines; spills at the largest shape | no | sweep/l2_direct_loads.md |
| L5 | `EARLY_STREAM` (operand stream order, FP8) | slower past noise on FP8 | premise-removed | no | - | L7 removed the FP8 output it tuned | the FP8 output returns | sweep/l5_register_pressure.md, L7 |
| L6 | `NT_STREAMS` below the prefill threshold | 0%, fast/slow pairs | noise | no | - | NT-on reads come in fast/slow pairs; the gain depends on which config runs first | re-measure once with more runs, then reclassify | sweep/l6_nt_streams_decode.md |
```

Several levers can fail for one root cause. Name the cause in each row, so a reader sees the overlap (three load-path levers overlapped in a past search, and their gains did not add).

## Status and class vocabulary

Status, for a lever. Use it in the `result` cell of `decision.tsv`.

- `queued`. Named, with a premise, not yet screened.
- `winner`. Beat B past noise with the gate green. In W.
- `loser`. Did not. It has a class.
- `kept`. In S*.
- `dropped`. Was in S*, and the ablation showed a marginal gain inside noise.
- `retired`. A loser with a root cause, evidence, and a `Retry if` condition that does not hold now. A lever that the `failure-modes` role of the `kb` resource records as a dead end for the same mechanism starts here, before any screen. Its root cause is the one the note states, its Evidence is the note (cite the note file), and its `Retry if` is the note's stated condition, or "new evidence that the premise holds here". Screen it only when that condition holds now.

Class, for a loser. Each class has a retry rule.

| Class | Meaning | Retry |
| --- | --- | --- |
| `premise-wrong` | The thing it targets is not there. A barrier lever on a main loop with 0 `s_barrier`. | No. |
| `premise-removed` | It depends on something that was removed. A lever that tunes an output a later change dropped. | Only if the premise returns. |
| `masked` | Real mechanism, but another bottleneck dominates (VMEM-issue-bound). | Yes, on S*. Or when a trace shows the bottleneck moved. |
| `cost-exceeds` | Real gain, and a side cost wins. A gain that comes with new spills. | If S* frees registers, LDS, or the other resource. |
| `broken` | The implementation or correctness failed. | After the fix. |
| `noise` | Inside run-to-run noise. NT on and off. | Re-measure once with more runs, then reclassify by root cause. |

A lever retires only with a root cause, its evidence, and a `Retry if`. A `noise` row has no root cause yet, so it cannot retire.

## Combo notation

- **B.** The frozen baseline. One commit SHA and its metric.
- **L<n>.** A lever. One branch `<topic>/L<n>` from B (or from S* in Phase 3), in its own worktree.
- **W.** The winners of Phase 1.
- **ALL.** B plus every lever of W.
- **C<n>.** Any combo built and measured in Phase 2 or 3. Give it an ID, its levers, and its SHA.
- **S\*.** The best subset. Version it `S*1`, `S*2` each time a Phase 3 win joins.

```
| Combo | Levers | SHA | Metric (median of N, spread) | vs B | vs S* | Note |
```

Rules.

- One combo branch, `<topic>/combo`. One kept lever is one commit, `perf(<kernel>): <ID> <lever>`. Stage files by name.
- Ablation is a revert. Branch `<topic>/ablate-<ID>` from the head of S*, then `git revert` the lever's commit. A conflicting revert means the levers edit the same lines. Record it.
- Subsets matter, not order. Build both orders only when two levers edit the same lines.
- Each combo branch gets its own JIT cache, per the `bench.run` skill function.

## Ablation table

One row per lever in S*.

```
| ID | Metric without it | Marginal Δ | Verdict |
```

Verdict is `keep` when the marginal gain is past noise, and `drop` when it is inside noise or negative. A dropped lever goes back to the lever table as `masked`, with `Retry if: S* changes`.

## Retired list

One line per retired lever: `<ID>: <class>. <root cause>. Evidence: <path>. Retry if: <condition>.` It goes into the Deliver finding unchanged.

A retired lever whose root cause is general is a candidate for the `kb.capture` skill function. General means true for any kernel with that mechanism, not tied to this ticket's shapes or machine. Mark those lines `KB candidate`, and offer them in Deliver. Run the skill function only after the user says yes. When `kb` is not set, skip the offer and write `skipped kb: not set`. The numbers, shapes, and SHAs stay in this doc.

## WaveScope notes

This section applies only when the `wavescope` resource is set. When `wavescope` is not set, or the `trace.annotate` skill is missing, deliver the trace findings in the reply or the ticket folder instead, skip the `notes.json` loop, write `skipped wavescope: not set`, and ask once per session whether the user uses WaveScope.

The `trace.annotate` skill function publishes trace findings as `annotations.json`, and the human verifies them in WaveScope. The human replies in `notes.json` beside the trace. When a `notes.json` exists for a trace of B or S*, read it before the next phase, as the skill function's skill says.

```
annotations.json ──► human reads in WaveScope ──► notes.json ──► lever doc ──► next phase
     (ours)                                         (theirs)
```

Each open note maps to one change in this doc.

| Note kind | Lever doc change |
| --- | --- |
| `rejected` | Retire the lever it names, and add its row if none exists. Choose the class and the root cause from the note's evidence. The Evidence cell is the note id. `Retry if` is new evidence that answers the note. Never re-propose the lever without that evidence. |
| `constraint` | Add a line to `Hard limits` in the header. Every lever respects it, in every phase. A lever that would break it is not built. |
| `question` | Add it to "For the human" in `<tickets>/<KEY>/STATUS.md`. Answer it with an annotation through the `trace.annotate` skill function. |
| `problem`, `hypothesis` | Queue a lever or open an investigation. Verify it against the trace before you write its premise. |

Other kinds, and notes that are not open, follow the `trace.annotate` skill.

- An existing `annotations.json` is a prior round. Read it. Do not restate it.
- Never write `notes.json`. It is the human's file.

## decision.tsv columns

Start from the six columns of **show-me-your-work**: `ts`, `phase`, `decision`, `why`, `evidence`, `result`. Kernel work adds three at the end.

```
ts	phase	decision	why	evidence	result	combo	lever	class
```

- **phase.** `setup`, `screen`, `combine`, `revisit`, or `ablate`.
- **combo.** The combo ID the row measured (`B`, `ALL`, `C3`, `S*1`). Empty for a row with no measurement.
- **lever.** The lever ID. Empty for a combo row of several levers, which lists them in `decision`.
- **class.** The failure class of a loser. Empty otherwise.

`scripts/log.sh` writes six columns. Append the nine with `printf`, and apply its cleaning: no tabs or newlines, and a leading quote on a cell that starts with `=`, `+`, `-`, or `@`. One row per measurement and one per status change. A superseded row gets a new row, never an edit.
