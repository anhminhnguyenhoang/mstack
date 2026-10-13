---
name: bro
description: "Translate the kernel and ROCm jargon in the last message into plain words for a reader who does not write GPU kernels. Use for /bro, 'say that in plain words', 'what is a VGPR, LDS, or MFMA', 'what does occupancy mean', 'I do not know these terms'."
disable-model-invocation: true
---

# Bro

Restate the last message for a reader who does not write GPU kernels. Replace each jargon term with plain words. Then give the original point in one sentence.

## Steps

1. Find every kernel or ROCm term in your last message.
2. Replace each term with its plain meaning. Use the table below.
3. Add a one-line analogy only when the plain meaning alone does not land.
4. Keep every number, unit, and verdict. Do not drop a measurement to be simpler.
5. End with the original point in one sentence.

```
last message ──► find jargon ──► plain words ──► point in one sentence
```

## Terms

| Term | Plain words | Analogy (use only if needed) |
|---|---|---|
| VGPR | Fast private memory of one thread | A worker's own hands |
| AGPR | Extra private memory used for matrix results | A tray next to the hands |
| LDS | Small fast memory that the threads of one block share | A shared table in a workshop |
| HBM | The big main memory of the GPU | The warehouse |
| MFMA | A hardware instruction that multiplies small matrix tiles in one step | A press that stamps a whole tile at once |
| wave | A group of threads that run the same instruction together (64 on this GPU) | A rowing crew |
| SIMD | One of the four execution units inside a CU. It runs waves | One lane of the factory |
| CU | One compute unit. A small block of the GPU with its own LDS and SIMDs | One workshop |
| XCD | One chiplet of the GPU. It holds a group of CUs and its own L2 cache | One building of the factory |
| occupancy | How many waves share one SIMD at the same time | Seats filled on a bus |
| waves per SIMD | The number that occupancy counts | Seats filled on a bus |
| spill | A value that did not fit in registers and went to slow memory | A desk so full that papers go to the floor |
| scratch | The slow memory that spills use | The floor |
| `s_waitcnt` | An instruction that stops the wave until its memory loads arrive | Wait at the door for the delivery |
| roofline | The speed limit of a kernel set by memory bandwidth or by math speed | The speed limit of a road |
| percent of peak | The speed of the kernel divided by that limit | 80 km/h on a 100 km/h road is 80 percent |
| ATT | A trace that records what every wave did, instruction by instruction | A security camera for one kernel |
| eager | Each GPU call is launched from Python one at a time | A cook who reads one step at a time |
| graph replay | The whole sequence of GPU calls is recorded once and replayed | A cook who follows a finished card |
| tile | One small block of the matrix that one thread block works on | One tile of a floor |
| epilogue | The last step that converts and writes the result to memory | Packing the box |

A term that is not in the table: say what it holds, what it does, or what it limits, in plain words. Do not guess a meaning you cannot state.

## Reply

Write the reply as the owner's reply style says: short sentences, one thought each, no filler.

- Use a table of `term | plain words` when the message has three or more terms.
- Use a diagram when the point is a flow, for example `HBM ──► LDS ──► VGPR ──► MFMA`.
- Do not apologize for the first message. Do not explain what you are doing.

```
term | plain words
...

Point: <the original point, one sentence, plain words>
```
