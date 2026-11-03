---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Adversaries try to break a change or design, and only findings proven by a run survive."
disable-model-invocation: true
---

# Interrogate

Adversaries try to break a change or a design. A finding survives only when a run proves it. Report the findings. Do not apply fixes.

## Step 1, Scope

The scope is what the user names: specific files, a diff, or recent work. Otherwise it is the branch diff from its merge base with the base branch, through the working tree.

## Step 2, Intent

State the intent with the **in-your-own-words** skill, from the user's message, the commits, and the PR description when one exists. Ask the user when the intent is unclear.

## Step 3, Fan out

Run Phase A steps 3 and 4 and Phase B of the **arena** skill, with four changes. Read the `interrogate reviewers` line in place of `arena runners`. Copy the scope's uncommitted changes into each worktree. Spawn each adversary as `generalPurpose`. In place of the arena task and rationale, give each adversary the scope, the intent, and this brief:

> Break this change. Prove each finding with a run against the real code, such as a failing test, a repro script, or command output that shows the wrong behavior. For a kernel, that is an op test or a repro that prints wrong values, or a fault, on a named shape, dtype, and arch. For a design or plan, run a prototype or probe the current tree. Keep repros in your own worktree. Report each finding with a title, the exact command, the output it printed, and the output the intent requires. Leave out anything you did not run. That covers style, naming, structure, and risks that need a future change to matter. No findings is a valid result.

When the diff touches a GPU kernel or its dispatch, also add the GPU kernel findings section of `../ateam-mode/references/review-bot-triage.md` to the brief, so each adversary runs the check that settles each kernel finding. Adversaries share the GPU: hold each GPU run to one locked GPU.

### Read-only review group

The PR review playbook (`../ateam-mode/playbooks/pr-review.md`) runs the group differently, blind and read-only, through `scripts/review-group-gate.py`. Steps 1 and 2 and the `interrogate reviewers` line still apply. The gate fills `references/reviewer-prompt.md` with the intent, the diff, `references/rubric.md`, and `references/code-quality-review.md`, and it records each reviewer's reply. The playbook merges the findings, and its card's refutation rule takes the place of Step 4's rerun. Do not edit those three files without reading the gate script first.

## Step 4, Verify

Verify each finding per arena Phase F by rerunning its command. Keep a finding when the output shows the failure and the failure breaks the intent. A failure on an input no caller can pass, such as a shape the op wrapper or the dispatcher rejects, does not break the intent. Drop the rest. Merge findings that share a root cause.

Skip arena Phases C, D, and E. Adversaries find different failures, so the verdict keeps every verified finding, not one adversary's list.

## Output

- **Intent**: the restatement.
- **Findings**: for each verified finding, the command, its output, how it breaks the intent, and the adversaries that found it. Say "no verified findings" when none survive.
- **Dropped**: for each adversary, the count of dropped findings and why.
