### Trace forensics

**You own the diagnosis from the artifact.**

Distinct from **Runtime forensics**, which instruments the live process. Here the capture already exists. The artifact is a fixed dataset. Read it and do not re-run it. GPU artifacts are the main case, and step 1 routes them to the AMD tools.

1. Identify the format and load it with the right tool. Route GPU artifacts by format, through the skill functions in `references/skill-functions.md`:
   - An ATT decode directory (holds `code.json`, `filenames.json`, `occupancy.json`, `se*_wv*.json`) goes to the `trace.annotate` skill function when the `wavescope` resource is set. Read `notes.json` first when it exists. WaveScope shows the annotations. When `wavescope` is not set, or the `trace.annotate` skill is missing, deliver the trace findings in the reply or the ticket folder instead, skip the `notes.json` loop, write `skipped wavescope: not set`, and ask once per session whether the user uses WaveScope. For a hotspot plan, use the `trace.analyze` skill function.
   - A `rocprofv3` CSV or database (kernel trace, PMC counters) goes to the `trace.analyze` skill function.
   - Final ISA (`.s`) or LLVM IR (`.ll`) dumps go to the `compiler.knob` skill function to read them, and the `isa.diff` skill function for VGPR, SGPR, spill, scratch, and LDS counts.
   - A host-side process artifact (cpuprofile, spindump, heap snapshot): use the generic parser or viewer for that format, then follow steps 2 to 6.

   Parse large artifacts in a subagent (the **principle-guard-the-context-window** skill) and keep the reduced finding in the main thread.
2. Transform the raw artifact into a form you can query. Do this before you read. An ATT decode is already JSON. Use the viewer's CLI queries rather than a new parser when the `wavescope` resource is set (the `trace.annotate` skill function, section 0). Without it, read the JSON files directly. A `rocprofv3` CSV loads as a table. For any other large artifact, dump it into sqlite, one row per sample, frame, or node.
3. Narrow to the cause. For an ATT trace, find the instructions with the most stall cycles and the stall type (`s_waitcnt`, barrier, MFMA dependency). For a `rocprofv3` trace, find the kernels with the most total time, and check occupancy and the L2 and HBM counters. For a host-side artifact, query the frames that hold the most time and walk the call tree to the hot path.
4. Attribute to source. Map the hot instruction or frame to file, symbol, and line via the artifact's own symbols. A hotspot with no source mapping is not yet a diagnosis. Resolve the symbols, or say the artifact does not carry them. A GPU trace maps ISA to source lines only when the capture carried debug info. If it did not, recapture per the `trace.capture` skill function and say you did. Source lines that shift or land on blank lines are a capture defect. Fix it per the same skill function and recapture.
5. If you have a paired capture, diff the before and after artifacts to confirm. Otherwise, mark the finding as the strongest hypothesis the artifact supports, not a confirmed cause.
6. Hand back a cited diagnosis and no fix unless asked. Route to Bug fix, Perf issue, or **Kernel hillclimb** once the cause is known. Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only forensics`.

**Reply:** the artifact and format, the reduced finding, the source location, the artifact paths, and whether a paired capture confirmed it.
