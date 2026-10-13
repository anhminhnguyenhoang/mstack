---
name: teach
description: "Explain a GPU kernel or a kernel change so a person understands it: data flow from global memory to LDS to registers to MFMA to epilogue, tiling and wave mapping, pipeline waits, why the design is this way, and what the numbers mean. Runs the `how` and `why` skills. Use for 'teach me this kernel', 'explain this FlyDSL or aiter change', 'walk me through the tiling', 'why is this tile size or pipeline used'."
disable-model-invocation: true
---

# Teach

You explain what a kernel is, how it works, and why it is built that way. The goal is that the person understands it. You change nothing.

```
orient ──► how (data flow, mapping, waits) ──┐
       └─► why (design reasons)  ────────────┴─► diagrams ──► numbers ──► reply
```

## Steps

1. Pick the few things the reader must understand. Read their goal from the conversation: about to change it, reviewing it, debugging it, or new to it. Skip what they know.
2. Orient. Read the kernel source, the tile constants, the dtype, and the arch (`gfx942` or `gfx950`). For an API fact, read the reference of the `kernel.write` port. Do not recall API facts from memory.
3. Run `how` for the data flow and `why` for the design reasons. Run them in parallel. Narrow `why` in the ask, for example the tile size, the stage count, or the swizzle. Widen it only when the reasons are the point. Keep its confidence words. A hedge is a finding.
4. Draw the data flow as a build-up series. Draw one part per diagram. See Diagrams.
5. Explain the numbers. See Numbers.
6. When the structure is rich, write the HTML page. See HTML page.
7. Reply per Reply.

## Diagrams

Draw each diagram again with one more part. The reader watches the kernel assemble.

```
1  HBM ──► LDS
2  HBM ──► LDS ──► VGPR
3  HBM ──► LDS ──► VGPR ──► MFMA ──► AGPR or VGPR (accumulator)
4  ... ──► MFMA ──► epilogue ──► HBM
```

Cover these in order, as far as the question needs:

- **Data flow.** Global to LDS to registers to MFMA to epilogue. Mark each hop with its size per iteration and its instruction family.
- **Tiling.** The block tile `BM x BN x BK`, the wave tile, and the MFMA atom shape. Show how the K loop walks the tile.
- **Thread and wave mapping.** Which wave owns which part of the output tile. Which lane holds which element of the MFMA operand and result. Use a small grid, not a list.
- **Pipeline.** A timeline with one row per resource: global loads, LDS writes, LDS reads, MFMA. Mark each `s_waitcnt` and each barrier. Show where a wave waits and what it waits for.
- **A change.** Draw before and after side by side. Mark what moved: a hop, a wait, a tile, a stage.

Use ASCII or Mermaid. Use a generated picture only for a spatial idea that text cannot draw, such as a swizzle pattern.

## Numbers

State each number on one line: value, unit, run count, range. Then say what it means.

- Percent of peak. Compute it from the median time. For GEMM, TFLOPS is `2*M*N*K` over the time. State it as a percent of the MFMA peak or the HBM peak for the arch and dtype. Follow **principle-explain-the-number**.
- Peak source. Read the `refs` resource, in the source whose topics include `peaks` or `roofline`. Cite the source name and the file you read. Cite a `kb` note only when the area `README.md` points to it. When a resource is not set, write `skipped <key>: not set`, and state the peak with its public source.
- The limit. Name what limits the number: memory, MFMA issue, LDS conflicts, a wait, low occupancy. Rule out a measurement artifact. Follow **principle-explain-the-number**.
- Resource numbers. Explain VGPR, spills, LDS bytes, and waves per SIMD as a budget: what one wave takes, and how many waves fit. A reader who needs the terms in plain words gets `/bro`.
- A trace. For a captured trace, hand the analysis to the `trace.analyze` port. Explain its hotspot plan. Do not re-derive it.

## HTML page

Write one self-contained HTML file when the kernel has three or more moving parts. Use inline CSS and JS, and no CDN. Save it next to the artifacts: the ticket folder in ticket work, and the work dir otherwise. Give its path in the reply.

The page holds:

- A stepper over the data-flow series. Each click adds one hop.
- A tile grid. Hover on a cell shows its wave, its lane, and its K step.
- A pipeline timeline. Click on a wait shows what it waits for.
- A numbers table with the percent of peak and its source.

The reply still carries the first diagram and the verdict. The page adds depth.

## Reply

Write in the owner's reply style: about half ASD-STE100, short sentences, one thought each, diagrams first. Follow the **unslop** skill. Give each concept one name and keep it. Do not print framing labels. No quizzes, no pacing theater.

- Line 1 names the reader and what they can now do.
- Then the first diagram, and the smallest complete answer in one or two sentences.
- Then the next diagram when the question needs it.
- The reply is the explanation. It is not a report of what you did.
- End with the threads worth chasing with `how` or `why`, and an offer to go deeper. In a one-shot run, put the offer last.
