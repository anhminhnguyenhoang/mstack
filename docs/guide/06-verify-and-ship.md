# Verify the result and open a PR

"It compiles" is not evidence. The [Prove it works principle](../../skills/principle-prove-it-works/SKILL.md) makes the agent check the real artifact before it reports success, and your job is to make "the real artifact" checkable. This page covers stating a finish condition, vetting a measured number, generating a verification skill for a kernel library, opening the draft PR, and driving it to ready for your review.

Verification is the slowest step in most agent work, because it's the step that usually waits on a human. Make the agent able to do it, and you stop being the bottleneck. Skip it, and running more agents only gets you more unchecked work to review.

![A prototype plane flies a real test course while she times it with a stopwatch and robots film and checklist the run; the terminal reads verify: pass, evidence: captured.](./images/verification.jpg)

## State the finish condition up front

Put what done means in the first prompt, in whatever words fit:

```text
/ateam-mode add an fp8 path to this op. the bf16 output stays bit-identical, fp8 matches the torch reference within rtol and atol, and both run in the container on a locked gpu. show me the evidence.
```

Now the agent has three checks it can run. When the reply comes back, it should carry the exact commands and outputs. If a check couldn't run, a good reply says "inconclusive", and you should treat a confident reply without evidence as a red flag.

Match the check to the change:

- A kernel change runs the op test in the container on a locked GPU.
- A numerics change compares against the torch reference, with `rtol`, `atol`, and the NaN count.
- A register, spill, or LDS change compares the ISA before and after.
- A perf change compares before and after medians on one GPU, then a counter pass for the limiter.
- A config or dispatch change replays every tuned shape and checks which kernel each one picks.

Ask for the proof as an artifact you can inspect yourself: the failing test and then the passing one, the raw bench log, the ISA diff, the trace. If the fix already merged, ask for the same check again on main. An artifact beats a plausible explanation, because you can challenge it without replaying the whole run.

For a small diff you don't fully trust, [`/blast-radius`](../../skills/blast-radius/SKILL.md) finds what it could break elsewhere. It picks the one fact the change is safe because of and proves it by running code instead of writing an essay about it.

## Vet a measured number with `/benchmark-checklist`

A before-and-after number is the easiest evidence to get wrong by accident. A warm cache, a debug build on one side, or work that never ran inside the timed region can each produce a convincing speedup. Before you report or act on a number, type:

```text
/benchmark-checklist vet the GEMM speedup on gfx950 before it goes in the pr
```

[`/benchmark-checklist`](../../skills/benchmark-checklist/SKILL.md) asks seven questions and wants evidence from a run for each:

1. What limits the number, and why isn't it double?
2. Did every side run tuned the way production runs?
3. Does the result break a physical limit, like HBM bandwidth or the MFMA peak?
4. Did anything error or return wrong output?
5. Does it reproduce over alternating runs, with a median and a range?
6. Does it matter end to end, as a share of the model step?
7. Did the work happen inside the timed region?

The verdict comes back as faster, slower, no measurable difference, or inconclusive, with the run count, range, and limiter. It says inconclusive when it can't name the limiter or a side ran untuned. `/ateam-mode` already runs the checklist inside the Perf issue and Kernel hillclimb playbooks, so you type it yourself when you measured something outside them, or when someone else's number looks too good. It's the working form of the [Explain the number principle](../../skills/principle-explain-the-number/SKILL.md).

## Create a project verification skill

For a kernel, [`/verify-gpu-kernel`](../../skills/verify-gpu-kernel/SKILL.md) is the scripted way. It resolves the host and container, locks one idle GPU, runs the op test, and writes a JSON artifact. It runs one command. It does not know which commands prove a whole kernel library. For that map, run:

```text
/create-verification-skill
```

[`/create-verification-skill`](../../skills/create-verification-skill/SKILL.md) interviews the repository, not you. It inventories the op families and their test entry points (op tests, pytest targets), and maps each family to a correctness gate, a perf run against the reference, and an ISA resource check. It asks you only what the code can't answer.

It writes `.cursor/skills/verify-<lib>/`, agent-facing instructions plus a feature map under `features/` with one file per op family and the result that proves it works. The skill ships a [worked feature-map example](../../skills/create-verification-skill/references/feature-map-example/) with a README index and one file per feature using the four required H2s. Before handing it over, the generator proves the skill once on one locked GPU through the `bench.run` skill function: doctor, one feature, the artifact. If that proof fails, don't use the output.

From then on, "verify it in the app" is a step any agent can execute, in this repo, with no setup conversation. Name it in the prompt when you want the proof in a specific form:

```text
/ateam-mode build the fp8 path for this op. use /verify-gpu-kernel to verify your changes and show me the artifact JSON as proof.
```

```text
/ateam-mode repro this kernel failure with /verify-gpu-kernel on gfx950. if it repros on main, fix it and show me the artifact JSON as proof.
```

Once the verify skill works, a fan-out from `/ateam-mode` can split a full pass by feature-map entry and aggregate the results. A fan-out of verifiers also confirms a perf win over a big enough sample, or fuzzes the interface for regressions before a PR ships.

Treat the verification skill as infrastructure, not a one-off. Commit it, so every person and every agent on the team runs the project the same way. Then [build the lever](../../skills/principle-build-the-lever/SKILL.md). When agents keep writing throwaway scripts to click through the app, ask for a small control CLI that the skill calls instead. Agents spend fewer tokens, and every run becomes repeatable. A CLI that agents use well has these traits:

- A few composable commands, each doing real work, rather than many thin ones.
- A `--dry-run` option on anything destructive.
- Subcommands that reveal features gradually instead of all at once.
- Error messages that say what to do instead.
- Rich `--help` text.
- Machine-readable output, such as JSON.

While you're there, make the setup repeatable too: one container image, pinned repo SHAs, and one command per op family.

## Keep the verification skill honest

Op tests change, tolerances move, and feature maps rot. Run this at least once a day, ideally from a scheduled automation so nobody has to remember:

```text
/maintain-verification-skill
```

[`/maintain-verification-skill`](../../skills/maintain-verification-skill/SKILL.md) audits the generated skill: one read-only source reader per op family in parallel, then one live pass on one locked GPU that re-proves every mapped feature. It ends in exactly one of three outcomes. `clean` means full coverage and nothing to ship. `changed` means one PR of proven corrections, confined to the verification skill's own directory. `blocked` names the blocker. It never edits kernel code. If the live pass catches a kernel regression, it reports the regression instead of hiding it in docs.

## Open the PR

```text
/ateam-mode open the pr. small ordered commits, evidence in the description.
```

The [Opening a PR playbook](../../skills/ateam-mode/playbooks/opening-a-pr.md) works from a worktree, rebases the work into small ordered commits, cleans the diff, unslops the prose, and returns the PR link. Five narrow PRs beat one fat one, and stacked follow-ups beat a growing branch.

## Drive the PR to merge-ready with Babysit

An open PR starts collecting blockers immediately. Checks fail, reviewers comment, trunk moves. Hand that churn to the [Babysit playbook](../../skills/ateam-mode/playbooks/babysit.md):

```text
/ateam-mode babysit this pr. get it green.
```

Babysit polls the PR on a bounded interval under `/loop` and takes blockers in order: conflicts, then review threads, then CI. Every known fix batches into one push, so the checks restart once instead of after every fix. The comment triage is skeptical, because humans and bots file real catches and noise in the same list. A real finding gets a fix, and noise gets dismissed with the disproof posted on the thread. When all you want is status, ask smaller and Babysit answers without starting the loop:

```text
/ateam-mode check on pr 123. anything outstanding?
```

Babysit stops at merge-ready. It never merges, even with everything green, because merging is a different decision.

## Land the stack with Shipping

Green is not the same as safe. When you're ready to land, say so:

```text
/ateam-mode land the stack.
```

The [Shipping playbook](../../skills/ateam-mode/playbooks/shipping.md) verifies each PR independently before it arms anything. One fresh agent per PR proves the behavior live, and the agent that judges a change is never the one that wrote it. Then Shipping lands only the contiguous verified run from the bottom, one PR at a time through the resolved PR tool, and reports the first PR that breaks the chain. A verified PR sitting above an unverified one waits, because merging it would pull the gap in underneath.

Next: [Run work while you sleep](./07-overnight.md).
