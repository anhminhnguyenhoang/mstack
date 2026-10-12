# GEMM correctness

GEMM correctness lets a kernel author prove that a GEMM kernel matches an fp32 reference within a stated tolerance, on aligned shapes and on the edge cases that break tiled kernels.

## Sub-features

- `corr-aligned` passes the gate on shapes that are multiples of the tile.
- `corr-small-m` passes the gate when M is 1 or below one tile.
- `corr-tail` passes the gate when M, N, or K leaves a partial tile.
- `corr-dtypes` passes the gate for each supported dtype at that dtype's tolerance.
- `corr-nan` reports a NaN count of zero on finite input.
- `corr-control` fails on purpose when the tolerance is zero.

## How to get to it (user POV)

- Run `python3 op_tests/test_gemm.py` in the container, from the library root.
- Run `python3 -m pytest tests/kernels/test_gemm.py -q` in the container, when the library has a pytest target.
- Ask for a new test through the `test.author` port when none exists for the op.

## Driving it with bench.run

Preconditions:

- The container is up, and the library is at the revision under test.
- The `bench.run` doctor reports the expected arch, an idle GPU, and the repo SHA.
- `op_tests/test_gemm.py` exists. If it does not, write it through the `test.author` port first. It needs a torch reference, an `allclose` gate, and a final table.
- No other run holds the GPU lock.

- **Doctor.** Run the `bench.run` doctor. The output shows the arch, one idle GPU, and a clean repo at the expected SHA.
- **Aligned shapes.** Run `python3 op_tests/test_gemm.py -d bf16 -m 4096 -n 4096 -k 4096`. Exit code `0`. The table row for the shape reads pass, and the max error is below the printed tolerance.
- **Small M.** Run `python3 op_tests/test_gemm.py -d bf16 -m 1 -n 4096 -k 4096`. Exit code `0`. The row reads pass.
- **Partial tiles.** Run `python3 op_tests/test_gemm.py -d bf16 -m 129 -n 4100 -k 4104`. Exit code `0`. The row reads pass, and the tail columns match the reference.
- **Second dtype.** Run `python3 op_tests/test_gemm.py -d fp16 -m 4096 -n 4096 -k 4096`. Exit code `0`. The tolerance in the table is the fp16 tolerance.
- **NaN count.** Read the summary table of any run above. The NaN count is `0` for the kernel output.
- **Negative control.** Run the aligned-shape command with the test's own tolerance flags set to zero. At least one row fails. A gate that still passes tests nothing.
- **Proof.** Read the artifact that `bench.run` wrote. `correctness.passed` is `true`, `rtol` and `atol` match the table, `nan_count` is `0`, and `shapes_checked` equals the number of shapes run.

## Gotchas

- The reference runs in fp32. A reference in the kernel's own dtype hides rounding error that belongs to the kernel.
- A tolerance loose enough to pass every shape is a defect. Record `rtol` and `atol` in the artifact and compare them with the dtype's known tolerance.
- `allclose` can pass when both sides are NaN, depending on its flags. Count NaN separately.
- The first run compiles the kernel and is slow. Give the run its own JIT cache directory, and do not read perf from it.
- A shape with a tuned config may run a different kernel than an untuned shape. Log which path ran. Duplicate shape rows are the `config.tune` port.
- A partial-tile shape that the kernel refuses is not a pass. The test must show a refusal or a correct result.
- A pass on the wrong arch proves nothing for the arch you ship. Check the arch in the artifact.
