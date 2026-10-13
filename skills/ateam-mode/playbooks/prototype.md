### Prototype

**You own the design decision, not the code. The prototype is a throwaway instrument. The real build follows Feature.**

The one playbook where the "smallest change" rule of **principle-subtract-before-you-add** and the verification bar invert. Speed over polish, code quality does not matter, no planning. The rigor is in picking the right design cheaply. Propose variations the user didn't ask for, throw an approach away and try another.

1. Scope the decision the prototype exists to make: which tile shape, pipeline, or data flow for a kernel, which layout or interaction for an explainer page, or for an empirical fork which behavior, timing, or approach. No decision means no prototype. Route to Feature.
2. Gather references when the design space is open. Search for prior art (reference kernels, papers, and the `kb` resource when configured), summarize the candidate designs in one table, and let the user pick directions before building. Skip when the direction is set.
3. Build throwaway in an isolated scratch dir, separate from production source. For a kernel decision, the prototype is a throwaway kernel or probe (see **Bound probe**, `playbooks/bound-probe.md`). For a behavioral or timing decision, the smallest script that exercises the question. HTML/CSS/JS is for explainer pages only, where interactive HTML works best: the lightest stack that renders the idea, CDN deps. No production framework, no tests, no abstractions.
4. When comparing alternatives, build them behind one switch (an env flag or a constexpr knob, or buttons on an explainer page), each variant labeled. This is the **exhaust-the-design-space** principle skill made cheap.
5. Verify on the matching surface. For a kernel decision, run the probe on a locked GPU (the `bench.run` port) and read the number. For an explainer page, screenshot each variant and drive the interaction. For a behavioral or timing decision, observe the thing you are deciding by logging the timing or printing the output. The observation is the test here, not an assertion.
6. Present alternatives, tradeoffs, and a recommendation. The output is the decision plus the throwaway artifact, not shippable code. Hand the chosen direction to **Feature** (or `architect` for the shape) for the real build.

**Reply:** the variants explored, the evidence (the probe's output or timing for a kernel or behavioral decision, screenshots for an explainer page), tradeoffs, your recommendation, and the scratch path. Say plainly that the prototype is throwaway.
