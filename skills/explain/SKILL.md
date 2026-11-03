---
name: explain
description: "Explain a quoted line, term, question, or number from this chat or a draft in plain words: what it means, why it is there, and what it changes for the user. Use for /explain or 'what do you mean by'."
disable-model-invocation: true
---

# Explain

1. Find where the quoted text comes from: a file and line, or your own earlier message. Read that source again before you answer.
2. Say what the text means in plain words. Define each term the user does not use every day, such as an internal tag or a coined name.
3. Say why the text is there: the decision, the measurement, or the rule behind it. Label each reason as measured, inferred, or guess.
4. Say what the text changes for the user: an action, a decision, or nothing.
5. When the text sits in a draft that needed this explanation, offer a plainer line. Write it as a new draft version, per the revised-draft rule in the **ateam-mode** skill. Do not edit the posted text.
6. Use the voice of the [`/bro`](../bro/SKILL.md) skill: short sentences, plain words, no filler. Keep the answer under about 120 words unless the user asks for more. Answer several items as a numbered list, in the user's order.
