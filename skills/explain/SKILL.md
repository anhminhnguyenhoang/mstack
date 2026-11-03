---
name: explain
description: "Explains a quoted line, term, or number, or a kernel, design, optimization, lever, idea, or concept, in plain words. Routes kernels to teach, designs to how and why, optimizations and levers to the lever doc, and ideas to the kb resource. Use for /explain or 'what do you mean by'."
disable-model-invocation: true
---

# Explain

Explain a quoted line, term, or number in plain words, and route each other target to its owning source.

## Route

| Target | Do this |
|---|---|
| A quoted line, term, or number from this chat or a draft | Follow the steps under Quoted text. |
| A GPU kernel or a kernel change | Run the [`teach`](../teach/SKILL.md) skill. |
| A design, a subsystem, or "how does X work" | Run the [`how`](../how/SKILL.md) skill. Add the [`why`](../why/SKILL.md) skill when the reasons are the point. |
| "Why was this built this way" | Run the [`why`](../why/SKILL.md) skill. |
| An optimization or a lever that the lever doc records | Read the lever's row in the lever doc, as the [lever doc](../ateam-mode/references/lever-doc.md) defines it. Outside a ticket, the doc sits in the work dir. Explain the premise that queued the lever, its screen result, and its root cause. Explain its numbers per the Numbers section of [`teach`](../teach/SKILL.md). |
| An idea or a concept | Read the `kb` resource when it is set, following the [resources](../ateam-mode/references/resources.md) reference. When it is not set, write `skipped kb: not set`, and explain the idea plainly with one diagram. |

## Quoted text

1. Find where the quoted text comes from: a file and line, or your own earlier message. Read that source again before you answer.
2. Say what the text means in plain words. Define each term the user does not use every day, such as an internal tag or a coined name.
3. Say why the text is there: the decision, the measurement, or the rule behind it. Label each reason as measured, inferred, or guess.
4. Say what the text changes for the user: an action, a decision, or nothing.
5. When the text sits in a draft that needed this explanation, offer a plainer line. Write it as a new draft version, per the revised-draft rule in the **ateam-mode** skill. Do not edit the posted text.
6. Use the voice of the [`/bro`](../bro/SKILL.md) skill: short sentences, plain words, no filler. Keep the answer under about 120 words unless the user asks for more. Answer several items as a numbered list, in the user's order.
