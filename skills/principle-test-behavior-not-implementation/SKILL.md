---
name: principle-test-behavior-not-implementation
description: "Apply when you write, change, or keep a test. Assert what the code's users can observe, so that the test fails when that behavior breaks and keeps passing when only the internals change."
disable-model-invocation: true
---

# Test behavior, not implementation

A test is a claim about what users of the code can observe through its interface: return values, errors, state they can read back, and effects on outside systems. For a kernel, the users are the model code or the library that calls the op. They observe the output tensor, the buffer it writes, the errors it raises, and the variant the dispatcher picks when dispatch is the contract. Private helpers, internal call order, tile sizes, LDS layout, the instruction schedule, and intermediate buffers are implementation.

Judge each test against two imagined edits:

- **Break the behavior** (a wrong value, a skipped part of the output, a tile written twice). If the test still passes, it proves nothing. The usual causes are a tolerance looser than the dtype needs, an expected value computed by the kernel under test, and an assertion on data the test built itself.
- **Change the internals** (tiling, schedule, helpers) and keep every output the same. If the test fails, it is pinned to the implementation.

Keep a test that catches the first edit and survives the second. Rewrite or delete the rest. To write one, call the op the way the model calls it, at its real shapes, dtypes, layout, and output buffer, with a concrete input. Derive the expected value from the requirement, or from an independent reference such as plain torch, never from another path through the same kernel. Take the tolerance from the dtype and the reduction length. For aiter, write the test through the `test.author` skill function (`../ateam-mode/references/skill-functions.md`).

What an external service receives is behavior. A call to an internal helper is not. Pair "this never happens" with a case where it does happen. Assert the error type that callers branch on, not the message.

Dispatch counts as behavior only when it is the contract. When each shape class must reach the tuned kernel, assert the dispatched variant, and pair it with a shape that must fall back. Check tile sizes, LDS layout, and the schedule with ISA or trace tools, not unit tests.

A test can also pin an invariant, such as a shape that must exist in two tuned-config CSVs or a compile-time type check.
