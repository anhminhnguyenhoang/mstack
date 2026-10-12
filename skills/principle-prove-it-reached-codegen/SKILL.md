---
name: principle-prove-it-reached-codegen
description: "Apply when you change a compile hint, flag, attribute, or kernel structure and want credit for a result. A knob is real only if the ISA or IR changed."
disable-model-invocation: true
---

# Prove It Reached Codegen

- **A knob did something only if the generated code changed.** After a compile hint, an `-mllvm` flag, a function attribute, a tile or swizzle change, or a scheduling edit, diff the LLVM IR or the final ISA against the build without it. Count what the lever claims to move: instructions per iteration, `s_waitcnt` depth, VGPR, SGPR, spills, scratch, LDS bytes.
- **No diff means no effect.** The compiler may have dropped the hint, a cache may have served the old build, or the option may never have reached the backend. Treat a timing change with an identical ISA as noise, and treat a no-op as a revert.
- **Build fresh on both sides.** Clear the JIT or compile cache before you capture each side. A stale cache makes the diff and the timing describe different code.
- **Check the diff before the benchmark.** A resource diff needs no GPU and takes seconds. Run it first, and reject a regression before you spend a benchmark on it.

You skipped this when a result credits a flag or a hint, and no ISA or IR comparison backs the claim.

Use **isa-resource-diff** for register, spill, scratch, and LDS deltas, and **llvm** to read the IR and ISA and to confirm an option reached the backend. Distinct from [Prove It Works](../principle-prove-it-works/SKILL.md), which checks that an output is real. This one checks that a code change is real.
