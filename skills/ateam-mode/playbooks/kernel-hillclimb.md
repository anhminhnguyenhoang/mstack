### Kernel hillclimb

**You own the metric and the experiment's integrity. Supervise and review. Delegate the edits.** Hillclimb for a GPU kernel on AMD Instinct. It adds the GPU harness, a no-GPU ISA pre-check, one-GPU serialization, and a three-phase lever search to **Hillclimb** (`playbooks/hillclimb.md`). Read that playbook for the loop discipline. This one replaces its step 5 loop.

Named kernels have their own loop skills. Use `jdbba-autoresearch` or `jdbba-frontier-search` for `jagged_dense_bmm_broadcast_add` on `gfx950`, and `optimize-mla-reduce-flydsl` or `optimize-mla-reduce-traversal-flydsl` for `mla_reduce` on `gfx942`. This playbook is the same loop for any other kernel.

Kernel levers interact. They share registers, LDS, and one memory pipe. Gains from separate levers overlap and do not add, and one winner can erase another's gain. So the search runs in three phases. Each lever is measured alone, then in combination, then again on the best combination.

```
PHASE 1 SCREEN    every lever vs baseline B
                  -> winners W; losers L, each with a class + evidence
PHASE 2 COMBINE   ALL = B + W; search subsets of W -> best subset S*
                  ablate S*: marginal gain of each lever inside S*
PHASE 3 REVISIT   retry-eligible losers -> each on top of S*
                  a win joins S* -> back to PHASE 2 (ablation only)
                  dead premise -> retire with the reason
STOP              no retry-eligible loser left, S* stable
                  -> Deliver: S*, ablation table, retired list
```

The record is `~/<KEY>/<topic>-opt.md`, from `references/lever-doc.md`. It holds the lever table, the combo notation, and the log columns. Read it before you start.

1. Ground the target. Run the **how** skill over the kernel and its reference (the Triton or HIP kernel it must match or beat). Fix the arch (`gfx942` or `gfx950`), the GPU, the dtypes, and the shapes that matter in production, with their mix. Fix one metric (kernel time in µs, or the ratio to the reference), the direction, and a checkable stop predicate with a floor on attempts. Read the reference's source before you sweep anything (**cdna-kernel-opt**, step 4). Compute the byte and FLOP floor once and state the percent of peak you start at (**principle-respect-the-roofline**).
2. Build the harness, then freeze it.
   - Time with `run_perftest` (aiter) or `triton.testing.do_bench`. Report the median of N, not one run.
   - Gate correctness first: `allclose` against the torch reference with stated `rtol` and `atol`, plus the NaN count, on every shape and the edge cases (empty group, partial tail tile). A speed number that skips the gate does not count (**principle-correctness-before-speed**).
   - Run the reference on the same shapes, the same GPU, and the same session. Print the ratio.
   - Report the regime production uses: hipGraph replay or eager, cold L2 or warm. Measure both regimes when the change touches L2 reuse.
   - Print the error count and the kernel name from a `rocprofv3` kernel trace, so a fallback path cannot pass for the kernel.
   - Vet the harness with the **GPU kernels** section of **benchmark-checklist** before the freeze.
   - Measure the noise floor: run B against B, interleaved, and record the spread. Every "past noise" below means past this spread. Paired, interleaved runs on one GPU decide any close call. Separate runs in separate processes do not.
3. Open the decision log via the **show-me-your-work** skill, with the kernel columns from `references/lever-doc.md`. In ticket work it is `~/<KEY>/decision.tsv`. Open the lever doc next to it. Record B as the frozen baseline commit with its metric.
4. Name a lever for every hypothesis. Take it from the **cdna-kernel-opt** menu (pipeline overlap, MFMA atom and layout, intermediate residency, LDS swizzle, XCD remap, epilogue store path, compiler flags), or from **gemm-optimization**, **lds-optimization**, **prefetch-data-load**, **chiplet-xcd-remap**, or **llvm**. Classify the bottleneck with one counter pass (`MfmaUtil`, `VALUBusy`, `LDSBankConflict`, `MemUnitStalled`) before you pick. State the premise of each lever as a checkable fact about the ISA or a counter. "Try a different tile size" is not a hypothesis. Give each lever an ID and a row in the lever table.
5. PHASE 1, SCREEN. Measure every lever against B.
   - Hand each edit to a subagent in its own worktree of the target repo, branched from B. One lever per worktree. Give it the lever, the files, and the gate.
   - Run the correctness gate. A failure is class `broken`. Do not time it.
   - Run **isa-resource-diff** against B. It needs no GPU and takes seconds. New spills or scratch, or a VGPR or LDS rise that crosses an occupancy step (fewer waves per SIMD), skips the benchmark and the lever is class `cost-exceeds`, unless the lever's point is to trade occupancy for speed and the hypothesis said so. A rise inside the same occupancy step is benchmarked, so a possible uplift is not skipped. Record the diff as evidence.
   - Check the change reached codegen (**principle-prove-it-reached-codegen**). An unchanged ISA or IR is class `broken` when the edit should have moved it, and class `premise-wrong` when the knob is inert.
   - Fan out edits, builds, and ISA checks. Benchmarks run one at a time on one locked GPU (**verify-gpu-kernel**). Never run two benchmarks on one GPU together, and never share a JIT cache directory between worktrees.
   - A lever that beats B past noise with the gate green and no tracked shape regressing past noise is a winner. A lever that wins on one shape and loses on another is a winner for that shape. Note the shape.
   - Every other lever is a loser. Classify it at once, with evidence (trace, ISA diff, or counter). The classes and their retry rules are in `references/lever-doc.md`.
   - Update `~/<KEY>/STATUS.md` with one line: W, L, and the best single lever.
6. PHASE 2, COMBINE. Having all the winners can be worse than a subset. One winning lever can kill another's gain.
   - ALL is B plus every lever of W. Build it and measure it.
   - Search the subsets of W for the best subset S*.
     - Four winners or fewer: build and measure every subset. That is at most 11 builds and benches, the singletons already being measured in Phase 1.
     - More than four: backward elimination from ALL. Drop the lever whose removal helps most. Repeat until no removal helps. That is about n to n² benches.
   - A subset beats another only past noise. Use the median of N, interleaved A/B on one GPU.
   - Subsets matter, not order. Build both orders only when two levers edit the same lines.
   - S* lives on one combo branch. One kept lever is one commit, staged by file, never `git add -A`.
   - Ablate S*. For each lever in S*, revert its commit on a scratch branch, build, and measure. The marginal gain is the metric without it minus the metric of S*. Drop a lever whose marginal gain is inside noise or negative. Reclassify it `masked` with `Retry if: S* changes`, so it is not retried against the S* that just dropped it.
   - If prefill and decode, or any two shapes, prefer different subsets, make the lever a knob or a shape dispatch. P2's `MFMA_DIRECT_LOADS` is the pattern. If one subset must serve all shapes, pick by the production mix from step 1.
   - Update `~/<KEY>/STATUS.md` with one line: S*, its metric, and the gain over B.
7. PHASE 3, REVISIT. A loser is not dead until its cause says so. Do not skip any uplift from an idea that still has potential.
   - Take each retry-eligible loser. A loser is eligible when its `Retry if` condition holds now.
   - Build it on top of S*, gate it, run **isa-resource-diff** against S*, and measure it against S*.
   - A win joins S* as one commit. Return to Phase 2 for ablation only, because a new lever can change the marginal gain of the old ones. Then run the eligible losers again against the new S*. Repeat until a full pass adds nothing.
   - A loser that fails on the current S* waits with its condition. It becomes eligible again only when S* changes or the condition is met.
   - A `noise` loser is re-measured once with more runs, then reclassified by its root cause.
   - A loser whose premise is dead is retired. A retirement needs a root cause, its evidence (trace, ISA diff, or counter), and a `Retry if` condition. Without all three, the lever is not retired. It stays a loser.
   - A new lever from the plateau trace or a probe (like G1 after B2 and B3) is screened against the current S*, not the stale B.
   - A premise change (like U1 in the mega-mHC record, which removed three levers' ground) re-screens the affected levers against the new baseline, then reruns Phase 2. Supersede the old rows in `decision.tsv`. Do not edit them.
   - At a plateau, stop guessing. Capture an ATT trace of S* (**capture-kernel-trace**) and read it with **analyze-att-trace** or **kernel-trace-analysis**. Pick new levers from the stall that dominates, and the trace is also the evidence to reclassify `masked` losers. When the trace points at a redesign rather than a lever, run **Bound probe** (`playbooks/bound-probe.md`) before you build it. If the loop is unattended, borrow only the wake mechanism from the Autonomous run playbook.
   - Update `~/<KEY>/STATUS.md` with one line: S*, joins this phase, and the retired count.
8. STOP when no retry-eligible loser is left and S* is stable. Do not relax the predicate. If the predicate is met earlier, still finish the Phase 3 pass for eligible losers, and list any untried one as open. Name the structural gap that remains when you stop short.
9. Run **Deliver**. The finding carries S*, the ablation table, and the retired list with reasons. Code output opens a PR per **Opening a PR**, with the commits of S* in the order they landed. A ticket result becomes a comment draft.

**Reply:** the kernel, arch, and GPU. The metric and target. Baseline to final with the percent delta, and the percent of the HBM or MFMA peak at the end. S* and its ablation table in one line per lever. Levers screened, won, and retired. ISA resource delta, the `decision.tsv` and lever-doc paths, and the one lever you would try next.
