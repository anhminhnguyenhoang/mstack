### Kernel skill map

Routing for AMD GPU kernel work (aiter, FlyDSL, Triton, HIP/MFMA on `gfx942` and `gfx950`). The skills live in `~/.claude/skills/<name>/SKILL.md`. Read the skill before you apply it. Run the cheapest check that can settle the question first.

```
write ──► optimize ──► debug ──► prove ──► test ──► ship
                         ▲          │
                         └── regress┘
```

| Stage | Task | Skill |
|---|---|---|
| Write | New FlyDSL kernel from a requirement, or a Triton port | `flydsl-tile-programming` |
| Write | FlyDSL API, layout algebra, copy/MMA, LDS lookups | `flydsl-kernel-authoring` |
| Write | A new MFMA, WMMA, or copy atom in a backend dialect | `add-target-atom-op` |
| Write | Explain a Triton kernel's tiling and memory pattern | `kernel-walkthrough` |
| Write | HIP kernels on opus | `opus-kernel-best-practice`, `opus-module-build-optimization` |
| Optimize | Pick the lever for any MFMA kernel, close a gap to a reference | `cdna-kernel-opt` |
| Optimize | GEMM tiling, ping-pong, swizzle, pipelining, epilogue | `gemm-optimization` |
| Optimize | LDS bank conflicts, `lgkmcnt` stalls | `lds-optimization` |
| Optimize | Load latency exposed in a loop | `prefetch-data-load` |
| Optimize | Low L2 hit rate across blocks | `chiplet-xcd-remap` |
| Optimize | Compile hints, `-mllvm` flags, spills, occupancy | `llvm` |
| Optimize | Loop on one named kernel | `jdbba-autoresearch`, `jdbba-frontier-search`, `optimize-mla-reduce-flydsl`, `optimize-mla-reduce-traversal-flydsl` |
| Optimize | A generic kernel metric loop | **Kernel hillclimb** (`playbooks/kernel-hillclimb.md`) |
| Debug | NaN, inf, wrong output, crash in FlyDSL | `debug-flydsl-kernel` |
| Debug | Illegal address, silent corruption, bad `buffer_load` math | `oob-detection` |
| Debug | Which commit made it slow | `bisect-perf-regression` |
| Prove | Did VGPR, SGPR, spills, or LDS change. Compile-only, no GPU | `isa-resource-diff` |
| Prove | Capture an ATT or `rocprofv3` trace | `capture-kernel-trace` |
| Prove | Stall hotspots from a `rocprofv3` run or dispatch dir | `kernel-trace-analysis` |
| Prove | A decoded ATT folder, WaveScope annotations | `analyze-att-trace` |
| Test | An `op_tests/test_*.py` for aiter | `aiter-op-test` |
| Test | Tuned config CSVs under `aiter/configs` | `aiter-config-shape` |
| Ship | Style gate before commit or push | `format-code`, `check-python-style` (FlyDSL) |
| Ship | Run base and head on a locked GPU, emit a report | `validate-kernel-pr` |
| Ship | Advisory review of an aiter or FlyDSL PR | `review-pr` |
| Ship | FlyDSL stable-API compliance | `api-stability`, `release-api-check` |
| Ship | Clean up a kernel, keep numerics and speed | `kernel-code-cleanup`, `flydsl-kernel-code-cleanup`, `flydsl-internal-types-cleanup` |
| Env | Build FlyDSL, or the ROCm image with aiter and FlyDSL | `build-flydsl`, `build-rocm-image` |
| Env | Run on a GPU, in a container, on a remote host | [`verify-gpu-kernel`](../../verify-gpu-kernel/SKILL.md), [`env.md`](env.md) |

Order of checks for a perf change.

```
isa-resource-diff   (seconds, no GPU)   regress? ──► reject, no benchmark
        │ clean
        ▼
bench on a locked GPU   (benchmark-checklist, GPU kernels)
        │ plateau
        ▼
capture-kernel-trace ──► kernel-trace-analysis / analyze-att-trace
```

Rules.

- A skill that names a kernel (`jdbba-*`, `optimize-mla-*`) applies only to that kernel and arch. For any other kernel, use **Kernel hillclimb** and borrow the levers.
- `jdbba-*` targets `gfx950`. `optimize-mla-*` targets `gfx942`. Confirm the arch before you trust a number from either.
- Correctness gates every perf number (**principle-correctness-before-speed**).
