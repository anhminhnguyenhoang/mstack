### Trace forensics

**You own the diagnosis from the artifact.**

Distinct from **Runtime forensics**, which instruments the live process. Here the capture already exists. The artifact is a fixed dataset, read it, don't re-run it. Keep tooling generic for CPU artifacts: a DevTools or trace parser for cpuprofile and `.json.gz`, a text editor for a spindump, your heap tooling for a heapsnapshot. GPU artifacts route to the AMD tools in step 1.

1. Identify the format and load it with the right tool. Route GPU artifacts by format:
   - An ATT decode directory (holds `code.json`, `filenames.json`, `occupancy.json`, `se*_wv*.json`) → the **analyze-att-trace** skill. Read `notes.json` first when it exists. WaveScope shows the annotations.
   - A `rocprofv3` CSV or database (kernel trace, PMC counters) → the **kernel-trace-analysis** skill.
   - Final ISA (`.s`) or LLVM IR (`.ll`) dumps → the **llvm** skill to read them, and **isa-resource-diff** for VGPR, SGPR, spill, scratch, and LDS counts.

   Parse large artifacts in a subagent (the **principle-guard-the-context-window** skill) and keep the reduced finding in the main thread.
2. Transform the raw artifact into a form you can query. Dump the trace or heap snapshot into sqlite, one row per sample, frame, or node. Reach the queryable shape before you read. An ATT decode is already JSON. Use the viewer's CLI queries rather than a new parser (**analyze-att-trace**, section 0).
3. Narrow to the cause. Query for the frames that hold the most time and walk the call tree to the hot path. For a leak, follow the retainer chain from the leaked object to a GC root. For a spindump, find the thread stuck on-CPU or blocked and its wait reason.
4. Attribute to source. Map the hot frame to file, symbol, and line via the artifact's own symbols. A frame with no source mapping is not yet a diagnosis. Resolve the symbols, or say plainly the artifact does not carry them. A GPU trace maps ISA to source lines only when the capture ran with `FLYDSL_DEBUG_ENABLE_DEBUG_INFO=1`. If it did not, recapture with that variable set (**capture-kernel-trace**) and say you did. Source lines that land on blank lines or shift mean a stale compile cache. Clear it and recapture.
5. If you have a paired capture, diff the before and after artifacts to confirm. Otherwise, mark the finding as the strongest hypothesis the artifact supports, not a confirmed cause.
6. Hand back a cited diagnosis, no fix unless asked. Route to Bug fix, Perf issue, or **Kernel hillclimb** once the cause is known. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

**Reply:** the artifact and format, the reduced finding, the source location, the artifact paths, and whether a paired capture confirmed it.
