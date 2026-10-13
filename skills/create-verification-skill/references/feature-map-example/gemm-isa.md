# GEMM ISA resources

GEMM ISA resources lets a kernel author check, without a GPU, that a change did not raise register use, add spills or scratch, or grow LDS in the GEMM kernels.

## Sub-features

- `isa-base` captures the resource table of the base revision.
- `isa-head` captures the resource table of the head revision with the same command.
- `isa-diff` shows the change of VGPR, SGPR, spills, scratch, and LDS for each kernel.
- `isa-gate` rejects a head that adds spills or scratch.

## How to get to it (user POV)

- Run the `isa.diff` skill function with the GEMM test command and the target arch.
- Run it before any benchmark, as the first check of a perf change.

## Driving it with isa.diff

Preconditions:

- The container is up, and the library is at the revision under test.
- Use the same test command and the same arch for the base and the head.
- The runtime cache is off for both captures.

- **Base.** Check out the base revision. Run the GEMM test command into a fresh dump directory. The directory holds one resource record for each kernel.
- **Head.** Check out the head revision. Run the identical command into a second fresh directory.
- **Diff.** Run the diff of the two directories. The output lists each kernel with its VGPR, SGPR, spill, scratch, and LDS values on both sides.
- **Gate.** Read the spill and scratch columns. Both are `0` on the head, or they equal the base. A rise rejects the change before any benchmark.
- **Proof.** Save the diff table in the work dir. Record both SHAs, the command, and the arch.

## Gotchas

- A warm runtime cache returns the old binary, and the diff shows no change. Turn the cache off.
- A different arch for the base and the head compares two different kernels.
- A clean diff means the resources are unchanged. It does not mean the time is unchanged.
- A kernel that is absent on one side did not compile, or was renamed. Report it. Do not skip it.
- A compile-only run proves resources only. It does not prove correctness. Run the correctness file next.
