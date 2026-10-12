---
name: principle-respect-the-roofline
description: "Apply before you report or act on a GPU kernel performance claim. State the claim as a percent of the HBM or MFMA peak for the arch and dtype, with the peak's source."
disable-model-invocation: true
---

# Respect the Roofline

- **Every perf claim carries a percent of peak.** Divide bytes moved by time and compare with the HBM bandwidth. Divide FLOPs by time and compare with the MFMA throughput for that dtype. Name the arch (`gfx942` or `gfx950`) and say which side of the ridge the kernel sits on. "2x faster" without a percent of peak does not say how far the kernel is from the floor.
- **Look in the knowledge base first.** Vendor peaks for the MI350 family are in the `hardware/` area of the knowledge base (`~/.cursor/mstack/env.md` Knowledge base table, default `~/knowledge-base/`). Cite the note file you used.
- **Name the source of the peak.** Cite the file, table, or measurement the denominator came from. State whether it is vendor peak, max-achievable, or a measured copy ceiling, and whether it is per GCD or per module. Never quote a peak from memory.
- **Below 80% of the limiting peak, there is headroom. Above 100%, the number is wrong.** Above the HBM peak the kernel read the L2 or MALL cache, or skipped the work. Check for it before you celebrate.
- **Optimize the limiter, not the other axis.** A memory-bound kernel gains from fewer bytes and better access patterns, not from MFMA scheduling. A compute-bound one gains from the reverse. If a lever moves the wrong axis, expect no change.

You skipped this when a speedup has no percent of peak, when the peak has no source, or when a lever targets an axis the kernel is not bound by.

The **benchmark-checklist** skill's GPU kernels section holds the procedure and the local peak references. Distinct from [Explain the Number](../principle-explain-the-number/SKILL.md), which asks what limits a number. This one fixes what it is compared with.
