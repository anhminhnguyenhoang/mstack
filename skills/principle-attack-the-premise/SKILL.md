---
name: principle-attack-the-premise
description: "Apply when two or more fixes that share one premise have failed the same gate. Write the premise down and test it directly before you write another fix that assumes it."
disable-model-invocation: true
---

# Attack the premise

When two or more fixes that share one premise have failed the same gate, suspect the premise, not the fixes.

**Why:** Each failed fix is evidence against the belief it assumed. A third fix on the same premise spends effort where the evidence already says the cause is not.

**Pattern:**
- **Write the premise down.** The premise is the one sentence that every failed fix assumed.
- **Test the premise before the next fix.** Find an observation that would come out differently if the premise were false, and make it. Look at how the failures are distributed, not only at how large they are. For a GPU kernel, split them per wave, CU, XCD, shape, or dtype, from an ATT trace or counters (the `trace.capture` skill function, `../ateam-mode/references/skill-functions.md`), because a skew there shows a cause that the averages hide. Make the check rerunnable per [Build the lever](../principle-build-the-lever/SKILL.md).
- **Follow the evidence.** If it contradicts the premise, the cause is elsewhere. Look for what the failures have in common that the premise did not predict. If it confirms the premise, ask the next "why" per [Fix root causes](../principle-fix-root-causes/SKILL.md). The earlier fixes may have treated a consequence instead of the cause.
- **Remove the condition instead of compensating for it**, per [Subtract before you add](../principle-subtract-before-you-add/SKILL.md). If the evidence shows that one part always gets the worse outcome, change what assigns it that outcome. A mechanism that cleans up after it leaves the cause in place and adds work on every run.

**Stop:** Do not start the next fix before the premise is written down and tested.

This principle is distinct from [Redesign from first principles](../principle-redesign-from-first-principles/SKILL.md), which rebuilds a design around a new requirement. It questions a fact the current design assumes.
