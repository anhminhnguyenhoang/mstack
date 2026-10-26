# Review Rubric

Review through whichever lenses are relevant. Not every lens applies to every change.

## Correctness

Does the code do what the intent says it should?

- Edge cases: zero-size and tail shapes, non-contiguous strides, NaN and inf inputs, boundary values, concurrent access
- Error handling: are errors caught, propagated, or silently swallowed?
- Off-by-one, type coercion, integer overflow, string encoding
- State management: race conditions, stale closures, dangling references
- Do both the happy path and the sad path work?
- Idempotency: what happens if this operation runs twice, or if a previous run crashed halfway? If the answer is "it depends on what state was left behind," a reconciliation step is missing.
- Concurrency: if multiple actors can touch the same mutable state (files, branches, shared data), is access serialized structurally (locks, sequential phases, exclusive ownership), or by conventions that won't hold?

When you find a potential bug, trace the execution path. Don't just flag "this could read out of bounds". Show the call chain and the shape that make it do so.

## Root causes vs. symptoms

Is the code fixing the cause or hiding a symptom?

Answering this often requires looking beyond the changed files. Read the surrounding code (callers, callees, type definitions, sibling modules) and understand the architecture the change belongs to. Use the tools available to you (Read, Grep, Glob) to follow the call chain and read the types. Understand why the code exists before judging whether the change addresses the right layer.

- Guard clauses that mask a deeper invariant violation
- Retry logic that hides a broken contract
- Type casts that silence a modeling error
- A workaround: why is it needed? What would a proper fix look like?
- A fix in module A that should be a fix in module B's contract
- Instructions where structure would be better: if the fix is a comment saying "don't do X" or a convention someone has to remember, ask whether it could instead be a type constraint, a lint rule, or a runtime check that makes the wrong thing impossible

## Structural integrity

Does the code fit well into the system it's part of?

- Input checks: are shapes, strides, dtypes, and arch preconditions checked once at the op entry point, or scattered through the kernel and its launcher?
- Abstraction level: is the code mixing high-level orchestration with low-level detail?
- Coupling: does this change introduce dependencies that will make future changes harder?
- Data model fit: do the data structures match the actual access patterns?
- Bolted-on vs. integrated: if the new requirement had been known from the start, would the code look like this, or does the change feel patched onto the existing design?
- Legacy dual-paths: does the change introduce a new API while keeping the old one alive? If there are no external consumers, migrate callers and delete the old path in the same wave. Don't leave compatibility layers that will become permanent.

Don't penalize simple code for lacking abstraction. Premature abstraction is worse than duplication.

## Verification

Can you tell that this code works from reading it?

- Are there tests? Do they test behavior or implementation details?
- Are there assertions/invariants that would catch regressions?
- If this is a bug fix: is there a test for the bug?
- If this touches an integration boundary: is the full path tested?
- Check the real thing, not a proxy. If the code checks liveness via file mtime or cached state instead of reading the actual value, that's a verification gap.
- For delegated or async work: does the code verify actual output artifacts, or does it trust self-reports and summaries?

## Complexity budget

Is the complexity justified by what the code accomplishes?

- Code that could be simpler without losing correctness or clarity
- Abstractions that serve only one call site
- Configuration or parameterization for cases that don't exist yet
- Dead code, unused imports, vestigial parameters
- Over-engineering: "just in case" code paths with no current callers
- Obsolete compatibility paths kept alive for transitional stability that's no longer needed. If the migration is done, delete the temporary code
- Does the user experience justify the complexity? Every feature, control, and option should earn its place. Half-finished features are worse than missing ones.

Simpler is better unless simpler is wrong.

## GPU kernels

When the diff touches a kernel or its dispatch, check each class and name the check that settles it. The lead pastes the full entries with their checks.

- Numerics drift: accumulation order, a narrowed dtype, fast-math, NaN or inf flow
- Occupancy cliff: VGPR, AGPR, or LDS growth, or a new spill, that crosses a waves-per-SIMD step
- Out-of-bounds or masked-tail access: partial tiles, varlen batches, empty groups
- Race or missing barrier on LDS
- Arch-gated path: an instruction, MFMA shape, fp8 format, or LDS size that differs between `gfx942` and `gfx950`
- Dispatch threshold: an off-by-one boundary, a threshold tuned on another arch or dtype, a tuned-config miss

## Security

For each security finding, trace the input path through the code and show it.

- Input flowing to dangerous sinks (shell, eval, `pickle` or `torch.load` of an untrusted file, a path built from input) without checks
- GPU memory read or written out of bounds because a shape, stride, or offset from the caller is not checked
- Secrets in code, logs, or error messages
- TOCTOU (time-of-check-time-of-use) in security-critical paths
