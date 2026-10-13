---
name: principle-explain-the-number
description: "Apply before you trust, report, or act on a number you measured: a speedup, a regression, a throughput, a latency, or an eval result. Find what limits it, state a GPU kernel number as a percent of peak with the peak's source, and rule out that it measured something other than the work you think."
disable-model-invocation: true
---

# Explain the Number

- **Ask "why not double?"** Name the resource or code path that bounds the result: HBM bandwidth, MFMA issue, LDS, VMEM issue, occupancy, or launch overhead. For host-side work it is a core, a lock, the disk, or the network. Get it from a profile or from counters taken during a run (`rocprofv3` counters or an ATT trace for a kernel), then map it to source. A guess from reading the code is not a limiter. If you cannot say why the number is not twice as good, you do not know what you measured.
- **List what else the number could be measuring, and rule out each one with evidence.** The usual suspects are errors, skipped or cached work (a warm L2 or MALL), code that never ran (a fallback kernel), an untuned side (one left on default settings), noise, and a piece too small to matter end to end.
- **Keep the evidence with the number.** Put the run count, the spread, and the limiter in the notes or a linked artifact.

## GPU kernel numbers

- **Every kernel perf claim carries a percent of peak.** Divide bytes moved by time and compare with the HBM bandwidth. Divide FLOPs by time and compare with the MFMA throughput for that dtype. Name the arch (`gfx942` or `gfx950`) and say which side of the ridge the kernel sits on. "2x faster" without a percent of peak does not say how far the kernel is from the floor.
- **Look in your references first.** When configured, cite a `refs` source tagged `peaks` or `roofline`, or the `hardware/` area of the `kb` resource. Cite the file you used. Otherwise state the peak with its public source.
- **Name the source of the peak.** Cite the file, table, or measurement the denominator came from. State whether it is vendor peak, max-achievable, or a measured copy ceiling, and whether it is per GCD or per module. Never quote a peak from memory.
- **Below 80% of the limiting peak, there is headroom. Above 100%, the number is wrong.** Above the HBM peak the kernel read the L2 or MALL cache, or skipped the work. Check for it before you celebrate.
- **Optimize the limiter, not the other axis.** A memory-bound kernel gains from fewer bytes and better access patterns, not from MFMA scheduling. A compute-bound one gains from the reverse. If a lever moves the wrong axis, expect no change.

For a performance number, run the full procedure with the [benchmark-checklist](../benchmark-checklist/SKILL.md) skill. For an eval result, ask the same of the trials: did every run do the task, does the gap hold across trials and models, and does the scenario matter.

You skipped this when the evidence behind a number has no run count, no spread, or no named limiter, when a kernel speedup has no percent of peak or the peak has no source, when a lever targets an axis the kernel is not bound by, or when the time saved is larger than the time the changed piece took.

Distinct from [Prove It Works](../principle-prove-it-works/SKILL.md), which checks that an output is real.
