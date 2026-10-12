### SGLang in-model measurement

Use this when a kernel ships into an SGLang model and the claim must hold end to end. The sources are the owner's SILOTIGER-1164 probes (`~/SILOTIGER-1164/b1/`, `b4/`, `b5/`, `bench_v0521_per_side.py`, `comment-draft-v0521-validation-and-tp4-rebase.md`) and the SGLang checkout's own docs (`docs_new/docs/developer_guide/benchmark_and_profiling.mdx`). Host, container, and GPU facts are in `~/.cursor/mstack/env.md` (`references/env.md`). The values below are the SILOTIGER-1164 ones, as worked examples. Take the real values from the ticket you work on.

```
isolated bench ──► in-model share ──► in-model A/B ──► serving sweep
 (kernel µs)       (µs, % of step)    (ms per step)    (tok/s, TPOT)
   cheap             profile only      swap, same run    PR-level claim
```

Run the cheapest rung that settles the claim. Go up a rung when the rung below cannot answer "does it matter" (benchmark-checklist, GPU kernels, question 6).

#### When to measure in-model

- The claim names a model step, a chunk, or throughput, not a kernel time.
- The isolated number and the in-model number can differ. In B1 the isolated seam total was 226.4 µs per boundary and the in-model total was 190 to 203 µs. The isolated sinkhorn took 38.4 µs and the in-model one 23 µs.
- The baseline is an SGLang kernel. SGLang may pick another kernel per shape or phase (HIP at prefill, Triton at decode).
- A ticket target is stated as ms per chunk or ms per step.

Skip it for a kernel that SGLang does not call. Say so, and give the isolated number with that label.

#### Pins

Write these on every row before you compare. A number without them is not an SGLang claim.

| Pin | How to get it, with the SILOTIGER-1164 value |
|---|---|
| Docker image tag and digest | `lmsysorg/sglang:dev-dsv41-mi35x` (B1), `lmsysorg/sglang:v0.5.21-rocm720-mi35x` (B4, B5) |
| SGLang version and the path it loads from | `python3 -c "import sglang; print(sglang.__file__)"`, as `b4_run.sh` prints it. An overlay on `PYTHONPATH` wins over the image |
| SGLang overlay SHA and PR | B4 and B5 overlay `python/sglang` from the head of SGLang PR #42055. Upstream v0.5.21 defines the Single-Pass boundary kernels and does not call them |
| aiter SHA and flydsl version | `4ad99832` in B1. B5 installed flydsl 0.3.4.1 for both arms because the image ships 0.3.2 |
| Model and weights | DeepSeek-V4.1-Flash, `--load-format dummy` |
| Parallelism | `--tp 2` (B1), `--tp 4` (B4, B5) |
| Prefill chunk | `--chunked-prefill-size` 4096 (B1), 16384 (B4, B5) |
| Decode batch | bs = 32 (B1), bs = 4 (B4, B5) |
| Dtype and quant format | `--kv-cache-dtype fp8_e4m3`, and the output format the seam writes (bf16, `fp8_grid`, `mxfp8`) |
| Other server flags | `--attention-backend dsv4 --page-size 256 --disable-radix-cache --swa-full-tokens-ratio 0.15 --disable-shared-experts-fusion --mem-fraction-static 0.85`, and `--random-seed 0` in B5 |
| GPUs | `HIP_VISIBLE_DEVICES`, and the arch from inside the container |

Pin every server flag the run passes, not only the ones the ticket names. When the ticket does not fix a flag that moves the result (attention backend, page size, EP setting, memory fraction), ask the human once and record the answer in `~/<KEY>/STATUS.md`. B1's `readiness.md` §7 shows the cost of guessing them.

#### Measure a kernel's share of a step

The B1 method. Server mode, so the real scheduler, chunking, and CUDA graphs run.

1. Set `SGLANG_TORCH_PROFILER_DIR` and start the server with the pins above. Wait for `The server is fired up`. Capture takes about 9 minutes on B1.
2. Check the GPUs are idle (`rocm-smi --showuse --showmemuse`). Keep `HIP_VISIBLE_DEVICES` on the server. `/dev/dri` shows every GPU, so a typo uses another one.
3. Warm up with 2 prefills and 1 short decode. The HIP module and the Triton kernels JIT on first use.
4. Prefill. `POST /start_profile` with `output_dir`, `activities: ["GPU"]`, and `profile_prefix`. Send 3 requests one at a time, each of exactly the chunk size in random token ids with `max_new_tokens=1`. `POST /stop_profile`. Each request is then one chunk.
5. Decode. Start bs concurrent requests with a 128-token prompt, a long `max_new_tokens`, and `ignore_eos`. Wait 15 to 20 s until all run in graph decode. Profile a window, then stop. The profiler records one graph-replayed step per window, so take several 1 s windows (`b1_decode_multi.py`).
6. Parse the per-rank `*.trace.json.gz`. Keep events with `ph == "X"` and `cat == "kernel"`. Classify by name substring (`b1/analyze.py`, `b4/analyze_b4.py`).
7. Cut one forward at a time. Take the prefill chunk from the layer-0 kernel to the first graph-replayed kernel. Take the decode step from one dense cluster of kernels with gaps under 500 µs.
8. Report per-call µs, calls per forward, ms per forward, and the share of the chunk or step wall. Use medians over rank × chunk or rank × window. Print the spread.

Check each of these before you trust a share.

- The server log shows `#new-token: <chunk>` for each profiled request and `cuda graph: False` for prefill. A kernel grid with the token count as a dimension confirms it too.
- The call count per forward matches the model (80 seams in a 40-layer model, not 77).
- The kernel names are the ones you meant, not a fallback (benchmark-checklist question 7).
- The regime is stated. Prefill ran eager. Decode ran graph replay, and the trace has no grid for replayed kernels.

`b1/readiness.md` §6 and `b1/b1_run.sh` have the full command. `one_batch` (`python -m sglang.benchmark.one_batch ... --profile`) is the lighter option in B1's notes. B1 did not verify that it honors chunked prefill. The checkout's docs name `sglang.bench_one_batch` and say it skips the scheduler, so its metrics are unrealistic.

#### Swap a kernel in for an A/B

The B5 method. The kernel that changes is the only difference between the arms.

- Overlay the SGLang tree on the image (`-v <tree>:/sgl_src:ro`, `-e PYTHONPATH=/sgl_src:/mega_pkg`). Vendor your kernel as a package in the same overlay, so the image's own aiter stays untouched. Check the vendored copy is bit-identical to your worktree on a case sweep (`b5/vendor_check.py`).
- Put the swap behind one env flag (`SGLANG_MEGA_MHC=0|1` in B5). Run shim off and shim on with the same image, flags, client, and GPUs. Install the same flydsl in both arms.
- Make the shim count the calls it replaces and the calls that fall back. B5 replaced 80 of 80 seams per forward with 0 fallbacks.
- Check CUDA graph capture still passes. B5 warmed each batch size eagerly on the capture stream first.
- Check numerics on live activations. B5 ran SGLang's path next to the new kernel on the first N eager calls per side, form, and size, and logged the max abs difference and the bit-equal fraction (`SGLANG_MEGA_MHC_CHECK=N`). Graph-replayed decode is not compared.
- Do not use logprobs or outputs as evidence with dummy weights. The distribution is uniform and greedy output cycles between 2 tokens.
- Report the chunk wall and step wall deltas next to the kernel-sum delta. B5: seam −26.8 ms, chunk wall −26.9 ms. Decode seam −0.30 ms, step wall −0.35 ms.

When the swap is not wired yet, time both sides in isolation with the production chain called through SGLang's own functions (`bench_v0521_per_side.py`, `bench_ue8m0_vs_sglang.py`). Use a source snapshot of the SGLang commit (`MHC_SGLANG_SRC`). Use the same shape, form (`post` or `no_post`), and output format as the model. Time both sides with torch-profiler device time (20 calls, median of 5), because SGLang's HIP prefill boundary is not graph-capturable. Label the result an estimate. B5 did this: estimated −0.47 ms per decode step, measured −0.30 ms.

#### Audit an SGLang PR's numbers

Run the **Repro audit** playbook (`playbooks/repro-audit.md`), with these pins added.

- Pin the PR head SHA and the base SHA, not the branch name. A PR moves. SGLang PR #39994 (a draft, 25 commits at capture) merged `main` on 2026-10-06, and its own text says the baseline step went from 21.55 ms to 14.29 ms because of that merge.
- Build the baseline from the PR's merge base, or from the base tip if the PR merged it, and name the SHA. Run base and head with the same server flags. The PR text says its decode-step and throughput rows compare configurations as well as trees.
- Split the PR's claims one per line, as the playbook says: launches per step, ms per kernel, decode step ms, output tokens per second per concurrency, GSM8K mean.
- Run the PR's own commands first: its `launch_server` line and its `bench_serving` line. For the profile, the PR used `--enable-profile-cuda-graph` with `SGLANG_ENABLE_PROFILE_CUDA_GRAPH=1` and `--profile --profile-by-stage`. These flags are in the PR body. They are not in the July checkout's docs.
- Count kernel launches per step from the trace, not from the PR's table. Match each row to a kernel name.
- Ask the author's server settings when the PR text and its commands disagree.
#### Pitfalls from the notes

- **Targets move with the config.** The first targets used TP2, 4096-token chunks, and decode bs = 32: seam 15.58 ms per chunk, 194.7 µs per boundary, 1.37 ms per decode step. The ticket was re-based to TP4, 16,384-token chunks, and bs = 4: seam 57.6 ms per chunk, 719.8 µs per boundary, 0.99 ms per step. A saving against the old base is not a saving against the new one.
- **The boundary count was wrong twice.** The ticket said 77 per chunk, and B1 found 80. The ticket's TP4 trace said 39 `<true>` calls, and B4 found 77. Count calls from the trace.
- **A parser can double-count.** Each profiled prefill request is followed by a tiny graph-replayed decode step with its own boundaries. `parse_trace.py` split by forward count and printed 160 per chunk. B1 replaced it with `analyze.py`.
- **The kernel depends on the phase.** Prefill uses the HIP boundary kernel. Decode uses the Triton partial kernel. In TP4 decode with 8 rows or fewer, every boundary has no pending post, because the all-reduce applies it.
- **The hosting norm differs by side.** The FFN side used aiter `add_rmsnorm_quant` (16 µs). The attention side used Triton `rmsnorm_fake_quant_fp8` (29 µs). An isolated bench that times one of them misses the other.
- **The output format follows the flags.** Without `--fp8-gemm-backend` the MXFP8 consumer is off, so the seam writes bf16 and the fp8 grid. The B4 estimate assumed `bf16` on the FFN side. B5 ran `mxfp8` there, which is part of why decode saved 0.30 ms and not 0.47 ms.
- **Isolated and in-model can disagree either way.** The old image's isolated total was 12 to 19% above in-model. The v0.5.21 isolated SGLang times were within 3%. B1 gives a warm L2 or MALL as the cause and marks it untested.
- **Flag names change with the SGLang version.** B1 passes `--cuda-graph-max-bs`. B4 and B5 pass `--cuda-graph-max-bs-decode`. The July checkout has only the first. Run `launch_server --help` in the image.
- **Server start has known failures on this model.** B1 hit the unified KV layout error (drop `SGLANG_HACK_FLASHMLA_BACKEND`) and an OOM in dummy weight init (set `SGLANG_ENABLE_DSV41_ENGRAM_HOST_TABLE=1`). See `b1/fixlog.txt`.
- **Dummy weights and random tokens.** Seam kernels did not look data-dependent. MoE routing may differ from real traffic. Say so in the caveats.
- **One run per arm is a sample.** B5 ran one server per arm. Say it.
- **Files from the container are root-owned.** `b1_run.sh down` runs a `chown` on the output directory.
- **A profiler error with stacks.** If the trace fails with `Python replay stack is empty`, the checkout's docs give `SGLANG_PROFILE_WITH_STACK=False`.

#### Report

Lead with the verdict and the share. Give the number as µs per call, ms per chunk or step, and the percent of the step. State TP, chunk, batch, regime, image, and the SGLang and aiter SHAs. Mark an isolated-based figure as an estimate.
