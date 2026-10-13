# Bugbot triage

Use this reference when the Babysit playbook (`../playbooks/babysit.md`) handles Bugbot or review-automation comments. The goal is not to ignore Bugbot by default. The goal is to stop treating every comment as a required code change.

## Decision rubric

Classify each Bugbot thread before acting:

- `fix`: The comment identifies a plausible correctness, numerics, memory-safety, security, privacy, data loss, auth, billing, migration, idempotency, race, or shipped-behavior issue. Fix it in the lowest owning PR, then reply with the commit SHA and resolve the thread.
- `dismiss`: The comment matches a documented low-risk noisy pattern, and the current code/context proves the concern does not need a code change. Reply with a short reason and resolve the thread.
- `ask`: The comment is novel, high-severity, security/privacy/data-related, or ambiguous. Ask the user instead of guessing.

When in doubt, ask. Skipping a noisy code-quality comment is cheap; skipping a real data or security bug is not.

## Learned pattern format

Add future patterns in this shape:

```markdown
### <short pattern name>

- Confidence: candidate | recurring | strong
- Skip when: <conditions that must be true>
- Do not skip when: <risk boundaries>
- Example signal: <phrases or code context that identify the pattern>
- Source: <PR/comment URL or short historical note>
```

Use `candidate` for one or two examples. Use `recurring` after multiple real dismissals. Use `strong` only when the pattern is narrow, repeatedly verified, and low-risk.

## Recurring skip candidates

### Upstack or stack-local usage Bugbot cannot see

- Confidence: candidate
- Skip when: Bugbot flags an export, helper, or file as unused, and the active PR tool's PR list and diffs, upper-stack diffs, or PR context show it is used by a later PR in the stack.
- Do not skip when: The current PR is not part of a stack, the symbol is public API, or the supposed upstack use cannot be verified.
- Example signal: "Exported helper is never used" with a human reply like "used upstack".

### Temporary duplication during parallel implementation

- Confidence: candidate
- Skip when: The PR intentionally duplicates a small amount of code to keep a new path parallel to an old path that is being deleted, replaced, or proven out.
- Do not skip when: The duplicated code changes security, billing, data access, API behavior, or a long-lived shared abstraction would clearly reduce risk.
- Example signal: "Significant duplication" or "duplicated validation logic" where the owner explains the old path will be deleted or the duplicate logic is intentionally local.

### Existing framework or component invariant covers the warning

- Confidence: candidate
- Skip when: The concern is already guaranteed by a shared helper, framework contract, type invariant, or single source of truth visible in the current diff or nearby code.
- Do not skip when: The invariant is assumed but not enforced, depends on timing, or crosses async/state boundaries where values can diverge.
- Example signal: Comments about a missing bounds check when a shared helper already clamps the index, or nullable values where the local checked value and passed value share the same source.

### Owner-declared follow-up or deferred cleanup

- Confidence: candidate
- Skip when: The PR owner explicitly says the issue is a known follow-up, the behavior is not made worse by the current PR, and the comment is not about a high-risk area.
- Do not skip when: The agent is acting without owner input, the issue is medium/high severity product behavior, or deferring would merge a new regression.
- Example signal: "I'll worry about that later" or "we'll delete this eventually".

### Self-withdrawn or explicit false-positive rule comments

- Confidence: recurring
- Skip when: The comment body or a later Bugbot reply explicitly says the finding is withdrawn, compliant, or a false positive, and the agent can verify the relevant rule locally.
- Do not skip when: The only evidence is a human saying "false positive" on a high-risk issue without explanation.
- Example signal: A file-naming rule comment whose body says the file is already compliant.

## GPU kernel findings

Default to `fix`. Bugbot findings in these classes are usually real, and a wrong kernel can pass a lenient test. Each entry names what settles the finding. Run that check on the PR tip before you classify. Run the check through the ports in [`ports.md`](./ports.md).

### Numerics drift

- Confidence: candidate
- Real by default when: The diff changes the accumulation order (split-k, a new reduction tree, an atomic add), narrows a dtype before the accumulate or the store, enables fast-math or a lower-precision intrinsic, or changes how NaN or inf flows (a dropped max-subtract, a changed mask value).
- Settled by: The op test's `allclose` gate at the dtype's tolerance, on shapes that hit the changed path, against an fp32 reference. Add the NaN and inf count on adversarial input: large magnitudes and fully masked rows. Run it through the `bench.run` port.
- Dismiss only when: The order or dtype change is the stated goal and the gate passes on the same run with the tolerance unchanged.
- Example signal: "accumulates in bf16", "reduction order differs from the reference", "`-inf` row yields NaN".

### Occupancy cliff

- Confidence: candidate
- Real by default when: The change raises VGPR, AGPR, or LDS use, or adds a spill or scratch, and the new total crosses a waves-per-SIMD step.
- Settled by: The before and after resource table from the `isa.diff` port. It is compile-only and needs no GPU. Benchmark only when a step is crossed.
- Dismiss only when: Both sides sit in the same waves-per-SIMD bucket with no new spill, or the kernel trades occupancy on purpose and a benchmark shows the win.
- Example signal: "increases register pressure", "larger tile may reduce occupancy", "LDS allocation grows".

### Out-of-bounds or masked-tail access

- Confidence: candidate
- Real by default when: A load or store address depends on a tile index with no mask, or the mask or buffer limit ignores a partial tile (M, N, or K not a multiple of the tile), a varlen batch, or an empty group (zero tokens or zero rows).
- Settled by: A test at the failing shape: a tail of 1, M below one tile, an empty group, and a varlen batch with a zero-length sequence. Run it with the `kernel.debug` port. An illegal address or a wrong value in the tail confirms it.
- Dismiss only when: The shape is excluded by a check before launch that the diff shows, and a test covers the check.
- Example signal: "reads past the end when M is not divisible", "no guard for empty expert", "mask uses the padded length".

### Race or missing barrier on LDS

- Confidence: candidate
- Real by default when: One wave reads LDS that another wave wrote with no barrier or wait between them, or a buffer is rewritten before every wave finished reading it (a double-buffer swap, a reused scratch region).
- Settled by: Listing each LDS write and each read of the same region on every path, and naming the barrier or wait between each pair. A stress run of many iterations against the reference shows a mismatch for a real race.
- Dismiss only when: The code shows that each wave reads only what it wrote, so no cross-wave order is needed.
- Example signal: "missing `s_barrier` before reading `smem`", "overwrites the buffer while other waves read it".

### Arch-gated path

- Confidence: candidate
- Real by default when: The code uses an instruction, an MFMA shape, an fp8 format, or an LDS size that exists on one arch (`gfx942` or `gfx950`) but runs on the other, or a gate tests the wrong arch string.
- Settled by: Reading the gate against the arch string, then compiling for both targets. The `isa.diff` port compiles with `--arch`. A run on each arch settles a runtime difference.
- Dismiss only when: The dispatcher refuses the other arch before this path, and a test covers the refusal.
- Example signal: "instruction not available on gfx942", "fp8 format differs between archs", "assumes the larger LDS".

### Dispatch threshold routes a shape to the wrong kernel

- Confidence: candidate
- Real by default when: A boundary uses `<` where `<=` is meant, a threshold tuned on one arch or dtype applies to another, a tuned-config lookup miss falls to a slow default, or a config row duplicates a shape.
- Settled by: A sweep at the boundary (threshold minus 1, the threshold, and threshold plus 1) that logs which kernel ran and times both kernels there. Use the `bench.run` port. Duplicate shape rows are the `config.tune` port.
- Dismiss only when: The sweep shows the same kernel is faster or equal on both sides of the boundary.
- Example signal: "off-by-one at the threshold", "falls through to the default kernel", "threshold copied from another arch".

- Source: kernel review convention. No dismissal history confirms or refutes these yet.

## Ask by default

Do not auto-skip these categories, even if a previous PR dismissed something similar:

- Security, privacy, auth, billing, data retention, training-data, and permission-boundary findings.
- Out-of-bounds, race, and numerics findings in a kernel, unless the evidence in the GPU section settles them.
- High-severity findings.
- Migration, schema, idempotency, concurrency, and cross-system behavior findings.
- Comments where the suggested fix is small and clearly reduces risk without changing product intent.

Historical data showed humans sometimes dismiss security/data-flow comments. Treat those as owner judgment calls, not team-wide skip rules.

## Candidate learnings from recent babysits

Append new candidate learnings here during or after babysitting when they look team-useful but not yet mature. Prefer promoting recurring candidates into the section above once several PRs confirm the pattern.

### Contract-test drift claims are cheap to verify, so run the test first

- Confidence: candidate
- Skip when: Never skip the verification itself; it costs one command. When a PR
  ships a contract test that pins protocol or documentation prose (regexes over
  a SKILL.md, snapshot of doc wording), and Bugbot claims "the test no longer
  matches the doc" (or vice versa), run that test on the PR tip before
  classifying. A red run confirms the claim empirically; a green run is a
  concrete disproof for the dismissal reply.
- Do not skip when: n/a. This is a verification shortcut, not a dismissal
  pattern. Repeat-pass lean-dismiss heuristics would misfire here:
  prose-pinning tests drift because earlier fix rounds edit the prose.
- Example signal: "Contract test omits the pre-fix wait" on a PR whose earlier
  fix commits reworded the pinned passage; the test run on the tip failed on
  exactly the cited assertion.
- Source: one prose-pinning PR with eight Bugbot passes; the claim was real on
  pass 7 despite every earlier pass being fixed-and-resolved.

### Stale security-review finding already fixed later in the same PR

- Confidence: candidate
- Skip when: An agentic security review (or similar) claims a missing authz/validation call, and the current PR tip clearly includes that exact gate (with tests), typically added in a later hardening commit after the review ran.
- Do not skip when: The cited helper is a no-op for the principal under discussion, the check runs after the side effect it guards, or coverage for the claimed principal is missing.
- Example signal: A HIGH "missing authorization check" finding while the exact guard is already called before the side effect on the tip.
- Source: one endpoint PR whose hardening commit postdated the review run.

### Widening a deliberately narrow error condition would mask the real error

- Confidence: candidate
- Skip when: The finding asks to broaden a narrow error condition (a specific
  `errno`, error code, or status class) into a catch-all, and that narrowness
  encodes a real distinction. The canonical shape is a dependency fallback
  gated on `ENOENT`: "binary is not installed" is a different situation from
  "the command ran and failed". Retrying on any non-zero exit would re-run a
  legitimate failure (not found, expired auth, network) against the fallback
  and then report the fallback's error, hiding the true one.
- Do not skip when: The narrow condition misses a case in the same category
  (another "binary unusable" errno such as `EACCES`, another transport-level
  failure), the unhandled path loses data or leaves partial state, or the retry
  is idempotent and the original error is still reported.
- Example signal: "only retries when X fails with ENOENT … never tries the
  fallback even when a working Y exists", pointing at code whose fallback
  exists for a missing dependency rather than a failed operation.
- Source: one CLI-rename PR whose fallback existed for a missing binary rather
  than a failed command.
