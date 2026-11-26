---
name: principle-fix-root-causes
description: "Apply when debugging. Trace each symptom back to the first place the system went wrong and fix it there. A guard is a fix only when the state it handles is legitimate."
disable-model-invocation: true
---

# Fix root causes

Fix the fault, not the place where it surfaced. The root cause is the first place the system did something it should not do, or failed to handle a state it should handle.

- Reproduce first. Ask "why" until the answer is a wrong decision in the code. When stuck, instrument and read the actual state.
- Ask whether the state that triggered the symptom is legitimate. If it is, handle it where the code broke. If it should never exist, a check there hides the bug, so find what produced it. Guards, retries, swallowed errors, clamped values, and discarded state are the usual ways to hide a bug.
- Fix the pattern, not the instance. Find every place with the same fault.
- When something fails only after a restart, a rebuild, or on one machine, suspect persisted state first: a stale JIT or compile cache (FlyDSL, Triton, aiter), a tuned-config CSV, a lock file, or an env var set in one container.
- If the deciding fact took a deep dig, propose the cheap, always-on signal that would have shown it at first look. For a GPU kernel, the signal can be the dispatched kernel's name, so a fallback cannot pass for the new kernel. It can also be the ISA resource table on every build (the `isa.diff` skill function, `../ateam-mode/references/skill-functions.md`), or a reference comparison on every bench run.
