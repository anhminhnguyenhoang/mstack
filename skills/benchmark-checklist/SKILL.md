---
name: benchmark-checklist
description: "Vet a perf measurement (limiter, tuning, limits, errors, repeatability, relevance, and whether the work happened) before you report or act on it. Use when you run a benchmark or report a speedup or regression you measured."
disable-model-invocation: true
---

# Benchmark checklist

Use this when you produce a performance number: a PR's before and after, a regression claim, a hillclimb harness, or a library or config choice. Answer each question with evidence from a run, not a guess about the code.

For a quick ballpark the user asked for, one run is enough. Still check questions 4 and 7, and say that it is one run. Skip the rest unless that run looks wrong. A choice between options is never a ballpark.

## Before you run anything

- Write down the claim you expect to make, in the words you would ship ("export is 30% faster at p50 on the 60k-row dataset"). The questions test that sentence.
- Read the measurement script. Note what it times, counts, and ignores.
- Check the load average with `uptime` and the core count with `nproc`. If the machine is busy, find out what is running. If you cannot stop it, interleave the sides so both see the same noise, and say so in the report.

## The questions

1. **Why not double?** Name the limiter. Profile in a run you do not report, because profilers and tracers slow the work down. Use CPU per process (`top`, `pidstat`), a runtime profiler (`node --cpu-prof`, `py-spy`, `perf`), I/O wait, and syscall counts (`strace -c` on Linux), then map the hot spot to source. Watch the load generator too: if it saturates first, you measured the load generator. If a change did not move the number, the limiter explains why, so find it before you call the change useless.
2. **Was it tuned?** Run every side the way production runs it: release builds, production flags and env, batching and transaction settings, connection pools, caches as warm or cold as production sees them, and the same versions and data. If one side runs on defaults, you compared configurations, not implementations. A limiter that is a setting (a commit per row, a debug build, a missing index) means that side is untuned. Tune it and measure again before you pick a winner. If you cannot tune it, do not pick a winner from that run. When the user is choosing what to adopt, narrowing the claim to the code as it ships today does not fix this, because they adopt the option, not today's settings.
3. **Did it break limits?** Do the arithmetic. Compare bytes per second with disk and network bandwidth, operations per second times cost per operation with your cores, and the time saved with the time the changed piece took. Removing a piece that takes 10% of the run can make the run at most about 11% faster. A result past a limit measured something other than the work, such as a cache, a no-op, or a bug.
4. **Did it error?** Count failures and non-success responses, and check that outputs are correct, not just present. Rejections are often fast, and timeouts and retries are slow. If the script does not count errors, add the count.
5. **Does it reproduce?** Run each side at least 5 times, alternating (A, B, A, B, and so on) so warmup, lazy initialization, caches, and drift favor neither. Report the median and range. A gap smaller than the run-to-run variation is no measurable difference. When the call is close, use a rank-sum test or the harness's own statistics.
6. **Does it matter?** Next to any micro result, measure the end-to-end path a user waits on, with realistic data sizes and concurrency, and report the micro result as a share of the whole. A helper that takes 1% of a request can make the request at most 1% faster, however fast the helper gets.
7. **Did it even happen?** Confirm the work ran inside the timed region: the request reached the server, the rows were written, the bytes were read, and the code used the result. Lazy code (generators nobody iterates, promises nobody awaits, results the JIT can discard) and timeouts produce numbers for work that never happened.

## GPU kernels

Use this section for a number from a GPU kernel on AMD Instinct (MI300X `gfx942`, MI355X `gfx950`). It adds to the questions above and does not replace them. Questions 1 to 7 still apply, read as below. A claim without an arch, a GPU, and an image or ROCm version is not a GPU claim.

**Before you run.**

- Run `rocm-smi` and check the target GPU is idle: no other process, near-zero utilization and VRAM use. A shared GPU makes the run inconclusive.
- Use the same GPU id for both sides (`HIP_VISIBLE_DEVICES`, or `ROCR_VISIBLE_DEVICES` inside a container). Different GPUs of one host differ by several percent.
- Note clocks and power state from `rocm-smi`. Say so when the GPU is not in its normal performance state.
- Clear the JIT caches so both sides compile fresh, and exclude compile time from the timed region. For FlyDSL and aiter, clear the cache directories the build uses, and check the resolved paths before you delete anything.
- Record the arch, the ROCm and torch versions, the docker image, and the repo SHAs (`~/aiter`, `~/FlyDSL`) for both sides.

**The questions, for a kernel.**

1. **Why not double?** Name the limiter: HBM bandwidth, MFMA throughput, LDS, latency, or launch overhead. Take it from one unreported `rocprofv3` counter pass or an ATT trace, not from the source. The diagnosis step of the `lever.menu` port names the counters to read. Use the `trace.analyze` port, or the `trace.annotate` port in the WaveScope loop, to go further. Ports resolve in `../ateam-mode/references/ports.md`.
2. **Was it tuned?** Both sides use the same compile flags, the same torch and ROCm, and the same launch mode. Eager and hipGraph differ in launch cost, so compare like with like. A Triton baseline gets its autotune run. A FlyDSL or aiter side gets its tuned config for that shape (the `config.tune` port).
3. **Did it break limits?** Do the roofline arithmetic. Bytes moved divided by time gives bytes per second, to compare with the HBM peak. FLOPs divided by time gives FLOP/s, to compare with the MFMA peak for that arch and dtype. State the percent of peak, per the **principle-respect-the-roofline** principle skill. A result above the HBM peak measured the L2 or MALL cache, not HBM. Evict inputs between launches for a cold-cache number.
4. **Did it error?** Check the output against a torch reference with `allclose`, state `rtol` and `atol`, and count NaN and inf. A fast wrong kernel is not a result (the **principle-correctness-before-speed** principle skill).
5. **Does it reproduce?** Warm up first. Flush the L2 between timed launches when the kernel is cold in production, and say which regime you report. Alternate sides (A, B, A, B). A fixed-config kernel reports the median of N launches. An autotuning baseline (such as Triton with `@triton.autotune`) reports either the median after you exclude the autotune trial dispatches, or its min or p10. State which. One benchmarked call can fire many trial-config dispatches, and the slow trials inflate the median by 30 to 40 percent. Both regimes can flip the verdict for an L2-sensitive change, so measure both for one.
6. **Does it matter?** Report the kernel as a share of the model step (for example the mHC seam as a share of a DeepSeek decode step or prefill chunk). A fast kernel on 1% of the step is 1% of the step.
7. **Did it even happen?** Confirm the kernel name appears in a `rocprofv3` kernel trace. Match the full kernel name exactly, because a short substring can match the wrong kernel. Confirm that it is the kernel you meant and not a fallback path. For a knob or flag, confirm the ISA or IR changed (the **principle-prove-it-reached-codegen** principle skill).

**Peaks.** Do not quote a peak from memory. State the peak, its source, the arch, and whether it is per GCD or per module. Local references:

- `~/KernelForge/knowledge_base/shared/gemm_roofline.md` lists HBM bandwidth as 5.3 TB/s (MI300X), 6.0 TB/s (MI325X), and 8.0 TB/s (MI355X). It lists max-achievable BF16 and FP8 TFLOPs as about 650 and 1300 (MI300X) and about 1260 and 2500 (MI355X), and says to use these instead of vendor peak.
- The `hardware/` area of the knowledge base (`~/.cursor/mstack/env.md` Knowledge base table, default `~/knowledge-base/`) holds the MI355X vendor peaks in its MI350 family note. Cite the note file you used.
- `~/FlyDSL/docs/kernel_tuning_guide.md` gives gfx942 peaks per GCD (about 653 TFLOPS FP8 and 326 TFLOPS BF16), which differ from the module-level table above. Name which you used.
- Achievable bandwidth sits below peak. `~/KernelForge/local_knowledge/flydsl/operators/reduction/numerics.md` puts the MI300X BabelStream-class ceiling at about 4.3 TB/s. `~/SILOTIGER-1164/comment-draft-in-model-targets-feasibility.md` measured a best-case copy at 5.86 TB/s on MI355X. Measure a copy of the same bytes on the same GPU when the claim is near the floor.

If the arch or dtype is not in these files, say the peak is unstated and give the number with its source before you compute a percent.

## Report

- Lead with the verdict: faster, slower, no measurable difference, or inconclusive.
- Give the number with its unit, the run count, the range, and the limiter. For example, "p50 41 ms → 33 ms, median of 7 runs per side, range 32 to 35 ms after, bound by JSON parsing on one core."
- Call the verdict inconclusive when you claim a difference but cannot name the limiter, when a side ran untuned, or when you could not check questions 4 and 7. Name the gap.
- Keep a PR body to one primary number, per the **Opening a PR** playbook. Put the runs, range, and limiter evidence in a linked artifact or notes file.

## Other perf material

- Vet the **Perf issue** playbook's baseline before the playbook plans from it, and every number after that.
- Vet the **Hillclimb** playbook's harness before it is frozen. The frozen harness then prints error and work counts, so each keep-or-revert checks questions 4 and 7 for free.
