---
name: benchmark-checklist
description: "Vet a perf measurement (limiter, tuning, limits, errors, repeatability, relevance, and whether the work happened) before you report or act on it. Use when you run a benchmark or report a speedup or regression you measured."
disable-model-invocation: true
---

# Benchmark checklist

Use this when you produce a performance number: a kernel's before and after, a regression claim, a hillclimb harness, or a choice between implementations or configs. Answer each question with evidence from a run, not a guess about the code.

For a quick ballpark the user asked for, one run is enough. Still check questions 4 and 7, and say that it is one run. Skip the rest unless that run looks wrong. A choice between options is never a ballpark.

## GPU kernels

Use this section for a number from a GPU kernel on AMD Instinct (MI300X `gfx942`, MI355X `gfx950`). A claim without an arch, a GPU, and an image or ROCm version is not a GPU claim. Host-side code has its own section below.

**Before you run.**

- Write down the claim you expect to make, in the words you would ship ("the kernel is 1.3x faster than the Triton reference at M=4096 bf16 on `gfx950`, median of 50 graph replays"). The questions test that sentence.
- Read the measurement script. Note what it times, counts, and ignores.
- Run `rocm-smi` and check the target GPU is idle: no other process, near-zero utilization and VRAM use. A shared GPU makes the run inconclusive.
- Use the same GPU id for both sides (`HIP_VISIBLE_DEVICES`, or `ROCR_VISIBLE_DEVICES` inside a container). Different GPUs of one host differ by several percent.
- Note clocks and power state from `rocm-smi`. Say so when the GPU is not in its normal performance state.
- Clear the JIT caches so both sides compile fresh, and exclude compile time from the timed region. For FlyDSL and aiter, clear the cache directories the build uses, and check the resolved paths before you delete anything.
- Record the arch, the ROCm and torch versions, the docker image, and the repo SHAs (each repo in the `repos` resource) for both sides.

**The questions.**

1. **Why not double?** Name the limiter: HBM bandwidth, MFMA throughput, LDS, latency, or launch overhead. Take it from one unreported `rocprofv3` counter pass or an ATT trace, not from the source. The diagnosis step of the `lever.menu` skill function names the counters to read. Use the `trace.analyze` skill function, or the `trace.annotate` skill function when the `wavescope` resource is set, to go further. Without that resource or skill, deliver the trace findings in the reply or the ticket folder, skip the `notes.json` loop, write `skipped wavescope: not set`, and ask once per session whether the user uses WaveScope. Skill functions resolve in `../ateam-mode/references/skill-functions.md`. If a change did not move the number, the limiter explains why. Find it before you call the change useless.
2. **Was it tuned?** Both sides use the same compile flags, the same torch and ROCm, and the same launch mode. Eager and hipGraph differ in launch cost, so compare like with like. A Triton baseline gets its autotune run. A FlyDSL or aiter side gets its tuned config for that shape (the `config.tune` skill function). One side on defaults means you compared configurations, not kernels. Tune it and measure again before you pick a winner. If you cannot tune it, do not pick a winner from that run. When the user is choosing what to adopt, narrowing the claim to the code as it ships today does not fix this, because they adopt the option, not today's settings.
3. **Did it break limits?** Do the roofline arithmetic. Bytes moved divided by time gives bytes per second, to compare with the HBM peak. FLOPs divided by time gives FLOP/s, to compare with the MFMA peak for that arch and dtype. State the percent of peak, per the **principle-explain-the-number** principle skill. A result above the HBM peak measured the L2 or MALL cache, not HBM. Evict inputs between launches for a cold-cache number. Removing a piece that takes 10% of the kernel makes it at most about 11% faster.
4. **Did it error?** Check the output against a torch reference with `allclose`, state `rtol` and `atol`, and count NaN and inf. A fast wrong kernel is not a result (the **principle-correctness-before-speed** principle skill).
5. **Does it reproduce?** Warm up first. Flush the L2 between timed launches when the kernel is cold in production, and say which regime you report. Alternate sides (A, B, A, B). A fixed-config kernel reports the median of N launches. An autotuning baseline (such as Triton with `@triton.autotune`) reports either the median after you exclude the autotune trial dispatches, or its min or p10. State which. One benchmarked call can fire many trial-config dispatches, and the slow trials inflate the median by 30 to 40 percent. Both regimes can flip the verdict for an L2-sensitive change, so measure both for one. A gap smaller than the run-to-run variation is no measurable difference.
6. **Does it matter?** Report the kernel as a share of the model step (for example the kernel's time as a share of one decode step or one prefill chunk). A fast kernel on 1% of the step is 1% of the step.
7. **Did it even happen?** Confirm the kernel name appears in a `rocprofv3` kernel trace. Match the full kernel name exactly, because a short substring can match the wrong kernel. Confirm that it is the kernel you meant and not a fallback path. Confirm that the `imports` path is under the worktree you meant to test. For a knob or flag, confirm the ISA or IR changed (the **principle-prove-it-reached-codegen** principle skill).

**Peaks.** Do not quote a peak from memory. State the peak, its source, the arch, and whether it is per GCD or per module. Take it from the first source that is configured:

- A `refs` source tagged `peaks` or `roofline`. Prefer its max-achievable figure over the vendor peak, and cite the source name and the file.
- The `hardware` role of the `kb` resource. Read the KB index recorded in the env file, then the index of that role's folder, then the note. Cite the note you used.
- Neither is configured: state the vendor peak with its public source. Write `skipped refs: not set` in the report, and ask once per session whether the user has reference docs (`../ateam-mode/references/resources.md`).

Two sources can differ because one counts per GCD and the other per module. Name which you used.

Achievable bandwidth sits below peak. A `refs` source tagged `numerics` or `roofline` may give a measured ceiling. When the claim is near the floor, measure a copy of the same bytes on the same GPU.

If the arch or dtype is not in the source, say the peak is unstated and give the number with its source before you compute a percent.

## Host-side code

Use this section for host-side Python or C++ in the timed path: launch overhead, data prep, a CPU fallback. Ask the same seven questions, in short form.

- Check the load average with `uptime` and the core count with `nproc`. If the machine is busy and you cannot stop the load, interleave the sides and say so.
- **Why not double?** Profile in a run you do not report, because profilers slow the work down. Use `top` or `pidstat` for CPU per process, `py-spy` or `perf` for the hot spot, and `strace -c` for syscall counts. Map the hot spot to source.
- **Was it tuned?** Run every side as production runs it: release build, production flags and env, caches as warm or cold as production sees them. A limiter that is a setting (a debug build, a per-item loop that should batch) means that side is untuned.
- **Did it break limits?** Compare bytes per second and operations per second with the hardware. Compare the time saved with the time the changed piece took.
- **Did it error?** Count failures, and check that outputs are correct, not just present.
- **Does it reproduce?** Alternate sides at least 5 times. Report the median and range.
- **Does it matter?** Report the result as a share of the end-to-end path.
- **Did it even happen?** Confirm the work ran inside the timed region. Lazy code (generators nobody iterates, results the compiler can discard) and timeouts produce numbers for work that never happened.

## Report

- Lead with the verdict: faster, slower, no measurable difference, or inconclusive.
- Give the number with its unit, the run count, the range, and the limiter. For example, "41 µs → 33 µs, median of 50 graph replays per side, range 32 to 35 µs after, bound by `s_waitcnt vmcnt` stalls on the K-tile loads."
- Call the verdict inconclusive when you claim a difference but cannot name the limiter, when a side ran untuned, or when you could not check questions 4 and 7. Name the gap.
- Keep a PR body to one primary number, per the **Opening a PR** playbook. Put the runs, range, and limiter evidence in a linked artifact or notes file.

## Other perf material

- Vet the **Perf issue** playbook's baseline before the playbook plans from it, and every number after that.
- Vet the **Kernel hillclimb** playbook's harness before it is frozen. The frozen harness then prints error and work counts, so each keep-or-revert checks questions 4 and 7 without extra work.
