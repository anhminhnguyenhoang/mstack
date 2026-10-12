# Lever doc

The record of a three-phase lever search (**Kernel hillclimb**, `playbooks/kernel-hillclimb.md`). It lives at `~/<KEY>/<topic>-opt.md`. Outside a ticket, keep it in the work dir. The worked example is `~/SILOTIGER-1164/mega-mhc-opt.md`.

Update the doc in place as levers change status. The decision log is the append-only history. The doc is the current state.

## Layout

1. Header. Kernel, arch, GPU, dtypes, shapes with their production mix, metric, target, noise floor, and B (commit SHA and metric).
2. Lever table.
3. Combo table.
4. Ablation table for S*.
5. Retired list.

## Lever table

One row per lever. IDs are `L1`, `L2`, and so on, or the owner's own scheme (P1 to P5, D1 to D5, G1).

```
| ID | Lever | Screen Δ vs B | Class | In S* | Marginal Δ in S* | Why it failed | Retry if | Evidence |
```

- **ID.** Stable. Never reused.
- **Lever.** The name from the `lever.menu` port and the knob or edit, in one line.
- **Screen Δ vs B.** Median change against B with the spread, in the harness metric. For a lever added in Phase 3, the change against the S* of that time, marked `vs S*1`, `vs S*2`.
- **Class.** Empty for a winner. A failure class for a loser.
- **In S\*.** `yes`, `no`, or `-` when not yet decided.
- **Marginal Δ in S\*.** Metric without the lever minus the metric of S*, from the ablation. `-` outside S*.
- **Why it failed.** The root cause in one line. Empty for a winner.
- **Retry if.** The condition that makes a retry worth it, or `no`.
- **Evidence.** A path or SHA to the trace, ISA diff, counter table, or bench log. Never prose.

Example rows, from the mega-mHC record.

```
| P2 | MFMA-layout loads (`MFMA_DIRECT_LOADS`) | +9 to +13% slower at T >= 4096 | premise-wrong | no | - | 0 `s_barrier` in the main loop; 4 lanes of a row touch 4 cache lines; 81 spills at T = 16384 | no | sweep/p2_mfma_direct_loads.md |
| P5 | `FN_EARLY` (fn stream order, FP8) | -2 to -5% FP8 | premise-removed | no | - | U1 removed the FP8 amax/448 output it tuned | the FP8 output returns | sweep/p5_register_pressure.md, U1 |
| D1 | `NT_STREAMS` below the prefill threshold | 0%, fast/slow pairs | noise | no | - | NT-on reads come in fast/slow pairs; the gain depends on which config runs first | re-measure once with more runs, then reclassify | sweep/d1_nt_streams_decode.md |
```

Several levers can fail for one root cause. Name the cause in each row, so a reader sees the overlap (P1, P2, and P4 overlapped, and their gains did not add).

## Status and class vocabulary

Status, for a lever. Use it in the `result` cell of `decision.tsv`.

- `queued`. Named, with a premise, not yet screened.
- `winner`. Beat B past noise with the gate green. In W.
- `loser`. Did not. It has a class.
- `kept`. In S*.
- `dropped`. Was in S*, and the ablation showed a marginal gain inside noise.
- `retired`. A loser with a root cause, evidence, and a `Retry if` condition that does not hold now.

Class, for a loser. Each class has a retry rule.

| Class | Meaning | Retry |
| --- | --- | --- |
| `premise-wrong` | The thing it targets is not there. P2: 0 `s_barrier` in the main loop. | No. |
| `premise-removed` | It depends on something that was removed. P5 after U1. | Only if the premise returns. |
| `masked` | Real mechanism, but another bottleneck dominates (VMEM-issue-bound). | Yes, on S*. Or when a trace shows the bottleneck moved. |
| `cost-exceeds` | Real gain, and a side cost wins. P2's 81 spills. | If S* frees registers, LDS, or the other resource. |
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
- Never share a JIT cache directory between combo branches.

## Ablation table

One row per lever in S*.

```
| ID | Metric without it | Marginal Δ | Verdict |
```

Verdict is `keep` when the marginal gain is past noise, and `drop` when it is inside noise or negative. A dropped lever goes back to the lever table as `masked`, with `Retry if: S* changes`.

## Retired list

One line per retired lever: `<ID>: <class>. <root cause>. Evidence: <path>. Retry if: <condition>.` It goes into the Deliver finding unchanged.

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
