# GEMM perf

GEMM perf lets a kernel author measure a GEMM kernel against a reference on one locked GPU with a frozen harness, and keep the result as a JSON artifact that a reviewer can rerun.

## Sub-features

- `perf-lock` runs on one idle GPU under one lock.
- `perf-harness` runs the frozen harness and prints one row for each shape.
- `perf-ref` measures the reference side in the same run.
- `perf-peak` states each result as a percent of the arch peak, with the source of the peak.
- `perf-artifact` writes a JSON file from the run.
- `perf-compare` compares the base and the head of a change.

## How to get to it (user POV)

- Run the frozen bench harness through the `bench.run` port.
- Run the op test and read its perf table, through the `bench.run` port.
- Compare two revisions through the `pr.validate` port.

## Driving it with bench.run

Preconditions:

- The correctness map passed on the same shapes, at the same SHA.
- The harness file is unchanged since the baseline. Record its hash before the run.
- The `bench.run` doctor shows one idle GPU, and the lock is free.
- The library path and container come from the `repos` resource.

- **Doctor and lock.** Run the `bench.run` doctor, pick the GPU, and take the lock. The run uses one HIP index, and the artifact records it.
- **Harness run.** Run `python3 <harness>` inside the container, with the harness path from the repo. It prints one row for each shape and each side. Exit code `0`.
- **Reference side.** Read the rows of the reference side. Each shape has a reference row from the same process, run in the same interleaved loop as the kernel row.
- **Repeat.** Run the harness 7 times. Report the median, the run count, and the range for each shape, for example `p50 41 us, median of 7 runs, range 40 to 43 us`.
- **Percent of peak.** Compute TFLOPS as `2*M*N*K` over the median time. State it as a percent of the MFMA peak for the arch and dtype, and cite where the peak comes from. Follow **principle-respect-the-roofline**.
- **Explain the number.** For any speedup or regression, name what limits it and rule out a measurement artifact. Follow **principle-explain-the-number**.
- **Artifact.** Read the JSON that `bench.run` wrote. It holds the arch, the GPU index, the SHAs, the exact command, a `perf` row for each shape and each `side` with `us_median`, `runs`, `min_us`, `max_us`, and `regime`, and the path to the saved stdout.
- **Revision compare.** Run the `pr.validate` port for the base and the head. Do not compare two separate hand runs.

## Gotchas

- A busy GPU gives a meaningless number. With no idle GPU, report `NO_GPU` and stop. Do not benchmark.
- A JSON file typed by hand is not evidence. It must come from the run.
- Changing the harness during a hillclimb breaks the comparison. Freeze it and record its hash.
- Cold-L2, warm, and `hipGraph` runs differ. State the regime on every row. Follow **benchmark-checklist**.
- The first iterations include compile and warmup. Exclude them, and say how many you dropped.
- A perf row without a passing correctness row on the same run is not a result.
- A faster result on a different arch or container is not a speedup. Check both in the artifact.
- Copy numbers from the saved stdout. Never copy them from memory.
