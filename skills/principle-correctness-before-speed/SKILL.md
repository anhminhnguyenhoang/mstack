---
name: principle-correctness-before-speed
description: "Apply before you time, report, or keep any kernel change. A perf number counts only after an allclose check and a NaN count pass on the same run."
disable-model-invocation: true
---

# Correctness before speed

- **Gate every perf number.** Compare the output with a torch reference using `allclose`, and state `rtol` and `atol`. Count NaN and inf. Run it on every shape you time, plus the edge cases: an empty group, a partial tail tile, one long row among short ones.
- **Check more than one metric.** A cosine near 1.0 can hide a wrong tile. Add the mean signed error or the max absolute error. A fast kernel that fails any of them has no speedup.
- **Low precision adds a scale-free metric.** For an fp8, fp4, or mxfp4 path, also report the SNR in dB, `10·log10(Σ ref² / Σ (out − ref)²)`, against a reference that takes the same quantized inputs. The wide `rtol` these dtypes need can pass a wrong kernel. A register bug that silently dropped values measured 21 dB. The check fails when the SNR is more than 3 dB below the baseline on the same shapes, unless the lever's hypothesis trades precision and says so.
- **Same run, same inputs.** The check and the timing use the same kernel build, the same shapes, and the same launch path. A check on the eager path does not cover the hipGraph path.
- **Tolerance is a decision.** Loosening `rtol` or `atol` needs a stated reason, such as the dtype's rounding. Never widen it to let a change pass.
- **Failure ends the attempt.** Revert or fix first. Do not time a kernel that fails the gate, and do not report a number from one.

You skipped this when a speedup sits next to a failed, unchecked, or loosened correctness row.

The harness prints the correctness result next to the time (**benchmark-checklist**, question 4 of the GPU kernels section). Distinct from [Test behavior, not implementation](../principle-test-behavior-not-implementation/SKILL.md), which shapes a test. This one orders correctness and speed.
