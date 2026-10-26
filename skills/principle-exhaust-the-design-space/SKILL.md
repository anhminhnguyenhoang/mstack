---
name: principle-exhaust-the-design-space
description: "Apply when facing a novel kernel design or architectural decision with no precedent in the codebase. Build 2 or 3 competing prototypes and compare side by side before committing."
disable-model-invocation: true
---

# Exhaust the design space

It also applies to kernel choices that only a measurement can decide, such as a tiling, a pipeline depth, or a data layout. Build each candidate as a throwaway probe per the **Bound probe** playbook, and compare them on the same locked GPU.
