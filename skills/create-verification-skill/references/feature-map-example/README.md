# Kernel library verification map

This directory is the maintained source for verifying the user-facing behavior of a GPU kernel library. Read the index before you run anything, then use the matching feature file as the recipe.

The example assumes a library with an op test, `op_tests/test_gemm.py`, that takes `-d`, `-m`, `-n`, and `-k`. A real map names the flags of the real test.

## Baseline preconditions

- Resolve the library path, the container, and the path in the container from the `repos` resource. Never write them into the map.
- Run every command inside the container. The host has no torch.
- Run the `bench.run` doctor first. Require the expected arch, an idle GPU, and the repo SHA.
- Hold one lock on one GPU for each run, and give the run its own JIT cache directory.
- Check the arch from inside the container. A number from the wrong arch is not a number.
- Never run on a GPU that this run did not lock.

## Driving conventions

- Start every recipe from a clean checkout of the revision under test. Record its SHA.
- Treat every command as literal. Keep flags and shapes unchanged.
- Run correctness before perf. A perf row next to a failed or unchecked correctness row is not a result.
- Write a missing op test through the `test.author` skill function. Do not hand-roll its table.
- Compare two revisions through the `pr.validate` skill function. Do not rerun by hand and compare.
- Clear the JIT cache for a cold-compile run. State the regime of every perf row.
- Remove the run's scratch files and JIT directory after the run. Do not remove proof artifacts.

## Proof and skip reporting

- Capture the command, the full stdout, and the exit code.
- Proof of correctness includes the tolerance, the NaN count, and the number of shapes checked.
- Proof of perf includes the median, the run count, the range, the regime, and the percent of peak.
- Every number comes from a run. Never type a result by hand.
- A mutation proof pairs the result with a negative control that must fail.
- Record the feature ID and the entry point used with every artifact.
- Report an unreachable path with the attempted command and the unmet precondition. A busy GPU, a missing container, or an unreadable output is `INCONCLUSIVE`.
- Do not report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with <harness>` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of the map. Name only user paths, stable handles, required state, commands, and observable proof.

## Features

- [GEMM correctness](./gemm-correctness.md) covers the `allclose` gate over aligned shapes, small M, partial tiles, dtypes, and NaN handling, with a negative control.
- [GEMM perf](./gemm-perf.md) covers one locked GPU, the frozen harness, the JSON artifact, the reference side, and the base-to-head comparison.
- [GEMM ISA resources](./gemm-isa.md) covers the compile-only resource diff of VGPR, SGPR, spills, scratch, and LDS, with a gate on spills.
