### Kernel hillclimb

**You own the metric and the experiment's integrity. Supervise and review. Delegate the attempts.** Hillclimb for a GPU kernel on AMD Instinct. It adds the GPU harness, a no-GPU ISA pre-check, and one-GPU serialization to **Hillclimb** (`playbooks/hillclimb.md`). Read that playbook for the loop discipline. This one changes the steps below.

Named kernels have their own loop skills. Use `jdbba-autoresearch` or `jdbba-frontier-search` for `jagged_dense_bmm_broadcast_add` on `gfx950`, and `optimize-mla-reduce-flydsl` or `optimize-mla-reduce-traversal-flydsl` for `mla_reduce` on `gfx942`. This playbook is the same loop for any other kernel.

1. Ground the target. Run the **how** skill over the kernel and its reference (the Triton or HIP kernel it must match or beat). Fix the arch (`gfx942` or `gfx950`), the GPU, the dtypes, and the shapes that matter in production. Fix one metric (kernel time in µs, or the ratio to the reference), the direction, and a checkable stop predicate with a floor on attempts. Read the reference's source before you sweep anything (**cdna-kernel-opt**, step 4). Compute the byte and FLOP floor once and state the percent of peak you start at (**principle-respect-the-roofline**).
2. Build the harness, then freeze it.
   - Time with `run_perftest` (aiter) or `triton.testing.do_bench`. Report the median of N, not one run.
   - Gate correctness first: `allclose` against the torch reference with stated `rtol` and `atol`, plus the NaN count, on every shape and the edge cases (empty group, partial tail tile). A speed number that skips the gate does not count (**principle-correctness-before-speed**).
   - Run the reference on the same shapes, the same GPU, and the same session. Print the ratio.
   - Report the regime production uses: hipGraph replay or eager, cold L2 or warm. Measure both regimes when the change touches L2 reuse.
   - Print the error count and the kernel name from a `rocprofv3` kernel trace, so a fallback path cannot pass for the kernel.
   - Vet the harness with the **GPU kernels** section of **benchmark-checklist** before the freeze.
3. Open the decision log via the **show-me-your-work** skill. In ticket work it is `~/<KEY>/decision.tsv`. Add the lever name to each row's hypothesis.
4. Name a lever for every hypothesis. Take it from the **cdna-kernel-opt** menu (pipeline overlap, MFMA atom and layout, intermediate residency, LDS swizzle, XCD remap, epilogue store path, compiler flags), or from **gemm-optimization**, **lds-optimization**, **prefetch-data-load**, **chiplet-xcd-remap**, or **llvm**. Classify the bottleneck with one counter pass (`MfmaUtil`, `VALUBusy`, `LDSBankConflict`, `MemUnitStalled`) before you pick. "Try a different tile size" is not a hypothesis.
5. Loop, one lever per attempt.
   - Hand the edit to a subagent in its own worktree of the target repo, with the lever, the files, and the gate named.
   - Run the correctness gate. A failure reverts the attempt. Do not time it.
   - Run **isa-resource-diff** against the last kept kernel. It needs no GPU and takes seconds. A regression in VGPR, spills, scratch, or LDS rejects the attempt with no benchmark, unless the lever's point is to trade registers for speed and the hypothesis said so.
   - Check the change reached codegen. A lever that does not move the ISA or IR did nothing, so revert it (**principle-prove-it-reached-codegen**).
   - Benchmark on the locked GPU, one attempt at a time (**verify-gpu-kernel**). Never run two benchmarks on one GPU together, and never share a JIT cache directory between sides.
   - Accept only when the metric moves past noise, the gate holds, and no other tracked shape regresses. Commit one accepted lever per commit, staging only the files you changed. Log the row either way.
   Fan-out is for edits, builds, and ISA checks. Each subagent works in its own worktree. Benchmarks queue on the locked GPU.
6. At a plateau, several rejects in a row, stop guessing. Capture an ATT trace (**capture-kernel-trace**) and read it with **analyze-att-trace** or **kernel-trace-analysis**. Pick the next lever from the stall that dominates. Then pivot category, combine near-misses, or re-read the reference. If the loop is unattended, borrow only the wake mechanism from the Autonomous run playbook.
7. Stop when the predicate is met, or when the remaining levers are marginal. Do not relax the predicate. Name the structural gap that remains when you stop short.
8. Run **Deliver**. Code output opens a PR per **Opening a PR**, with the accepted commits in the order they landed. A ticket result becomes a comment draft.

**Reply:** the kernel, arch, and GPU. The metric and target. Baseline to final with the percent delta, and the percent of the HBM or MFMA peak at the end. Iterations run (kept vs reverted), each accepted lever on one line, ISA resource delta, the `decision.tsv` path, and the next lever you would try.
