---
name: ateam-help
description: Guides users through mstack setup, /ateam-mode, and picking the skill, playbook, or principle for a task. Type /ateam-help with a question.
disable-model-invocation: true
---

# Ateam help

Answer the user's question about mstack, hand them a prompt they can send, and link the file the answer came from. For a help question, don't start the work. The user asked how, and an mstack run spends real tokens, so let them send the prompt.

A message that asks for work, such as "use mstack to fix this bug", is not a help question. Read [`ateam-mode`](../ateam-mode/SKILL.md), do the work under it, and mention once that a Custom Mode keeps it on.

This file maps questions to the skills and guide pages that hold the answers. Those files own the details. Read the file you route to before you quote it, and trust it when it disagrees with this map. The links here point into the installed plugin, which the user may not be able to open, so give the user the file's repo copy: the `homepage` field of the plugin's `plugin.json`, then `/blob/main/`, then the file's path.

## Find out what they need

Infer the need from the message and the conversation. A named situation, such as "which skill reviews a PR?", goes straight to its section. If the need is still unclear, ask one multiple-choice question with these options, then answer only the section they pick:

- Get set up
- Start a task with `/ateam-mode`
- Pick a skill for a situation
- Fix a run that went wrong
- Make mstack my own

Check the state that changes the answer, and mention it only when it does:

- No `~/.cursor/rules/mstack-models.mdc` means `/setup-mstack` hasn't run for this user, so every role uses its default model.
- No `~/.cursor/mstack/env.md` means the machine is not mapped, so every GPU run, container exec, and PR stops and asks. Give them `/setup-mstack env`. A `not set` optional resource (`kb`, `wavescope`, `refs`) only skips cited notes, the trace annotation loop, and peaks, and `/setup-mstack env` adds it.
- `/verify-gpu-kernel` runs one command on one locked GPU. A kernel library with no `verify-<lib>` skill has no map of what to run per op family. Mention `/create-verification-skill` when the question is about proving a library's ops work.

When the model rule is missing and it matters, ask whether the user wants to pick a model for each role and a reasoning budget now. It matters when the user is new, the question is about setup or cost, or the answer depends on which models run. Ask at most once per chat. If the need is also unclear, ask both questions together. Offer two choices:

- Now: give them `/setup-mstack` to type, and answer their question too.
- Later: answer their question, and add one line saying every role keeps its default model until they run `/setup-mstack`.

## Get set up

1. Install with `/add-plugin mstack` in chat, or from Customize in the sidebar.
2. Run [`/setup-mstack`](../setup-mstack/SKILL.md). It asks for a reasoning budget, maps a model to each role, and writes a rule. Then it maps the machine (hosts, containers, forge, Jira sites, GPU lock) and any local resources you have (repos, skills dir, ticket root, reference docs, and the optional knowledge base and WaveScope) into `~/.cursor/mstack/env.md`. It looks each one up by what it contains and asks only for what it did not find. Both apply to new chats.
3. Start a real task with `/ateam-mode`, a goal, and a check that can pass or fail.

Installing changes nothing until the user invokes a skill. Only `/setup-mstack` loads from the user's words. The [README](../../README.md) and [guide page 1](../../docs/guide/01-setup.md) have the details. Offer to word their first prompt with them, per [`references/prompting.md`](references/prompting.md).

If cost is the worry, say where the tokens go and how to spend fewer. mstack spends extra tokens on subagents and review panels. Rerun `/setup-mstack` and pick a smaller budget or cheaper models. A role set to `auto` or `inherit-parent` runs on the chat's model, which saves tokens when the chat runs on Auto or a cheaper model. A shorter panel list runs fewer subagents, one for each entry. Save `/ateam-mode` for work that needs rigor.

mstack is built for Cursor. Its skills use the Agent Skills format, so other tools can read them. But most workflow skills, including `/ateam-mode`, `/how`, `/why`, and `/teach`, spawn Cursor subagents with per-role models, and Custom Modes and `/loop` are Cursor features, so those parts may not work there.

## Start a task with `/ateam-mode`

`/ateam-mode` matches the task to a playbook, copies the playbook's steps into the todo list, and runs the other skills as the steps need them. A step it skips stays in the list as `skip: <reason>`. A good prompt states the goal and how to tell it's done. It doesn't list skills, because a hand-written sequence tends to drop or reorder steps the playbook would keep. Read [`references/prompting.md`](references/prompting.md) before you help word one. [Guide page 2](../../docs/guide/02-ateam-mode.md) has examples.

Whether `/ateam-mode` stays on depends on how the user starts it:

- Enter on `/ateam-mode` attaches the skill to one message. It stops applying as the chat moves on.
- Option+Enter on Mac or Alt+Enter on Windows, or Use as Mode from the skill entry, makes it a Custom Mode. It stays in context every turn until the user exits the mode, and it stays out of casual turns.
- Cursor's docs list Custom Modes in the Agents Window and the CLI. Elsewhere, start each new task with `/ateam-mode`.

Link [Cursor's skills docs](https://cursor.com/docs/skills) when this comes up. Mid-chat, "new task" makes the mode match a fresh playbook. `/ateam-mode` already uses `ateam-agent` for the subagents its playbook steps spawn. To get the same style from a subagent of your own, spawn it with `subagent_type: "ateam-agent"`.

## Pick a skill

The default answer is `/ateam-mode`, which runs most of the others when its steps need them. Name a skill directly when the user wants more or less of something than the playbook gives. Read the skill before you recommend it, and give one example prompt.

| The user wants to | Skill |
|---|---|
| Do any non-trivial task with rigor | [`/ateam-mode`](../ateam-mode/SKILL.md) |
| Know how code works now, or where new code should live | [`/how`](../how/SKILL.md) |
| Know why code is shaped this way, or where a number came from | [`/why`](../why/SKILL.md) |
| Understand a kernel or a kernel change, explained plainly | [`/teach`](../teach/SKILL.md) |
| Catch up on their own recent work on a topic | [`/recall`](../recall/SKILL.md) |
| Catch up on everything in this chat since their last message, with enough context to decide each action item | [`/ketchup`](../ketchup/SKILL.md) |
| Know what a small diff could break outside itself | [`/blast-radius`](../blast-radius/SKILL.md) |
| Settle types and module shape before code that crosses a function boundary | [`/architect`](../architect/SKILL.md) |
| Get several attempts at one brief, merged into the best one | [`/arena`](../arena/SKILL.md) |
| Run parallel checks over slices, or race workers, as cloud agents | [`/swarm`](../swarm/SKILL.md) |
| Have different models review a diff and try to break it | [`/interrogate`](../interrogate/SKILL.md) |
| Review someone's PR by number or URL, with GPU evidence, and post it after approval | `/ateam-mode review PR 123`, the [PR review](../ateam-mode/playbooks/pr-review.md) playbook |
| Fix a bug test-first when a cheap local test exists | [`/tdd`](../tdd/SKILL.md) |
| Strip comments before review, using a reviewer that didn't write them | [`/no-comments`](../no-comments/SKILL.md) |
| Clean AI tells out of prose | [`/unslop`](../unslop/SKILL.md) |
| Write docs, an RFC, a README, a PR description, or a commit message to a standard | [`/technical-writing`](../technical-writing/SKILL.md) |
| Hear the last reply again without kernel jargon | [`/bro`](../bro/SKILL.md) |
| Give a kernel library a scripted way to prove its ops (correctness, perf, ISA) | [`/create-verification-skill`](../create-verification-skill/SKILL.md) |
| Bring a kernel library's verification skill and its feature map back in line with its tests | [`/maintain-verification-skill`](../maintain-verification-skill/SKILL.md) |
| Start from a Jira ticket key and set up its ticket folder | [`/ticket-init`](../ticket-init/SKILL.md) |
| Run, reproduce, or benchmark a kernel on the real GPU | [`/verify-gpu-kernel`](../verify-gpu-kernel/SKILL.md) |
| Vet a performance number before reporting or acting on it | [`/benchmark-checklist`](../benchmark-checklist/SKILL.md) |
| Find the domain skill for a kernel step: write, optimize, debug, trace, or ship | The port bindings in [`ports.md`](../ateam-mode/references/ports.md) |
| Run a large or cross-cutting change, or one to review after stepping away | [`/figure-it-out`](../figure-it-out/SKILL.md) |
| Keep a decision log during a run, and review it afterward | [`/show-me-your-work`](../show-me-your-work/SKILL.md) |
| Pick a model for each role and a reasoning budget | [`/setup-mstack`](../setup-mstack/SKILL.md) |
| Map the GPU hosts, containers, repo remotes, Jira sites, and optional local resources for this machine | `/setup-mstack env` |
| Turn their own working habits into a personal mode skill | [`/automate-me`](../automate-me/SKILL.md) |
| Turn what a finished task taught into skill edits | [`/reflect`](../reflect/SKILL.md) |
| Stop agents from repeating the same mistakes in this repo | [`/correct`](../correct/SKILL.md) |
| Find their way around mstack | `/ateam-help` |

If a skill directory next to this one is missing from the table, read its frontmatter and route by its description. The `principle-*` directories are covered under principles below.

Close calls:

- `/how` explains what the code does. `/why` explains the reasons. `/teach` runs one or both and explains the result plainly.
- `/arena` gives every worker the same brief and merges the best parts. `/swarm` splits work into slices or a race and returns one report.
- `/architect` implements right after it settles the design. Add "with checkpoint" to review the design before it writes code.
- `/interrogate` reviews a local diff with a model panel. The PR review playbook reviews a PR by number: repo rules and GPU evidence, then the same panel, then a draft the human posts. `/blast-radius` looks for breakage outside the diff and proves the one fact that makes the change safe.
- `/recall` rebuilds context across recent chats. `/ketchup` covers only this chat since the user's last message. Resuming one specific chat or branch is the Session pickup playbook.
- `/figure-it-out` designs one rigorous run. A program of many stacked PRs is a Multi-phase plan, run by an Autopilot playbook. The Autonomous run playbook drives one task to a finish condition.

Not in mstack:

- A UI or browser control skill. mstack ships none. For GPU runs, use `verify-gpu-kernel`.
- `/loop` and `/create-skill` are Cursor built-ins.

## Playbooks and principles

Playbooks are step lists inside `/ateam-mode`, not skills, so they have no slash command. Inside `/ateam-mode`, describing the task picks one, and these phrases name one directly:

- "babysit this pr" or "check on pr 123" runs Babysit. It drives the PR to merge-ready and stops there. It doesn't merge unless the user asks to merge, land, or ship.
- "land the stack" runs Shipping.
- "take over this branch" runs Session pickup.
- "pause safely" runs Pause safely.
- "full autopilot on this queue" runs Autopilot-full. "stack them, don't ship" runs Autopilot-stack.
- "run the eval playbook" runs Eval.
- "reproduce their numbers" or "verify this claim" runs Repro audit.
- "hillclimb this", "climb this metric", or "beat the Triton baseline" runs Kernel hillclimb. A metric that is not a GPU kernel uses its Non-kernel metrics section.
- "will this redesign pay off" or "bound the ceiling before we build" runs Bound probe. It measures a ceiling and gives go, no-go, or re-target.
- "work on PROJ-123" runs Ticket. It starts with `/ticket-init`.

Without `/ateam-mode`, a phrase such as "babysit this pr" can start Cursor's own skill for the same job instead. The Playbooks section of [`ateam-mode`](../ateam-mode/SKILL.md) lists every playbook and when it applies. [Guide page 6](../../docs/guide/06-verify-and-ship.md) covers opening, babysitting, and landing a PR.

mstack has no planning skill. Cursor's Plan Mode works alongside it. For work that spans phases or stacked PRs, asking `/ateam-mode` for a plan runs the [Multi-phase plan playbook](../ateam-mode/playbooks/multi-phase-plan.md), which writes the plan and doesn't implement it. For a design question, the Prototype playbook or `/architect` settles it in code first.

Principles are one-rule skills that `/ateam-mode` reads and cites in its replies. The user rarely invokes one. They steer with the names instead, as in "apply prove it works. show me the real output." Typing `/principle-<name>` still loads one on demand. [Guide page 8](../../docs/guide/08-principles.md) lists them.

## Fix a run that went wrong

| Symptom | Fix |
|---|---|
| The mode stopped applying after a few turns | It was started with Enter. Start it as a Custom Mode, or start each task with `/ateam-mode`. |
| A question got treated as the next step of the last task | Say "new task", or say the turn doesn't need the mode. |
| A new model choice had no effect | The rule from `/setup-mstack` applies to new chats. Start one. |
| Runs cost more than expected | See the cost paragraph under Get set up. |
| A skill didn't load on its own | Only `/setup-mstack` loads from the user's words. The others load when the user types them or when `/ateam-mode` runs them, and it doesn't run every skill. |
| Parallel agents overwrote each other | Give each agent its own worktree, or run them as cloud agents, which each get their own machine. |
| An overnight run moved but finished nothing | `/loop` needs a check that can pass or fail, not a duration. See [guide page 7](../../docs/guide/07-overnight.md). |
| A kernel step stopped because a port's skill is missing or malformed | Run `/setup-mstack env` and read its Skills table. A renamed or removed skill needs a fix in [`ports.md`](../ateam-mode/references/ports.md). |
| The reply claims success from a green build | Ask for the real command, the op test output, or the ISA. That's the prove-it-works principle. |

For a run that drifts, [`references/prompting.md`](references/prompting.md) has one-line steers. [Guide page 10](../../docs/guide/10-recipes-and-pitfalls.md) has more pitfalls and the recipes worth copying.

## Make mstack my own

- [`/automate-me`](../automate-me/SKILL.md) drafts a personal mode skill from the user's own history, to use alongside `/ateam-mode`.
- [`/reflect`](../reflect/SKILL.md) after a session turns its lessons into skill edits the user approves.
- `/ateam-mode write a skill for <workflow>` runs the authoring playbook. The eval playbook tests a skill change blind.
- Fix a misbehaving skill in its own PR, not inside the feature work where it went wrong.

[Guide page 9](../../docs/guide/09-make-it-yours.md) covers each of these.

## Reply

Lead with the answer. Give at most one example prompt in a code block, adapted from [`references/recipes.md`](references/recipes.md) when one fits, then the link to that file. Keep it short unless the user asked for the whole map.
