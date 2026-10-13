# Prompts worth copying

Swap in the real paths, skills, and done checks. Informal wording works.

## Understand

- `/ateam-mode read PROJ-123 and its comments. restate the underlying issue in your own words, in plain english.`
- `/ateam-mode investigate why <symptom>. give me what we know, what data you used, and your best hypotheses. don't change any code yet.`
- `use /how to understand how <dispatch> picks a kernel. then use /why to find out why it started picking the HIP kernel.`
- `/recall my work on <kernel> from last week, then read PROJ-123.`
- `/teach me why you implemented it this way and not <other way>. what did you trade off?`
- `/ateam-mode take over this branch. read the decision log, find what's done, and continue. don't redo finished work.`

## Build

- Bug: `/ateam-mode <symptom>. repro first, then fix and verify.`
- Bug on the GPU: `/ateam-mode repro this kernel failure with /verify-gpu-kernel on <arch>. if it repros on main, fix it and show me the artifact JSON as proof.`
- Bug with a cheap test: `/ateam-mode repro <bug> first. if there's a cheap test path, /tdd it. then fix and rerun.`
- Feature: `/ateam-mode add <path> to <op>. the <current dtype> output stays bit-identical. verify both against the torch reference.`
- Refactor: `/ateam-mode clean up <kernel> without changing its ISA. save the current ISA first and prove it's byte-identical after.`
- Perf: `/ateam-mode close the <ratio> gap to the <reference> for <kernel> on <arch>. trace it, fix the measured cause, show me before and after.`
- Kernel hillclimb: `/ateam-mode get <kernel> within <ratio> of <reference> on <arch>. done means the correctness gate passes on every shape and the median of 7 runs is within <ratio>.`
- Bound a redesign: `/ateam-mode bound the ceiling of <redesign> before we build it.`
- Audit a claim: `/ateam-mode reproduce the numbers claimed in <pr>.`
- Read a trace: `/ateam-mode here is an ATT trace of <kernel>. where does the time go? no fix yet.`
- Ticket: `/ateam-mode resume PROJ-123.`

## Design and plan

- `/ateam-mode prototype a few options for <layout>. run the ISA check on each and send me the counts to compare.`
- `/ateam-mode we need <feature>. /architect it first, and answer open questions with prototypes. let me review before proceeding.`
- `/ateam-mode write a tutorial for how i would call <new API> first. then /teach me why it beats the current one.`
- `ask /arena for a second opinion on this thread and our approach.`
- `/ateam-mode turn this design into a plan. small verifiable PRs, each with its own verification steps.`
- `/ateam-mode plan the migration of <configs or helper> to <target>. small verifiable PRs, each with a check that every shape resolves as before. the result must match the original exactly, bugs included.`

## Review and ship

- `/interrogate the whole branch, but skeptically. don't change anything yet. no nitpicks unless it's a real bug or regression.` Read the dismissals too.
- `/ateam-mode check every kernel under <dir> with the isa.diff port. one worker per kernel. one report.`
- `/ateam-mode open the pr. small ordered commits, evidence in the description.`
- `/ateam-mode babysit this pr. get it green.` For status only: `/ateam-mode check on pr <number>. anything outstanding?`
- `/ateam-mode land the stack.`

## Away and back

- `/ateam-mode im going to bed. <goal> in a fresh worktree off <base>. done means <checks>. keep a decision log. don't ask me before committing. /loop until done. if you're truly stuck after a few hours, stop and write up why.`
- `/show-me-your-work catch me up on what you did last night.` Read its Attention section first.
- `/ateam-mode full autopilot on this queue. each item is independent.`
- `/ateam-mode autopilot these changes but stack them, don't ship. i'll land the stack.`
- `/reflect capture what we learned so the next run doesn't repeat it.` Approve only edits that change a future decision.
- `/bro` restates the last reply in plain words.
