---
name: principle-correctness-before-speed
description: "Apply before you time, report, or keep any kernel change. A perf number counts only after an allclose check and a NaN count pass on the same run."
disable-model-invocation: true
---

# Correctness Before Speed

- **Gate every perf number.** Compare the output with a torch reference using `allclose`, and state `rtol` and `atol`. Count NaN and inf. Run it on every shape you time, plus the edge cases: an empty group, a partial tail tile, one long row among short ones.
- **Check more than one metric.** A cosine near 1.0 can hide a wrong tile. Add the mean signed error or the max absolute error. A fast kernel that fails any of them has no speedup.
- **Same run, same inputs.** The check and the timing use the same kernel build, the same shapes, and the same launch path. A check on the eager path does not cover the hipGraph path.
- **Tolerance is a decision, not a knob.** A loosened `rtol` or `atol` needs a stated reason, such as the dtype's rounding. Never widen it to let a change pass.
- **Failure ends the attempt.** Revert or fix first. Do not time a kernel that fails the gate, and do not report a number from one.

You skipped this when a speedup sits next to a failed, unchecked, or loosened correctness row.

The harness prints the correctness result next to the time (**benchmark-checklist**, question 4 of the GPU kernels section). Distinct from [Test Behavior, Not Implementation](../principle-test-behavior-not-implementation/SKILL.md), which shapes a test. This one orders correctness and speed.
