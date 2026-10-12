# Set up mstack

In this page you install the plugin, pick which models mstack uses, and run your first task. Setup is one command plus a short conversation.

## Install the plugin

In a Cursor chat, run:

```text
/add-plugin mstack
```

Cursor confirms the plugin is installed.

## Pick your models

Run:

```text
/setup-mstack
```

[`/setup-mstack`](../../skills/setup-mstack/SKILL.md) detects the models you have access to, asks for a reasoning budget, shows you each role (code delegates, judgment, the review panels), and asks what you want. Answer the questions. It writes `~/.cursor/rules/mstack-models.mdc`, a small rule every mstack skill reads.

The defaults run at `xhigh` reasoning, the same as the `large` budget. `unlimited` lifts each model to its highest tier, up to `max`. Opus goes to `max` only if your account lists a `max` slug. Otherwise it stays at the highest tier you have. Sonnet's only tier is `high`, so it stays there. `medium` and `small` lower the reasoning and spend fewer tokens.

You only override what you care about. A role with no line in the rule keeps the skill's default. To restore a default, delete that role's line. A rerun of `/setup-mstack` keeps any role whose model differs from the default. When a default changes, a rule written before the change still pins the old default, so delete those role lines, or delete the file, then run `/setup-mstack` again.

You might be wondering what happens if you use Auto. Set a role to `inherit-parent` or `auto` and mstack omits the subagent `model` field, so the subagent inherits your parent chat model. Both values mean the same thing, and neither is a model slug. For a panel role the value is a list, and one subagent runs per entry, so the list length sets the panel size. Setup also configures `swarm workers`, the default model for every `/swarm` worker unless a race names a model for each arm.

## Map this machine

After the models, `/setup-mstack` maps the machine for kernel work. It detects the GPU arch, your containers and their mounts, the forge you can push and open PRs through, the Jira sites in your MCP config, and the GPU lock picker. It also looks for your local resources: the domain repos, the skills dir, a knowledge base, reference docs, and a ticket root. Then it asks in one form for what it cannot detect: the SSH alias, hosts for other archs, the push remote and default container per repo, the lock convention, and a path for each resource it did not find (give the path, or skip).

Every resource is optional until a step needs it. A step that only benefits from a resource you skipped does its work without it, says so in one line, and asks once per session whether you have it. A step that requires one stops: `repos` for a GPU run, a worktree, or a PR, `skills` for a port, and `tickets` for ticket work. [`resources.md`](../../skills/ateam-mode/references/resources.md) lists the five resources.

It also runs `scripts/check.py --skills-only`. That checks every domain skill the [port bindings](../../skills/ateam-mode/references/ports.md) name: it is installed, its frontmatter is valid, and no installed skill is left unbound. It warns when a linked skill's repo is not on `main`, because the link follows that repo's checked-out branch.

It writes `~/.cursor/mstack/env.md`, outside the plugin, so an update never overwrites it. A fact you skip is `not set`. A skill that needs a required fact stops and asks rather than guessing. Rerun `/setup-mstack env` when a container, a host, or a resource path changes, or when you get a knowledge base or reference docs later.

## Accept the verification offer, or don't

At the end of setup, `/setup-mstack` looks for a way to prove app behavior in your project, either a `verify-*` skill or an existing harness. If it finds neither, it offers once to generate one with [`/create-verification-skill`](../../skills/create-verification-skill/SKILL.md).

Say yes and it writes `.cursor/skills/verify-<app>/`, a project-local skill that teaches agents to drive your app the way a user does. It proves the skill works once before handing it over. Say no and setup moves on. You can run `/create-verification-skill` yourself any time. [Verify and ship](./06-verify-and-ship.md#create-a-project-verification-skill) covers it in depth.

If you're new to mstack, say yes. An agent that can check its own work keeps going until the check passes. An agent that can't hands every result back to you to check by hand. Of everything in this guide, the verification skill pays off the most.

After setup, start a new chat. The model rule applies to new sessions.

## Keep the cost in check

mstack spends extra tokens on subagents and review panels. That's the price of the rigor. To spend fewer:

- Rerun `/setup-mstack` and pick a smaller reasoning budget or cheaper models. A strong model in the main chat with cheaper, faster models in the code roles is a good split.
- Set a role to `auto` or `inherit-parent` so it runs on the chat's own model.
- Shorten a panel list. Each entry runs one subagent.
- Save `/ateam-mode` for work that needs rigor. A small, obvious edit doesn't.

## Run your first task

Pick something real but small, and describe it the way you'd describe it to a colleague:

```text
/ateam-mode add a --json flag to this command. text output stays byte-identical. verify both.
```

Watch the todo list. Its first items are the matched playbook's steps copied in, the Feature playbook for this prompt. If `/ateam-mode` skips a step, the step stays in the list with `skip: <reason>`, so you can see what it chose not to do.

From here you can type normal follow-ups. To keep `/ateam-mode` on for the whole chat, pick it from the `/` menu with Option+Enter (Mac) or Alt+Enter (Windows) instead of Enter. That makes it a [Custom Mode](https://cursor.com/docs/skills), which stays in context on every turn until you exit it. Custom Modes are available in the Agents Window and the CLI. Plain Enter attaches the skill to one message, and it fades as the chat moves on.

Next: [Route work through `/ateam-mode`](./02-ateam-mode.md).
