### Repro audit

**You own the verdict on someone else's claim. Plan, run, judge.** For a result, a number, or a bug report you did not produce: "reproduce the SGLang numbers", a customer's failing script, a version matrix on a ticket. The deliverable is a finding, not a fix.

Run on the real GPU, in a container, with the claim's own script before any rewrite. A verdict from a rewritten script is a verdict on your script.

1. Write each claim verbatim with its source (ticket comment, PR, doc, chat) and its date. Split a compound claim into one line per claim, each with the number and condition it states.
2. Pin the environment before you run. Record the ROCm and torch versions (`torch.__version__`, `torch.version.hip`), the triton version, the aiter and FlyDSL SHAs, the docker image tag, the GPU model and arch (`gfx942` or `gfx950`), and the GPU id. Where the claim does not state an item, mark it `unstated` and pick the closest image you have. Say which one.
3. Reproduce exactly. Run the claim's script on the claim's stated environment, as given. Save the full output next to the script. If the claim does not reproduce, check the environment gap before you declare a result. Use the **verify-gpu-kernel** skill for the host, container, and GPU lock.
4. Vary one axis at a time. Take the axes from the ticket and the gap: ROCm version, torch version, arch, backend, dtype, shape, or scale. Keep every other pin fixed. Run the whole version matrix with one script that prints the pins on each row, as in `~/ROCM-31582/repro_version_matrix.py`. Vet every number with the **benchmark-checklist** skill, including its GPU kernels section.
5. Find the mechanism when a claim fails or varies. Name the dispatched kernel and library from a trace, not from the Python API (`~/ROCM-31582/notes/root-cause.md` is the shape). A cause without the dispatched kernel is a guess.
6. Give each claim a verdict.
   - `reproduced`. Same number or behavior within the stated spread, in the stated environment.
   - `partial`. Reproduced in some cells of the matrix. Name which cells.
   - `not reproduced`. A clean run in the stated environment shows otherwise. State the number you got.
   - `blocked`. You could not run it: missing hardware, image, access, or data. Say what is missing.
   `blocked` is never `not reproduced`.
7. Run **Deliver** as a finding. The comment draft lists the claims and verdicts first, then the environment matrix, the reproduce command, and the artifact paths. Keep the folder `~/<KEY>/` with the scripts, the raw output, and `notes/`.

For an SGLang PR or an in-model number, add the pins and the head and base SHAs from `references/sglang.md`.

**Reply:** one line per claim with its verdict, the matrix of environments with the cells that differ, the mechanism if you found one, the artifact folder, and the draft path.
