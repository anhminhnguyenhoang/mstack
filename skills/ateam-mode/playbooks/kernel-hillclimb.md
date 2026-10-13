### Kernel hillclimb

**You own the metric and the experiment's integrity. Supervise and review. Delegate the edits.** Hillclimb for a GPU kernel on AMD Instinct. It adds the GPU harness, a no-GPU ISA pre-check, one-GPU serialization, and a three-phase lever search to **Hillclimb** (`playbooks/hillclimb.md`). Read that playbook for the loop discipline. This one replaces its step 5 loop.

Some kernels have their own loop skill, named in the selection rule of the `lever.menu` port (`references/ports.md`). Check it first. This playbook is the same loop for any other kernel.

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

The record is `<tickets>/<KEY>/<topic>-opt.md`, from `references/lever-doc.md`. It holds the lever table, the combo notation, the log columns, and the WaveScope notes map. Read it before you start.

1. Ground the target. Run the **how** skill over the kernel and its reference (the Triton or HIP kernel it must match or beat). Fix the arch (`gfx942` or `gfx950`), the GPU, the dtypes, and the shapes that matter in production, with their mix. Fix one metric (kernel time in µs, or the ratio to the reference), the direction, and a checkable stop predicate with a floor on attempts. Read the reference's source before you sweep anything (the `lever.menu` port, step 4 of its loop). Compute the byte and FLOP floor once and state the percent of peak you start at (**principle-explain-the-number**).
2. Build the harness, then freeze it.
   - Time with `run_perftest` (aiter) or `triton.testing.do_bench`. Report the median of N, not one run.
   - Gate correctness first: `allclose` against the torch reference with stated `rtol` and `atol`, plus the NaN count, on every shape and the edge cases (empty group, partial tail tile). A speed number that skips the gate does not count (**principle-correctness-before-speed**).
   - Run the reference on the same shapes, the same GPU, and the same session. Print the ratio.
   - Report the regime production uses: hipGraph replay or eager, cold L2 or warm. Measure both regimes when the change touches L2 reuse.
   - Print the error count and the kernel name from a `rocprofv3` kernel trace, so a fallback path cannot pass for the kernel.
   - Vet the harness with the **GPU kernels** section of **benchmark-checklist** before the freeze.
   - Measure the noise floor: run B against B, interleaved, and record the spread. Every "past noise" below means past this spread. Paired, interleaved runs on one GPU decide any close call. Separate runs in separate processes do not.
3. Open the decision log via the **show-me-your-work** skill, with the kernel columns from `references/lever-doc.md`. In ticket work it is `<tickets>/<KEY>/decision.tsv`. Open the lever doc next to it. Record B as the frozen baseline commit with its metric. Before each phase, check for a `notes.json` from the `trace.annotate` port beside the latest trace of B or S*. When one exists, read it and apply its open notes to the lever doc, per its WaveScope notes section. Never write `notes.json`.
4. Read the `kernel-optimization/` area of the `kb` resource before Phase 1, when that resource is configured. Read its lever notes, to name and premise levers alongside the `lever.menu` port. Read its failure-modes notes for known dead ends and decision heuristics. A lever that the `kb` resource records as a dead end for the same mechanism starts as `retired`. Its root cause is the one the KB note states, its Evidence is the note, and its `Retry if` is the note's stated condition, or "new evidence that the premise holds here". Screen it only when that `Retry if` holds now. When the `kb` resource is missing or `not set`, write one line in the decision log that it was skipped, ask once per session whether the user has one (`references/resources.md`), and continue.
5. Name a lever for every hypothesis. Take it from the `lever.menu` port, or from the `compiler.knob` port for a compiler flag. Classify the bottleneck before you pick, with the counter pass that the `lever.menu` diagnosis names. State the premise of each lever as a checkable fact about the ISA or a counter. "Try a different tile size" is not a hypothesis. Give each lever an ID and a row in the lever table. Every lever respects the `Hard limits` in the lever doc header. A lever that a `rejected` note retired comes back only with new evidence.
6. PHASE 1, SCREEN. Measure every lever against B.
   - Hand each edit to a subagent in its own worktree of the target repo, branched from B. One lever per worktree. Give it the lever, the files, and the gate.
   - Run the correctness gate. A failure is class `broken`. Do not time it.
   - Run the `isa.diff` port against B. It needs no GPU and takes seconds. New spills or scratch, or a VGPR or LDS rise that crosses an occupancy step (fewer waves per SIMD), skips the benchmark and the lever is class `cost-exceeds`, unless the lever's point is to trade occupancy for speed and the hypothesis said so. A rise inside the same occupancy step is benchmarked, so a possible uplift is not skipped. Record the diff as evidence.
   - Check the change reached codegen (**principle-prove-it-reached-codegen**). An unchanged ISA or IR is class `broken` when the edit should have moved it, and class `premise-wrong` when the knob is inert.
   - Fan out edits, builds, and ISA checks. Benchmarks queue on the lock of the `bench.run` port, one per GPU.
   - A lever that beats B past noise with the gate green and no tracked shape regressing past noise is a winner. A lever that wins on one shape and loses on another is a winner for that shape. Note the shape.
   - Every other lever is a loser. Classify it at once, with evidence (trace, ISA diff, or counter). The classes and their retry rules are in `references/lever-doc.md`.
   - Update `<tickets>/<KEY>/STATUS.md` with one line: W, L, and the best single lever.
7. PHASE 2, COMBINE. Having all the winners can be worse than a subset. One winning lever can kill another's gain.
   - ALL is B plus every lever of W. Build it and measure it.
   - Search the subsets of W for the best subset S*.
     - Four winners or fewer: build and measure every subset. That is at most 11 builds and benches, the singletons already being measured in Phase 1.
     - More than four: backward elimination from ALL. Drop the lever whose removal helps most. Repeat until no removal helps. That is about n to n² benches.
   - A subset beats another only past noise. Use the median of N, interleaved A/B on one GPU.
   - Subsets matter, not order. Build both orders only when two levers edit the same lines.
   - S* lives on one combo branch. One kept lever is one commit, staged by file, never `git add -A`.
   - Ablate S*. For each lever in S*, revert its commit on a scratch branch, build, and measure. The marginal gain is the metric without it minus the metric of S*. Drop a lever whose marginal gain is inside noise or negative. Reclassify it `masked` with `Retry if: S* changes`, so it is not retried against the S* that just dropped it.
   - If prefill and decode, or any two shapes, prefer different subsets, make the lever a knob or a shape dispatch. A load-layout lever that helps prefill and hurts decode is the pattern. If one subset must serve all shapes, pick by the production mix from step 1.
   - Update `<tickets>/<KEY>/STATUS.md` with one line: S*, its metric, and the gain over B.
8. PHASE 3, REVISIT. A loser is not dead until its cause says so. Do not skip any uplift from an idea that still has potential.
   - Take each retry-eligible loser. A loser is eligible when its `Retry if` condition holds now.
   - Build it on top of S*, gate it, run the `isa.diff` port against S*, and measure it against S*.
   - A win joins S* as one commit. Return to Phase 2 for ablation only, because a new lever can change the marginal gain of the old ones. Then run the eligible losers again against the new S*. Repeat until a full pass adds nothing.
   - A loser that fails on the current S* waits with its condition. It becomes eligible again only when S* changes or the condition is met.
   - A `noise` loser is re-measured once with more runs, then reclassified by its root cause.
   - A loser whose premise is dead is retired. A retirement needs a root cause, its evidence (trace, ISA diff, or counter), and a `Retry if` condition. Without all three, the lever is not retired. It stays a loser.
   - A new lever from the plateau trace or a probe (such as a layout lever that a copy probe and a remove-one-piece probe pointed at) is screened against the current S*, not the stale B.
   - A premise change (such as a change that removes an output three levers tuned) re-screens the affected levers against the new baseline, then reruns Phase 2. Supersede the old rows in `decision.tsv`. Do not edit them.
   - At a plateau, stop guessing. Capture an ATT trace of S* (the `trace.capture` port) and read it with the `trace.analyze` port, or the `trace.annotate` port in the WaveScope loop. In ticket work, publish the findings through the `trace.annotate` port, so the human can verify them in WaveScope. An `annotations.json` already on the trace is a prior round: read it, do not restate it. The human's `notes.json` reply feeds the next phase, per step 3. Pick new levers from the stall that dominates, and the trace is also the evidence to reclassify `masked` losers. When the trace points at a redesign rather than a lever, run **Bound probe** (`playbooks/bound-probe.md`) before you build it. If the loop is unattended, borrow only the wake mechanism from the Autonomous run playbook.
   - Update `<tickets>/<KEY>/STATUS.md` with one line: S*, joins this phase, and the retired count.
9. STOP when no retry-eligible loser is left and S* is stable. Do not relax the predicate. If the predicate is met earlier, still finish the Phase 3 pass for eligible losers, and list any untried one as open. Name the structural gap that remains when you stop short.
10. Run **Deliver**. The finding carries S*, the ablation table, and the retired list with reasons. A retired lever whose root cause is general is a candidate for the `kb.capture` port. General means true for any kernel with that mechanism, not tied to this ticket's shapes or machine. Offer those levers in the Deliver reply, and run the port only after the user says yes. The numbers, shapes, and SHAs stay in the lever doc. Code output opens a PR per **Opening a PR**, with the commits of S* in the order they landed. A ticket result becomes a comment draft.

**Reply:** the kernel, arch, and GPU. The metric and target. Baseline to final with the percent delta, and the percent of the HBM or MFMA peak at the end. S* and its ablation table in one line per lever. Levers screened, won, and retired. ISA resource delta, the `decision.tsv` and lever-doc paths, and the one lever you would try next.
