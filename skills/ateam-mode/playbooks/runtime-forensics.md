### Runtime forensics

**You own the diagnosis. Instrument the live process, don't theorize from source.** The deliverable is a cited diagnosis, not a fix.

1. Capture the live signal on the matching surface via the control skill. For a GPU symptom, run the kernel on a locked GPU (the `bench.run` port), then capture:
   - A slowdown or underused GPU: a `rocprofv3` kernel trace and counters, and an ATT trace for stalls (the `trace.capture` port).
   - A GPU stuck busy or a hang: `rocm-smi` for utilization and the process holding the GPU, then a kernel trace or a reduced repro to find the dispatch that never ends.
   - NaN, wrong results, a crash, or an illegal address: a minimal repro (the `kernel.debug` port).

   Ports resolve in `references/ports.md`. A real artifact, not a guess. For a host-side process, take a CPU profile for a spin or a heap snapshot for a leak.
2. Reduce the artifact to the smoking gun: the kernel or instruction on the hot path, the dispatch that hangs, the first op that produces NaN or a bad address, or for a host process the function on the hot path or the retainer chain from a leaked object to a GC root. Parse large artifacts in a subagent (the **guard-the-context-window** principle skill), keep the reduced finding in the main thread.
3. Prove the mechanism before believing it. For a kernel, add a device-side assert or printf, or run the error-isolation tests of the `kernel.debug` port. Test the hypothesis with the cheapest probe, such as one shape, one block, or one changed flag. For a host process, attach a debugger or add a log line to confirm it.
4. Map the finding back to source: file, symbol, and the line that launches, allocates, or schedules.
5. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

**Reply:** the signal captured, the reduced finding, how you proved the mechanism, the source location, artifact paths. No fix unless asked. Hand back to Bug fix or Perf once the cause is known.
