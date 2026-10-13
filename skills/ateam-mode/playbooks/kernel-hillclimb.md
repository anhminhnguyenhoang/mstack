### Kernel hillclimb

**You own the metric and the experiment's integrity. Supervise and review. Delegate the edits.** For sustained, iterative improvement of one measurable thing against a target, most often a GPU kernel on AMD Instinct. A one-off fix is Bug fix or Perf issue. This is the loop. It uses a GPU harness, a no-GPU ISA pre-check, one-GPU serialization, and a three-phase lever search.

Core discipline: measure one lever alone, keep or revert. Never stack untested changes, and never claim a win from code inspection (**principle-prove-it-works**). A metric that is not a GPU kernel follows the Non-kernel metrics section at the end.

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

The record is `<tickets>/<KEY>/<topic>-opt.md`, from `references/lever-doc.md`. It holds the lever table, the combo notation, the log columns, and the WaveScope notes map. Read it before you start. The WaveScope notes map applies only when the `wavescope` resource is set.

1. Ground the target. Run the **how** skill over the kernel and its reference (the Triton or HIP kernel it must match or beat). Fix the arch (`gfx942` or `gfx950`), the GPU, the dtypes, and the shapes that matter in production, with their mix. Pick a case that reproduces the user's complaint. If no case reproduces it, fix the repro first and do not climb. Fix one metric (kernel time in µs, or the ratio to the reference), the direction that counts as better, and a checkable stop predicate. The predicate pairs a target with a floor on attempts, so a lucky early win cannot end the run. For example: "at least 50% better than baseline and at least 10 levers screened". Use the user's numbers when given, otherwise agree them. Read the reference's source before you sweep anything (the `lever.menu` port, step 4 of its loop). Compute the byte and FLOP floor once and state the percent of peak you start at (**principle-explain-the-number**).
2. Build the harness, then freeze it.
   - Prove the harness is sensitive. Run contrasting shapes. Confirm that the target shape reproduces the symptom (the gap to the reference, or the dominant stall) and that easier shapes separate as expected. If the harness cannot tell them apart, revise the shapes or the metric (**principle-build-the-lever**).
   - Time with `run_perftest` (aiter) or `triton.testing.do_bench`. Report the median of N, not one run.
   - Gate correctness first (the correctness gate): `allclose` against the torch reference with stated `rtol` and `atol`, plus the NaN count, on every shape and the edge cases (empty group, partial tail tile). A speed number that skips the gate does not count (**principle-correctness-before-speed**).
   - Run the reference on the same shapes, the same GPU, and the same session. Print the ratio.
   - Report the regime production uses: hipGraph replay or eager, cold L2 or warm. Measure both regimes when the change touches L2 reuse.
   - Print the error count and the kernel name from a `rocprofv3` kernel trace, so a fallback path cannot pass for the kernel.
   - Vet the harness with the **GPU kernels** section of **benchmark-checklist** before the freeze.
   - Once frozen, one repeatable command emits the metric and the gate result.
   - Record B's metric and one green run of the regression gate before any change. The regression gate is the correctness gate plus the repo tests that must keep passing.
   - Measure the noise floor: run B against B, interleaved, and record the spread. Every "past noise" below means past this spread. Paired, interleaved runs on one GPU decide any close call. Separate runs in separate processes do not.
3. Open the decision log via the **show-me-your-work** skill, with the kernel columns from `references/lever-doc.md`. In ticket work it is `<tickets>/<KEY>/decision.tsv`. Read it before each attempt. Keep it out of the tree (gitignored). Open the lever doc next to it. Record B as the frozen baseline commit with its metric. Before each phase, when the `wavescope` resource is set, check for a `notes.json` from the `trace.annotate` port beside the latest trace of B or S*. When one exists, read it and apply its open notes to the lever doc, per its WaveScope notes section. Never write `notes.json`. When `wavescope` is not set, or the `trace.annotate` skill is missing, deliver the trace findings in the reply or the ticket folder instead, skip the `notes.json` loop, write `skipped wavescope: not set`, and ask once per session whether the user uses WaveScope.
4. When the `kb` resource is set, read its `levers` and `failure-modes` roles before Phase 1. Read the KB index recorded in the env file, then the index of each role's folder, then the matching notes. Cite the notes. Use the `levers` notes to name and premise levers alongside the `lever.menu` port. Use the `failure-modes` notes for known dead ends and decision heuristics. A lever that the `failure-modes` role of the `kb` resource records as a dead end for the same mechanism starts as `retired`. Its root cause is the one the KB note states, its Evidence is the note, and its `Retry if` is the note's stated condition, or "new evidence that the premise holds here". Screen it only when that `Retry if` holds now. A role that is `not set` is skipped: write `skipped kb <role>: not set` in the decision log, ask once per session whether the user has one (`references/resources.md`), and continue.
5. Name a lever for every hypothesis. Take it from the `lever.menu` port, or from the `compiler.knob` port for a compiler flag. Classify the bottleneck before you pick, with the counter pass that the `lever.menu` diagnosis names. When the diagnosis does not rank the levers, order them by the performance mantras in step 2 of the Perf issue playbook (`playbooks/perf-issue.md`). Borrow only their order, not that step's stop rule. State the premise of each lever as a checkable fact about the ISA or a counter. "Try a different tile size" is not a hypothesis. Give each lever an ID and a row in the lever table. Every lever respects the `Hard limits` in the lever doc header. A lever that a `rejected` note retired comes back only with new evidence.
6. PHASE 1, SCREEN. Measure every lever against B.
   - Hand each edit to a subagent in its own worktree of the target repo, branched from B (**principle-separate-before-serializing-shared-state**). One lever per worktree. Give it the lever, the files, and the gate. Use your configured hillclimb model (default `claude-sonnet-5-5-high`) with a tight scope. Supervise and review the diff, do not type it (**principle-guard-the-context-window**).
   - Run the regression gate. A failure is class `broken`. Do not time it.
   - Run the `isa.diff` port against B. It needs no GPU and takes seconds. New spills or scratch, or a VGPR or LDS rise that crosses an occupancy step (fewer waves per SIMD), skips the benchmark and the lever is class `cost-exceeds`, unless the lever's point is to trade occupancy for speed and the hypothesis said so. A rise inside the same occupancy step is benchmarked, so a possible uplift is not skipped. Record the diff as evidence.
   - Check the change reached codegen (**principle-prove-it-reached-codegen**). An unchanged ISA or IR is class `broken` when the edit should have moved it, and class `premise-wrong` when the knob is inert.
   - Fan out edits, builds, and ISA checks. Benchmarks queue on the lock of the `bench.run` port, one per GPU.
   - A lever that beats B past noise with the gate green and no tracked shape regressing past noise is a winner. A lever that wins on one shape and loses on another is a winner for that shape. Note the shape. A lever that "might help" but stays inside noise is not kept.
   - Correctness and simplicity outrank the number. Revert a win that breaks behavior. It is class `broken`. Keep a simplification that holds the number. A lever that removes code and stays inside noise of the baseline is kept, noted as a simplification (**principle-subtract-before-you-add**).
   - Every other lever is a loser. Classify it at once, with evidence (trace, ISA diff, or counter). The classes and their retry rules are in `references/lever-doc.md`.
   - You write each lever's `decision.tsv` rows, from its diff, gate, ISA diff, and bench artifact, never from the delegate's summary. The brief asks the delegate to end its report with each direction it tried and dropped, and why. A delegate that stops before it reports (turn cap, crash, abort) loses that list. Read the delegate's transcript, and log each dropped direction as one row with its reason. A lever with no measurement stays `queued`.
   - Update `<tickets>/<KEY>/STATUS.md` with one line: W, L, and the best single lever.
   - Each phase ends in a check before the next begins (**principle-sequence-verifiable-units**).
7. PHASE 2, COMBINE. Using all the winners can be worse than using a subset. One winning lever can cancel another's gain.
   - ALL is B plus every lever of W. Build it, run the regression gate, and measure it. Do the same for every subset.
   - Search the subsets of W for the best subset S*.
     - Four winners or fewer: build and measure every subset. That is at most 11 builds and benches, the singletons already being measured in Phase 1.
     - More than four: backward elimination from ALL. Drop the lever whose removal helps most. Repeat until no removal helps. That is about n to n² benches.
   - A subset beats another only past noise. Use the median of N, interleaved A/B on one GPU.
   - Subsets matter, not order. Build both orders only when two levers edit the same lines.
   - S* lives on one combo branch. One kept lever is one commit, staged by file, never `git add -A`.
   - Ablate S*. For each lever in S*, revert its commit on a scratch branch, build, and measure. The marginal gain is the metric without it minus the metric of S*. Drop a lever whose marginal gain is inside noise or negative (**principle-subtract-before-you-add**). Reclassify it `masked` with `Retry if: S* changes`, so it is not retried against the S* that just dropped it.
   - If prefill and decode, or any two shapes, prefer different subsets, make the lever a shape dispatch. It may be a knob while you search, and it becomes a fixed dispatch rule before the PR (**Opening a PR**, Production-ready). A load-layout lever that helps prefill and hurts decode is the pattern. If one subset must serve all shapes, pick by the production mix from step 1.
   - Update `<tickets>/<KEY>/STATUS.md` with one line: S*, its metric, and the gain over B.
8. PHASE 3, REVISIT. Do not retire a loser until its root cause shows the premise is wrong. Do not skip any uplift from an idea that still has potential.
   - Take each retry-eligible loser. A loser is eligible when its `Retry if` condition holds now.
   - Build it on top of S*, gate it, run the `isa.diff` port against S*, and measure it against S*.
   - A win joins S* as one commit. Return to Phase 2 for ablation only, because a new lever can change the marginal gain of the old ones. Then run the eligible losers again against the new S*. Repeat until a full pass adds nothing.
   - A loser that fails on the current S* waits with its condition. It becomes eligible again only when S* changes or the condition is met.
   - A `noise` loser is re-measured once with more runs, then reclassified by its root cause.
   - A loser whose premise is dead is retired. A retirement needs a root cause, its evidence (trace, ISA diff, or counter), and a `Retry if` condition. Without all three, the lever is not retired. It stays a loser.
   - A new lever from the plateau trace or a probe (such as a layout lever that a copy probe and a remove-one-piece probe pointed at) is screened against the current S*, not the stale B.
   - A premise change (such as a change that removes an output three levers tuned) re-screens the affected levers against the new baseline, then reruns Phase 2. Supersede the old rows in `decision.tsv`. Do not edit them.
   - Push past the first plateau. A stall is three measured levers in a row in `decision.tsv` with no new best. At a stall, first get a second opinion from another model family. Spawn one readonly reviewer on the `arena cross-judge pool` model whose family differs from yours, and give it the paths of `decision.tsv`, the lever doc, and the latest trace. It answers persist or pivot, names the axis it thinks the search circles, and proposes the next lever with a checkable premise. You decide. Log its answer as one row. Then pivot the bottleneck category, build two near-misses together, re-read the reference source, or try a more radical change before you conclude no further gain exists.
   - At a plateau, stop guessing. Capture an ATT trace of S* (the `trace.capture` port) and read it with the `trace.analyze` port, or the `trace.annotate` port when the `wavescope` resource is set. In ticket work with that resource, publish the findings through the `trace.annotate` port, so the human can verify them in WaveScope. An `annotations.json` already on the trace is a prior round: read it, do not restate it. The human's `notes.json` reply feeds the next phase, per step 3. When `wavescope` is not set, or the `trace.annotate` skill is missing, deliver the trace findings in the reply or the ticket folder instead, skip the `notes.json` loop, write `skipped wavescope: not set`, and ask once per session whether the user uses WaveScope. Pick new levers from the stall that dominates, and the trace is also the evidence to reclassify `masked` losers. When the trace points at a redesign rather than a lever, run **Bound probe** (`playbooks/bound-probe.md`) before you build it. If the loop is unattended, borrow only the wake mechanism from the Autonomous run playbook (`playbooks/autonomous-run.md`), not its stop rule.
   - Update `<tickets>/<KEY>/STATUS.md` with one line: S*, joins this phase, and the retired count.
9. STOP when no retry-eligible loser is left and S* is stable. Do not relax the predicate to meet it, and do not quit while a cheap untried lever remains. If the predicate is met earlier, still finish the Phase 3 pass for eligible losers, and list any untried one as open. If the remaining levers are marginal and not worth their cost, stop and list them as open with that reason. If you are stuck, report it to the user instead of repeating attempts. Name the structural gap that remains when you stop short.
10. Run **Deliver**. The finding carries S*, the ablation table, and the retired list with reasons. A retired lever whose root cause is general is a candidate for the `kb.capture` port. General means true for any kernel with that mechanism, not tied to this ticket's shapes or machine. Offer those levers in the Deliver reply, and run the port only after the user says yes. When `kb` is not set, skip the offer and write `skipped kb: not set`. The numbers, shapes, and SHAs stay in the lever doc. Code output opens a PR per **Opening a PR**, with the commits of S* in the order they landed. A ticket result becomes a comment draft.

**Reply:** the kernel, arch, and GPU. The metric and target. Baseline to final with the percent delta, and the percent of the HBM or MFMA peak at the end. S* and its ablation table in one line per lever. Levers screened, won, and retired. ISA resource delta, the `decision.tsv` and lever-doc paths, and the one lever you would try next.

#### Non-kernel metrics

For a metric that is not a GPU kernel (compile time, a test suite's runtime, a host-side script), run the same loop with these changes.

- Skip the GPU steps: no `isa.diff`, no GPU lock, no `rocprofv3` kernel-name check.
- The regression gate is the repo's tests. It replaces the `allclose` gate.
- When changes can interact, keep the screen, combine, and revisit phases. When they cannot, run one change, one measurement, keep or revert, with one log row each.
- Vet the number with the **Host-side code** section of **benchmark-checklist** before you freeze the harness.
- Keep the median of N and the noise floor from step 2.
