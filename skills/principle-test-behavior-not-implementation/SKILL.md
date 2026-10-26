---
name: principle-test-behavior-not-implementation
description: "Apply when you write, change, or keep a test. Assert what the code's users can observe, so that the test fails when that behavior breaks and keeps passing when only the internals change."
disable-model-invocation: true
---

# Test behavior, not implementation

A test is a claim about what the code does for its users. A kernel's users are the model code or the library that calls the op. Behavior is what those users can observe through the op's interface: the output tensor, the in-place buffer it writes, the errors it raises, and the variant the dispatcher picks when dispatch is part of the contract. Implementation is what they cannot observe: tile sizes, LDS layout, the instruction schedule, private helpers, and intermediate buffers.

Judge each test against two imagined edits:

- **Break the behavior.** Make the kernel write a wrong value, skip part of the output, or write a tile twice. If the test still passes, it proves nothing. The usual causes are a tolerance looser than the dtype needs, an expected value computed by the kernel under test, a restated constant or config row that never runs the code that reads it, and an assertion on data that the test built itself.
- **Change the internals.** Keep every output the same and change the tiling, the schedule, or the helpers. If the test now fails, it is pinned to the implementation. It will need a rewrite on every lever and still catches no bug.

Keep a test that catches the first edit and survives the second. Rewrite or delete the rest. To write a test that does both, call the op the way the model calls it, at the model's real shapes, dtypes, layout, and output buffer. Compare the output with an independent reference, such as a plain torch implementation, never with another path through the same kernel. Take the tolerance from the dtype and the reduction length, not from what the current kernel happens to reach. For aiter, write the test through the `test.author` skill function (`../ateam-mode/references/skill-functions.md`).

The contract decides, not the shape of the assertion. When "each shape class reaches the tuned kernel" is the promise, an assertion on the dispatched variant is behavior. Pair it with a shape that must fall back, so that the test shows it can see the difference. When dispatch is not the contract, the variant is implementation. An exact error message pins wording that no caller reads. The error type that callers branch on is the contract. Check tile sizes, LDS layout, and the schedule with ISA or trace tools, not with unit tests.

A test can pin an invariant instead of an output, such as a shape that must exist in two tuned-config CSVs or a compile-time type check. The invariant is the behavior.
