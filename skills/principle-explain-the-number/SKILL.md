---
name: principle-explain-the-number
description: "Apply before you measure, and before you trust, report, or act on a number you measured: a speedup, a regression, a throughput, a latency, or an eval result. Find what limits it, state a GPU kernel number as a percent of peak with the peak's source, and rule out that it measured something other than the work you think."
disable-model-invocation: true
---

# Explain the number

- **Write the decision before you run.** Name the result that would change it, and the noise floor. Stop when the run-to-run spread is larger than the effect.
- **Ask "why not double?"** Name the resource or code path that bounds the result, from a profile or counters taken during a run (`rocprofv3` or an ATT trace for a kernel). For a kernel, the limiter is HBM bandwidth, MFMA issue, LDS, VMEM issue, occupancy, or launch overhead. A guess from reading the code is not a limiter.
- **List what else the number could be measuring** (errors, skipped or cached work such as a warm L2 or MALL, code that never ran such as a fallback kernel, an untuned side, noise, a piece too small to matter) and rule out each one with evidence.
- **Keep the run count, the spread, and the limiter with the number.**

## GPU kernel numbers

- **Every kernel perf claim carries a percent of peak.** Divide bytes by time and compare with HBM bandwidth. Divide FLOPs by time and compare with MFMA throughput for that dtype. Name the arch (`gfx942` or `gfx950`) and the side of the ridge the kernel sits on. "2x faster" alone does not say how far the kernel is from the floor.
- **Source the peak.** When configured, cite a `refs` source tagged `peaks` or `roofline`, or the `hardware` role of the `kb` resource. Otherwise cite the public source. State whether it is vendor peak, max-achievable, or measured, and whether it is per GCD or per module. Never quote a peak from memory.
- **Below 80% of the limiting peak, there is headroom. Above 100%, the number is wrong.** Above the HBM peak, a cache (L2 or MALL) served the reads or work was skipped. Check before you report the number.
- **Optimize the limiter, not the other axis.** A memory-bound kernel gains from fewer bytes and better access, not MFMA scheduling. A compute-bound one gains from the reverse. A lever on the wrong axis gives no change.

For a performance number, run the [benchmark-checklist](../benchmark-checklist/SKILL.md) skill. For an eval result, ask whether every run did the task, whether the gap holds across trials and models, and whether the scenario matters.
