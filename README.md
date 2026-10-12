# mstack

mstack is a Cursor plugin for AMD GPU kernel development and Jira-ticket-driven work. It targets aiter, FlyDSL, Triton, and HIP/MFMA kernels on MI300X (gfx942) and MI355X (gfx950).

It is a fork of [pstack](https://github.com/cursor/plugins/tree/main/pstack) (see [Upstream](#upstream)). It keeps pstack's process: go deep first, write less code, verify against the real artifact. It adds the kernel domain and a ticket lifecycle.

**mstack ends in a deliverable, not always a PR.** A ticket can end in a PR, a Jira comment draft, or both. A human approves every Jira post.

**mstack routes to kernel skills.** Kernel work goes to the matching skills in `~/.claude/skills`, such as `cdna-kernel-opt`, `flydsl-kernel-authoring`, and `isa-resource-diff`.

## install

```bash
/add-plugin mstack
```

## get started

two steps:

1. run [`/setup-mstack`](./skills/setup-mstack/SKILL.md), pick a reasoning budget, and choose which models you want.
2. use [`/ateam-mode`](./skills/ateam-mode/SKILL.md) whenever you're doing anything that requires rigor.

new here? the [mstack guide](./docs/guide/README.md) walks you through a first real task, from setup and prompting through verification and overnight runs. stuck, or unsure which skill fits? ask [`/ateam-help`](./skills/ateam-help/SKILL.md).

that's it. the other skills are situational; the mode skill uses them for you as needed. out of the box the mode splits work by model strength: code delegates (feature, refactoring, bug fix, perf, hillclimb) go to grok, while the hardest changes, prose, and judgment go to opus 5.5. the default panel is opus 5.5 / grok. [`/setup-mstack`](./skills/setup-mstack/SKILL.md) changes any of it.

## usage

use [`/ateam-mode`](./skills/ateam-mode/SKILL.md) at the start of a task. it reads your request, picks from a set of playbooks, and runs the other skills as the steps need them.

### just use [`/ateam-mode`](./skills/ateam-mode/SKILL.md)

this skill is the main shortcut. i use it whenever i need the agent to do rigorous engineering work. it comes with twenty-six playbooks:

```
/ateam-mode this pr has a subtle bug where the scroll drifts every 750ms even when idle. repro
first, then fix and verify.
```

```
/ateam-mode i'm going to bed. land the stack even if ci flakes. i want everything merged by
morning.
```

<details>
<summary>the twenty-six playbooks</summary>

| playbook | for |
|---|---|
| [investigation](./skills/ateam-mode/playbooks/investigation.md) | a read-only question. how does x work, why was y built this way, are we sure. |
| [bug fix](./skills/ateam-mode/playbooks/bug-fix.md) | reproduce a defect, root-cause it, and fix with runtime evidence. |
| [perf](./skills/ateam-mode/playbooks/perf-issue.md) | trace a measured slowness and improve it against a baseline. |
| [hillclimb](./skills/ateam-mode/playbooks/hillclimb.md) | sustained, scientific improvement of one metric against a target, looping hypotheses with before/after measurement and one commit per accepted win. |
| [kernel hillclimb](./skills/ateam-mode/playbooks/kernel-hillclimb.md) | hillclimb for a gpu kernel: correctness-gated harness, isa resource pre-check before any benchmark, one benchmark on a locked gpu at a time, levers named from the cdna-kernel-opt menu. |
| [repro audit](./skills/ateam-mode/playbooks/repro-audit.md) | verify someone else's claim, number, or bug report on the real gpu: pin the environment, reproduce as stated, vary one axis, and give each claim a verdict. |
| [runtime forensics](./skills/ateam-mode/playbooks/runtime-forensics.md) | diagnose a live symptom (leak, idle-cpu spin, glitch) from instrumentation. |
| [trace forensics](./skills/ateam-mode/playbooks/trace-forensics.md) | diagnose a captured profiling artifact (cpuprofile, trace, spindump, heap snapshot). |
| [feature](./skills/ateam-mode/playbooks/feature.md) | new or changed behavior, built from a named data shape. |
| [refactoring](./skills/ateam-mode/playbooks/refactoring.md) | a behavior-preserving change to structure or shape. |
| [prototype](./skills/ateam-mode/playbooks/prototype.md) | a throwaway sketch to make a design or behavioral decision cheaply, or to settle an empirical fork by observing it. |
| [authoring a skill](./skills/ateam-mode/playbooks/authoring-a-skill.md) | writing or editing a SKILL.md. |
| [eval](./skills/ateam-mode/playbooks/eval.md) | test how a skill or prompt change affects agent behavior, blinded. |
| [babysit](./skills/ateam-mode/playbooks/babysit.md) | drive a pr or a stack to merge-ready: conflicts, review threads, ci. |
| [shipping](./skills/ateam-mode/playbooks/shipping.md) | independently verify a green stack, then land the contiguous verified run bottom-up through github by default or origin when available. |
| [autonomous run](./skills/ateam-mode/playbooks/autonomous-run.md) | drive a long task to completion without stopping. |
| [orchestrate](./skills/ateam-mode/playbooks/orchestrate.md) | a standing project handed to one coordinator chat: multi-day, many stacked prs, fleets of subagents. |
| [autopilot-full](./skills/ateam-mode/playbooks/autopilot-full.md) | run independent prs to merged with one owner per pr and a root swarm verdict on each round, from the code-ready head on. |
| [autopilot-stack](./skills/ateam-mode/playbooks/autopilot-stack.md) | build and verify one linear base-branch stack for the operator to review and land. |
| [session pickup](./skills/ateam-mode/playbooks/session-pickup.md) | resume or take over a prior agent's in-flight work. |
| [pause safely](./skills/ateam-mode/playbooks/pause-safely.md) | suspend in-flight work cleanly so it can be resumed later. |
| [multi-phase plan](./skills/ateam-mode/playbooks/multi-phase-plan.md) | work that spans phases or stacked PRs. |
| [worktree cleanup](./skills/ateam-mode/playbooks/worktree-cleanup.md) | reclaim disk by pruning merged or abandoned worktrees, safety-gated. |
| [ticket](./skills/ateam-mode/playbooks/ticket.md) | work that starts from a jira key. loads the ticket into `~/<key>/` with `/ticket-init`, sets a checkable predicate, routes to the matching playbook, and ends in deliver. |
| [deliver](./skills/ateam-mode/playbooks/deliver.md) | classify the output as code, finding, or both. code goes to opening a pr. a finding becomes a jira comment draft the human approves. invoked at the end of every other playbook. |
| [opening a pr](./skills/ateam-mode/playbooks/opening-a-pr.md) | open a ready pr from small ordered commits with a conventional commits title and a briefing-style body. invoked by deliver for code output. |

</details>



when invoked it:

1. matches your task to a [playbook](./skills/ateam-mode/playbooks/) and opens a todo list whose first items are its steps, copied in verbatim.
2. routes to the other skills as the steps fire.
3. writes replies diagram-first in short asd-ste100-lite sentences, with a one-line number, unit, and run count for each measurement, and an html page when a diagram alone is not enough.

the full rules and playbooks live in [`skills/ateam-mode/SKILL.md`](./skills/ateam-mode/SKILL.md).

to keep [`/ateam-mode`](./skills/ateam-mode/SKILL.md) on across turns, pick it from the `/` menu and press option+enter (mac) or alt+enter (windows) instead of enter. that makes it a [custom mode](https://cursor.com/docs/skills), which cursor offers in the agents window and the cli. it stays in context every turn, applies itself when a playbook matches or the task needs rigor, and stays out of the way otherwise. plain enter attaches it to one message only. say so to opt out, or exit the mode to turn it off.

[`/ateam-mode`](./skills/ateam-mode/SKILL.md) works extremely well with cursor's `/loop` command. you can make cursor work for many hours without sacrificing rigor.

## skills

[`/ateam-mode`](./skills/ateam-mode/SKILL.md) runs most of these for you when a step needs them (`how`, `why`, `architect`, `arena`, `swarm`, `interrogate`, `unslop`, `no-comments`, `technical-writing`, `tdd`, and the principles). the table below is for when you want one directly:

```
/how do we cancel runs? do we have an n+1 when we look up every run to cancel?
```

```
/interrogate review this pr.
```

<details>
<summary>all skills</summary>

| skill | use it when |
|---|---|
| [`/ateam-mode`](./skills/ateam-mode/SKILL.md) | default entry point for any non-trivial task. |
| [`/ateam-help`](./skills/ateam-help/SKILL.md) | you're new to mstack, or unsure which skill, playbook, or principle fits. finds out what you're trying to do, answers that part, and hands you a prompt to type. runs only when you type `/ateam-help`. |
| [`/ticket-init`](./skills/ticket-init/SKILL.md) | you start from a jira key. writes `~/<key>/ticket-raw.md`, a brief of at most 150 words, and an acceptance predicate. |
| [`/verify-gpu-kernel`](./skills/verify-gpu-kernel/SKILL.md) | you need to run, reproduce, or benchmark a kernel on the real gpu. resolves the host and container, locks one idle gpu, runs the op_test, and writes a json artifact into `~/<key>/`. |
| [`/how`](./skills/how/SKILL.md) | you want a walkthrough of how a subsystem works. |
| [`/why`](./skills/why/SKILL.md) | you want to know why something was built this way. discovers available MCPs at run time and queries each evidence category in parallel (source control, issue tracker, long-form docs, real-time chat, infra observability, error tracking, analytics warehouse). |
| [`/recall`](./skills/recall/SKILL.md) | you're starting or resuming work and want your recent context on a topic rebuilt from your own chat history and the shared record, handed back as a tight current-state brief. |
| [`/ketchup`](./skills/ketchup/SKILL.md) | you want everything in this chat since your last message, in plain words, with an executive summary for each action item so you can make the call. |
| [`/blast-radius`](./skills/blast-radius/SKILL.md) | you have a small-looking change and want to know what else it could break, with the one fact it's safe because of proven by running code, not asserted. |
| [`/architect`](./skills/architect/SKILL.md) | you're about to write code that crosses a function boundary and want the caller's usage, types, and module shape settled first. |
| [`/arena`](./skills/arena/SKILL.md) | you want N parallel attempts at the same thing, then to grab the best parts of each. |
| [`/swarm`](./skills/swarm/SKILL.md) | you want N parallel workers across different slices or races, then one aggregated report. |
| [`/interrogate`](./skills/interrogate/SKILL.md) | you have a diff and want different models to try to break it, including a strict code-quality lens. |
| [`/automate-me`](./skills/automate-me/SKILL.md) | you want your own `-mode` skill, drafted from how you've actually worked. |
| [`/setup-mstack`](./skills/setup-mstack/SKILL.md) | you want to pick which models mstack uses per role. detects your models and writes a config rule. |
| [`/reflect`](./skills/reflect/SKILL.md) | a long task landed and you want the recipe captured as a skill edit. |
| [`/correct`](./skills/correct/SKILL.md) | you keep correcting agents for the same mistakes. mines history for mistake classes, fixes each at the highest level that works (architecture, then types, lint, and ci, then tests, with docs last), and keeps a table pairing each rule with what enforces it. |
| [`/teach`](./skills/teach/SKILL.md) | you want to actually understand a change or subsystem, not just have it summarized. runs how + why and weaves one plain explanation, built up diagram by diagram. |
| [`/tdd`](./skills/tdd/SKILL.md) | you're fixing a bug and there's a cheap local test path. write the failing test first, then the fix. |
| [`/benchmark-checklist`](./skills/benchmark-checklist/SKILL.md) | you ran a benchmark or measured a speedup or regression. vets the number (limiter, tuning, errors, repeat runs, end-to-end relevance) before you report or act on it. |
| [`/no-comments`](./skills/no-comments/SKILL.md) | strip comments before review; spawns Comment Sicko, fixes accepted findings, offers encodings for claimed constraints. |
| [`/figure-it-out`](./skills/figure-it-out/SKILL.md) | no bundled playbook fits. designs a rigorous, auditable playbook for the task. |
| [`/show-me-your-work`](./skills/show-me-your-work/SKILL.md) | you want a reviewable decision trail. logs decisions to a tsv you can commit. |
| [`/create-verification-skill`](./skills/create-verification-skill/SKILL.md) | your project has no scripted way to prove app behavior. generates a project-local verify skill with a feature map, for any language or platform. |
| [`/maintain-verification-skill`](./skills/maintain-verification-skill/SKILL.md) | your verify skill's feature map has drifted from the app. source wave + one live pass, at most one PR of proven corrections. |
| [`/unslop`](./skills/unslop/SKILL.md) | you're cleaning up writing. removes AI tells. |
| [`/bro`](./skills/bro/SKILL.md) | you want the last message restated in plain human language, no jargon. |
| [`/technical-writing`](./skills/technical-writing/SKILL.md) | layered doc standard (Diátaxis + Google developer style + STE + Global English) for docs, RFCs, readmes, PR descriptions, commit messages. |

</details>



### examples

mostly i type [`/ateam-mode`](./skills/ateam-mode/SKILL.md) at the start of a task and let it route to a playbook. the other skills fire as the steps need them. a few i reach for directly.


<details>
<summary>all the examples</summary>

```
bug fix:           /ateam-mode this pr has a subtle bug where the scroll drifts every 750ms even
                   when idle. repro first, then fix and verify.
perf:              /ateam-mode a big list takes a second or two to load even though we virtualize.
                   run a cpu trace and tell me why.
feature:           /ateam-mode build a small feature behind a feature flag. verify it really works.
prototype:         /ateam-mode build two prototypes of the markdown renderer so we can compare.
                   spawn an agent for each.
multi-phase:       /ateam-mode open source these skills as a plugin. nothing internal leaks, work
                   in a temp dir, show me the dependency graph first.
overnight run:     /ateam-mode i'm going to bed. land the stack even if ci flakes. i want
                   everything merged by morning.
babysit:           /ateam-mode check on pr 123. anything outstanding?
figure it out:     /ateam-mode i'm stepping away. migrate every caller from the synchronous store
                   to the new async one, keeping behavior identical. i want to trust it was done
                   right when i'm back.
how:               /how do we cancel runs? do we have an n+1 when we look up every run to cancel?
why:               /why is this feature flag not on yet?
architect:         design this instrumentation to be high signal with no false positives. /architect
                   this first.
arena:             /arena take my prompt to the arena verbatim. i want to compare their proposals
                   with yours.
swarm:             /swarm check every package under packages/ against its check.sh. one worker per
                   package. one report.
interrogate:       /interrogate review this pr.
tdd:               /tdd implement
unslop:            can we unslop and tighten the new changes?
reflect:           /reflect that took too long. capture what we learned so the next run doesn't
                   repeat it.
correct:           /correct
show-me-your-work: /show-me-your-work keep a decision trail i can review when i'm back.
automate-me:       /automate-me
help:              /ateam-help which skill should i use to review this branch?
```

</details>

## the `ateam-agent` and Comment Sicko subagents

[`/ateam-mode`](./skills/ateam-mode/SKILL.md) runs in the chat that receives it. that chat owns the playbook, the todo list, and every subagent spawn.

mstack also ships [`subagent_type: "ateam-agent"`](./agents/ateam-agent.md) as the wrapper for delegates spawned during a run. it reads `ateam-mode` in full, including its inline principles index, before doing any work. substituting `generalPurpose` skips that read and drifts. do not spawn `ateam-agent` to run the playbook itself.

[`/ateam-mode`](./skills/ateam-mode/SKILL.md) and [`subagent_type: "ateam-agent"`](./agents/ateam-agent.md) route through the same wrapper.

mstack also ships [Comment Sicko](./agents/comment-sicko.md), a read-only comment reviewer available as `subagent_type: "comment-sicko"`. usually invoke it through [`/no-comments`](./skills/no-comments/SKILL.md), not directly.

## principles

twenty-seven short skills, one principle each. `ateam-mode` indexes them inline and reads that index at task start. the standalone files are there so other skills can reference a principle by name, and so the index can point at the full rule for each.

<details>
<summary>all twenty-seven principles</summary>

| principle | group | rule |
|---|---|---|
| [laziness-protocol](./skills/principle-laziness-protocol/SKILL.md) | core | Bias toward deletion and the smallest change that solves the problem. |
| [foundational-thinking](./skills/principle-foundational-thinking/SKILL.md) | core | Apply before writing logic: choosing core types and data structures, sequencing scaffold-vs-feature work, asking what concurrent actors share. Get the data structures right so downstream code becomes obvious. |
| [redesign-from-first-principles](./skills/principle-redesign-from-first-principles/SKILL.md) | core | Redesign as if the requirement had been a foundational assumption from day one, instead of bolting it on. |
| [attack-the-premise](./skills/principle-attack-the-premise/SKILL.md) | core | Apply when two or more fixes that share one premise have failed the same gate. Take a census of which actors hold the imbalance before the next fix, then question the premise instead of writing another fix that assumes it. |
| [subtract-before-you-add](./skills/principle-subtract-before-you-add/SKILL.md) | core | Remove dead weight, redundant validators, and stub references first, then build on the simpler base. |
| [minimize-reader-load](./skills/principle-minimize-reader-load/SKILL.md) | core | Count layers between question and answer, and hidden state in the reader's head; collapse one-caller wrappers and shrink mutable scope. |
| [outcome-oriented-execution](./skills/principle-outcome-oriented-execution/SKILL.md) | core | Apply during planned rewrites and migrations with explicit phase boundaries. Converge on the target architecture; don't preserve smooth intermediate states with throwaway compatibility code. |
| [experience-first](./skills/principle-experience-first/SKILL.md) | core | Choose user delight over implementation convenience; ship fewer polished features over more rough ones. |
| [exhaust-the-design-space](./skills/principle-exhaust-the-design-space/SKILL.md) | core | Build 2-3 competing prototypes and compare side by side before committing. |
| [build-the-lever](./skills/principle-build-the-lever/SKILL.md) | core | Apply to any non-trivial work, not just bulk work: edits, migrations, analyses, checks. Build the tool that does it or proves it (codemod, script, generator, or a skill your subagents follow) instead of working by hand. The tool is the artifact a reviewer can rerun. |
| [model-the-domain](./skills/principle-model-the-domain/SKILL.md) | architecture | Encode the domain in a structure instead of scattered conditionals. |
| [boundary-discipline](./skills/principle-boundary-discipline/SKILL.md) | architecture | Concentrate guards at system boundaries (CLI, config, network, external APIs); trust internal types and keep business logic in pure functions. |
| [type-system-discipline](./skills/principle-type-system-discipline/SKILL.md) | architecture | Make illegal states unrepresentable, brand semantic primitives, parse external data at boundaries, refuse to lie to the compiler, exhaust variants, derive from authoritative schemas. |
| [make-operations-idempotent](./skills/principle-make-operations-idempotent/SKILL.md) | architecture | Converge to the same end state regardless of partial prior runs. |
| [migrate-callers-then-delete-legacy-apis](./skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | architecture | Migrate callers and delete the old API in the same wave instead of preserving compatibility layers. |
| [separate-before-serializing-shared-state](./skills/principle-separate-before-serializing-shared-state/SKILL.md) | architecture | Eliminate the sharing first; serialize structurally only when one shared writer is a real invariant. |
| [prove-it-works](./skills/principle-prove-it-works/SKILL.md) | verification | Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'. |
| [fix-root-causes](./skills/principle-fix-root-causes/SKILL.md) | verification | Trace each symptom to its root cause and fix it there; reproduce first, ask why until you reach it, resist nil-check guards that silence crashes. |
| [sequence-verifiable-units](./skills/principle-sequence-verifiable-units/SKILL.md) | verification | Apply to multi-step work (sweeps, migrations, runs of similar edits) and to how you stack commits and PRs. Break work into small units that each end in a verifiable state, check each before the next, and order delivery so the sequence proves itself to a reviewer. |
| [test-behavior-not-implementation](./skills/principle-test-behavior-not-implementation/SKILL.md) | verification | Apply when you write, change, or keep a test. Call the code the way its users do and assert the result they observe against a literal expected value. If the test would still pass when every imported function returns undefined, rewrite the assertion or delete the test. |
| [explain-the-number](./skills/principle-explain-the-number/SKILL.md) | verification | Apply before you trust, report, or act on a number you measured: a speedup, a regression, a throughput, a latency, or an eval result. Find what limits it, and rule out that it measured something other than the work you think. |
| [respect-the-roofline](./skills/principle-respect-the-roofline/SKILL.md) | verification | Apply before you report or act on a GPU kernel performance claim. State it as a percent of the HBM or MFMA peak for the arch and dtype, with the peak's source. |
| [prove-it-reached-codegen](./skills/principle-prove-it-reached-codegen/SKILL.md) | verification | Apply when you change a compile hint, flag, attribute, or kernel structure and want credit for a result. A knob is real only if the ISA or IR changed. |
| [correctness-before-speed](./skills/principle-correctness-before-speed/SKILL.md) | verification | Apply before you time, report, or keep any kernel change. A perf number counts only after an allclose check and a NaN count pass on the same run. |
| [guard-the-context-window](./skills/principle-guard-the-context-window/SKILL.md) | delegation | Route bulk to subagents; keep summaries in the main thread, not raw payloads. |
| [never-block-on-the-human](./skills/principle-never-block-on-the-human/SKILL.md) | delegation | Proceed, present the result, let the human course-correct after the fact; reserve confirmation for irreversible actions. |
| [encode-lessons-in-structure](./skills/principle-encode-lessons-in-structure/SKILL.md) | meta | Encode the rule as a lint, metadata flag, runtime check, or script instead of more text. |

</details>

## not shipped here

a few things `ateam-mode` references but doesn't bundle:

- the kernel skills it routes to (`cdna-kernel-opt`, `flydsl-kernel-authoring`, `format-code`, `validate-kernel-pr`, and the rest of the [kernel skill map](./skills/ateam-mode/references/kernel-skill-map.md)) live in `~/.claude/skills`, not in this plugin.
- `/create-skill` is a cursor built-in. cursor also ships a built-in `/babysit`; inside `ateam-mode`, the [babysit playbook](./skills/ateam-mode/playbooks/babysit.md) supersedes it for pr-status requests.

## why are there no planning skills?

cursor already has a great plan mode which works great with mstack. but personally, i don't believe in planning. the best spec is code. if you do want to make a plan, [`/ateam-mode`](./skills/ateam-mode/SKILL.md) covers it, but it's not a default. 

## make it yours

`ateam-mode` is one engineer's style. you may not want exactly that.

type [`/automate-me`](./skills/automate-me/SKILL.md). it mines your recent transcripts, drafts a `<your-name>-mode` skill from how you've actually worked, and routes through mstack underneath. you keep mstack as the base and end up with your own routing skill alongside `ateam-mode`.

models are configurable too. type [`/setup-mstack`](./skills/setup-mstack/SKILL.md). it detects the models you have access to and writes a small always-applied rule mapping each role (code, judgment, the review panels) to a model. every skill reads it and falls back to sensible defaults when the rule is absent, so you override only what you want.

when a default changes, a rule written before the change still pins the old default. delete those role lines, or delete the file, then run `/setup-mstack` again. a rerun keeps any role whose model differs from the default.

## automations

mstack also ships a dormant [benny automation pack](./automations/benny/). benny triages slack issue reports, then reproduces and fixes confirmed bugs with real ui evidence. its files are not registered as slash skills.

to set it up, point cursor at [`FOR_AGENTS.md`](./automations/benny/FOR_AGENTS.md). setup copies the pack into the target repository at `.cursor/automations/benny/`, enables mstack there for shared skills, and keeps user configuration outside the copied pack.

## Upstream

mstack is forked from [pstack](https://github.com/cursor/plugins/tree/main/pstack) 0.15.20 by poteto (Lauren Tan), MIT licensed. The pristine import is commit `1491916`. [`LICENSE`](./LICENSE) keeps the upstream copyright notice.

To sync with upstream:

```bash
git clone https://github.com/cursor/plugins /tmp/cursor-plugins
mkdir /tmp/mstack-import && git archive 1491916 | tar -x -C /tmp/mstack-import
diff -ru /tmp/mstack-import /tmp/cursor-plugins/pstack
```

Port the changes you want by hand. Upstream paths use `pstack`, `poteto-mode`, `poteto-agent`, `poteto-help`, and `setup-pstack`. Map them to `mstack`, `ateam-mode`, `ateam-agent`, `ateam-help`, and `setup-mstack`.

## license

MIT
