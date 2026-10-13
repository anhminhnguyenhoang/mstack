---
name: principle-subtract-before-you-add
description: "Apply when sequencing an addition, refactor, or rewrite, when tempted to add an abstraction, layer, or flag, or when sizing a diff. Remove dead code, redundant validators, and stub references first, make the smallest change, then build on the simpler base."
disable-model-invocation: true
---

# Subtract before you add

When evolving a system, remove complexity first, then build. Default to subtraction.

Simplify on every change. Leave the design slightly simpler and more capable behind the same or smaller interface than you found it.

- Sequence removal before construction
- Cut before you polish (get to the minimum before investing in quality)
- Design for observed usage, not speculative edge cases
- No speculative validators, parsers, or guards beyond what the spec demands
- Simplify prompts (remove redundant instructions, excessive templates)
- When a reference has no novel content, delete it rather than leaving a stub

## Smallest change

- **Minimize the diff.** Make the smallest change that solves the problem. Fewer lines beat "elegant" boilerplate.
- **Consolidate decisions.** Do not repeat the same choice in several places. Put it behind one source of truth and pass the result as a simple flag.
- **Bias to deletion.** Before you add an abstraction, a layer, or signal threading, ask whether deleting something solves it.
