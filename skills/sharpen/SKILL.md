---
name: sharpen
description: "Make a task deeper, not bigger, then rewrite the prompt. Use for /sharpen."
disable-model-invocation: true
---

I want a deeper version of this task, not a bigger one. Before rewriting it, do four things:

1. Say what a top professional in this field would do here that I'm not asking for.
2. Name the rawest material they would start from instead of what someone has already summarized for me.
3. Name the specific methods and tools they would use.
4. Say what, other than you or me, would show the result is right.

For GPU kernel work, the rawest material is usually the ISA, an ATT trace, or hardware counters, not a summary of them. The outside check is usually an independent reference output and a percent of peak with the peak's source.

Then rewrite my prompt to ask for exactly that.

Leave choices that are mine to make open instead of deciding them.
