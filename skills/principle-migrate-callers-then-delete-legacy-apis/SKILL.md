---
name: principle-migrate-callers-then-delete-legacy-apis
description: "Apply when introducing a new internal API, or running a planned rewrite, while old callers still exist. Converge on the end state. Migrate callers and delete the old API in the same wave instead of preserving compatibility layers."
disable-model-invocation: true
---

# Migrate callers then delete legacy APIs

When we decide a new API is the right design, migrate callers and remove the old API in the same refactor wave instead of preserving compatibility layers.

**Rule:**
- Do not keep legacy API paths only because internal callers still exist
- Inventory callers, migrate them, and delete the old API immediately
- Treat temporary adapters as exceptional and time-boxed, not default architecture
- Update tests to assert the new contract, and delete tests that only protect pre-refactor implementation details

**Converge on the end state.** Do not keep every step between here and the target fully working with throwaway compatibility code, because that code outlives the rewrite. Breakage between steps is fine when you plan it, keep it on your branch, and declare it in the plan. Keep the checks for the code you touch running while you migrate, and run the full correctness and perf checks when the wave ends. Each PR merged upstream still passes CI on its own.

**When this applies:**
- No external users depend on backward compatibility
- The project can absorb coordinated breaking changes
- The new API is part of a simplification or refactor initiative

An op that model code outside the repo calls, such as an aiter op that sglang or vLLM imports, has external users. Keep its signature, add the new path beside it, and remove the old one only after those callers move.

Keeping both old and new APIs creates dual-path complexity, slows cleanup, and lets the codebase only grow.
