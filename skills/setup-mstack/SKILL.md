---
name: setup-mstack
description: Configure mstack for this user and this machine. Part A sets the model per role and the reasoning budget. Part B detects the GPU hosts, containers, forge, Jira sites, GPU lock, and the local resources (`repos`, `skills`, `kb`, `refs`, `tickets`), asks for what it cannot detect, and writes the machine-local env file every kernel skill reads. Use for /setup-mstack, /setup-mstack models, /setup-mstack env, "configure mstack", "mstack budget", or when a skill reports that ~/.cursor/mstack/env.md is missing or a fact in it is `not set`, or offers to add a resource.
---

# Setup mstack

Two outputs, both outside the plugin, so a plugin update never overwrites them:

| Part | Writes | Read by |
|---|---|---|
| A. Models | `~/.cursor/rules/mstack-models.mdc` | `ateam-mode` and every routed skill that spawns a subagent |
| B. Environment | `~/.cursor/mstack/env.md` and `~/.cursor/rules/mstack-env.mdc` | `verify-gpu-kernel`, `references/env.md`, `references/ports.md`, Ticket, Deliver, Opening a PR |

`/setup-mstack` runs A, B, then C. `/setup-mstack models` runs A only. `/setup-mstack env` runs B only. A skill that stops on a missing or `not set` env fact sends the user to `/setup-mstack env`.

## Part A. Models

### 1. Detect available models

Enumerate the model slugs you can pass to a `Task` subagent in this session. That is the dependable source. If Cursor also exposes a models API or CLI that lists the user's entitled models, prefer it for completeness. If you cannot detect any, ask the user to paste the slugs they have access to. Never write a real slug you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected slugs.

### 2. Load current state

The default role-to-model mapping is the rule shape shown in step 5 below. If `~/.cursor/rules/mstack-models.mdc` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer AskQuestion over free text. Offer these four options with these exact labels, and name the current budget when the rule records one. With no rule, say that `large` matches the skill defaults.

- `unlimited — max reasoning`
- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by family, list, or alias (`inherit-parent`, `auto`). `unlimited`, `large`, `medium`, and `small` set the effort token of every real slug, panel entries included, to `max`, `xhigh`, `high`, or `medium`. The effort token is the last token, or the one before a trailing `fast`, on the ladder `max` > `xhigh` > `high` > `medium` > `low`. If the result is not a detected slug, use the same family's detected slug with the highest effort at or below the target, else mark the role as needing a choice. `inherit-parent` and `auto` do not change. So `unlimited` turns `claude-opus-5-5-xhigh` into `claude-opus-5-5-max` only if that slug is detected. Otherwise it keeps the highest detected Opus tier. Sonnet's only detected tier is `high`, so every budget at or above `high` keeps `claude-sonnet-5-5-high`. `large` keeps both defaults. `medium` keeps Sonnet and turns Opus into the highest detected slug at or below `high`. `small` turns Opus into the highest detected slug at or below `medium`. With no `medium` slug, that is `claude-opus-5-5-low`. Sonnet has no lower tier, so it stays at `claude-sonnet-5-5-high`.

**(c) Show the roles and confirm.** Show every role with its model, marking any real slug not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model, which is how Auto users stay on Auto) as the options. Prefer AskQuestion over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every real slug written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real slug is not available, stop and ask again.

### 5. Write the rule

Write `~/.cursor/rules/mstack-models.mdc` with `alwaysApply: true`, a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels ateam-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:

```
---
description: mstack per-role model choices (overrides skill defaults)
alwaysApply: true
---
# mstack model configuration. One line per role. Delete a line to fall back to the skill default.
# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit Task `model`). Alias entries in a panel list still count toward its fan-out.
# budget: large (xhigh)
feature, refactoring: claude-sonnet-5-5-high
bug-fix: claude-sonnet-5-5-high
perf-issue: claude-sonnet-5-5-high
hillclimb: claude-sonnet-5-5-high
judgment and prose: claude-opus-5-5-xhigh
hardest tasks: claude-opus-5-5-xhigh
how explorer: claude-sonnet-5-5-high
how explainer: claude-opus-5-5-xhigh
why investigators: claude-sonnet-5-5-high
why synthesizer: claude-opus-5-5-xhigh
reflect tooling: claude-sonnet-5-5-high
reflect judgment, divergent, synthesizer: claude-opus-5-5-xhigh
arena runners: claude-opus-5-5-xhigh, claude-sonnet-5-5-high
arena cross-judge pool: claude-opus-5-5-xhigh, claude-sonnet-5-5-high
swarm workers: claude-sonnet-5-5-high
architect runners: claude-opus-5-5-xhigh, claude-sonnet-5-5-high
interrogate reviewers: claude-opus-5-5-xhigh, claude-sonnet-5-5-high
```

### 6. Confirm

Tell the user the rule was written and that it applies to new sessions. Re-running this skill updates it.

## Part B. Environment

Machine facts live in `~/.cursor/mstack/env.md`, never in the plugin. The plugin's [`references/env.md`](../ateam-mode/references/env.md) holds only the schema and the rules. [`references/resources.md`](../ateam-mode/references/resources.md) is the contract for the five resources: `repos`, `skills`, `kb`, `refs`, and `tickets`. A resource is optional on a machine until a step requires it. Every command in this part is read-only. Never `docker exec`, start, stop, or remove a container here, and never write a token or secret into the file.

### 7. Load current state

If `~/.cursor/mstack/env.md` exists, read it. A fact marked `user` is the user's answer. Keep it unless detection now contradicts it, and then show both values and ask. A fact marked `detected` is refreshed by step 8.

### 8. Detect

Run these and keep the raw output for step 10. A command that fails or is missing is a fact too. Record it as `absent`.

A row that carries the marker `(probe)` names a default location to look in. It is a guess to test, never a fact. Record a path only after the test passes and, for a probe, only after the user confirms it in step 9. Run the Tickets row before the rows that read the ticket folders.

| Fact | Command |
|---|---|
| Host name | `hostname` |
| GPUs and arch | `rocminfo \| grep -o 'gfx[0-9a-f]*' \| sort \| uniq -c`, `rocm-smi --showproductname` |
| Host ROCm | `readlink -f /opt/rocm` |
| Host torch | `python3 -c 'import torch'` (expected `absent`: runs go in a container) |
| The user's containers | `docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}'`, then `docker inspect --format '{{.Name}} {{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}' <name>`. Keep only containers with a mount under `$HOME`. Every other container belongs to someone else. List it nowhere |
| Tickets | Probe `~/*/ticket-raw.md` (probe). The common parent of the folders that hold a `ticket-raw.md` is the root candidate |
| Ticket containers | `<tickets>/*/.devcontainer/devcontainer.json`: the `--name=` entry in `runArgs`, and `workspaceMount`. Skipped when `tickets` is not found |
| Repos | Probe `~/aiter`, `~/FlyDSL`, and `~/triton` (probe). For each that exists: `git -C <path> remote -v` and the current branch |
| Forge | `gh auth status`, `timeout 15 ssh -o BatchMode=yes -T git@github.com`, `command -v origin`, and `get_me` on each GitHub MCP namespace in the session. Per host or org, push path is the SSH remote that works. PR path is `gh` only if `gh auth status` succeeds, `origin` only if it resolves the repo, else the MCP namespace whose sign-in covers that host or org. Resolution order is in [`references/forge.md`](../ateam-mode/references/forge.md) |
| Jira sites | The `JIRA_URL` of each server in `~/.cursor/mcp.json`, and each remote Atlassian MCP namespace in the session. Seed project prefixes from the URL and `**Site:**` lines in `<tickets>/*/ticket-raw.md`: the key prefix maps to that site |
| GPU picker | `test -f <skills>/<pr.validate skill>/pick-idle-gpu.py`. `<skills>` is the directory of the `skills` resource, and `<pr.validate skill>` is the skill that `ports.md` binds to `pr.validate`. Skipped when `skills` is not found |
| `kb` | Probe `~/knowledge-base/README.md` (probe). Record the path, the git remote (`git -C <path> remote get-url origin`), and whether all four areas exist (`test -f <path>/<area>/README.md` for `hardware`, `kernel-optimization`, `papers`, `dsl`). A missing area is `not set` |
| `skills` | The directory is `$MSTACK_SKILLS_DIR` when set, else probe `~/.claude/skills` (probe). Then run `MSTACK_SKILLS_DIR=<dir> python3 <plugin>/scripts/check.py --skills-only`, where `<plugin>` is the mstack plugin root, two directories above this SKILL.md. It resolves every binding in [`references/ports.md`](../ateam-mode/references/ports.md), checks each bound skill's frontmatter, names each installed skill that no port binds, and prints the Skills table. A symlinked skill's row carries its repo and checked-out branch. Exit 1 means at least one row is not `ok`. Record the rows either way. No skills dir: record the section as `not set` |
| `refs` | Probe for markdown files whose names contain `roofline`, `peak`, or `numerics` under the `docs/` of each repo in `repos` (probe). Each hit is a candidate source. The user confirms its name and topics in step 9. No hit: `not set` |

### 9. Ask what detection cannot settle

Ask once, in one AskQuestion form. Offer the detected values as options, plus `none` or `skip` where it applies. Ask only what is unknown or contradicted:

- The SSH alias or aliases for this host, as other machines reach it.
- Other GPU hosts, one per arch not present here (for example `gfx942` when this host is `gfx950`). For each: SSH alias, default container, and repo path. `none` is a valid answer.
- For each repo: the remote to push branches to, and the upstream PRs target.
- For each repo: the default container and its mount path, when no ticket names one.
- The GPU lock convention. The default is `flock /tmp/gpu-<id>.lock` with the picker that the `pr.validate` port's skill ships. Offer `team convention` as free text.
- For each resource that detection did not find or confirm (`repos`, `skills`, `kb`, `refs`, `tickets`), ask in this same form, with the same wording: "Do you have a knowledge base / reference docs / a ticket root / a skills dir? Give the path, or skip." For `refs`, ask for a name, a path, and topics (`peaks`, `roofline`, `numerics`) per source. Allow more than one source. Check that each path the user gives exists. For `kb`, check for a `README.md` at its root. Ask again for a path that fails, or record `not set`.
- The Jira MCP namespace for each site it cannot map, and the project prefixes for each site it has no ticket for. A prefix maps to exactly one site.
- The PR path for each GitHub host or org (`gh`, `origin`, or an MCP namespace name), when detection finds none or more than one. The push path is the SSH remote, asked only when SSH detection fails.

A fact or a resource the user skips is written as `not set`. A skill that needs a `not set` required fact stops and asks. A step that wants a `not set` optional resource skips it with a note (`references/resources.md`). Nothing ever guesses.

### 10. Write the env file

Overwrite `~/.cursor/mstack/env.md` in full, so a rerun stays idempotent. Every row ends with its source: `detected <date>` or `user <date>`. Use this shape:

```
# mstack environment (machine-local, written by /setup-mstack env)

## Hosts
| Host | SSH alias | Arch | GPUs | Host ROCm | Host torch | Source |

## Containers
| Container | Image | Status | Mounts (host:container) | Use | Source |

## Repos
| Repo | Path | Push remote | PR target | Default container | Path in container | Source |

## Forge
| Host or org | Push path (SSH remote) | PR path (`gh`, `origin`, or MCP namespace) | Source |

## Jira
| Site | MCP namespace | Project prefixes | Source |

## GPU lock
| Picker | Lock | Source |

## KB
| Path | Remote | Areas | Source |

## Refs
| Name | Path | Topics | Source |

## Tickets
| Root | Source |

## Skills
| Dir | Source |

| Port | Skill | Status | Repo | Branch | Warning | Source |
```

Each resource has a section named for its key: Repos, Skills, KB, Refs, and Tickets. A resource the user skipped gets one row with `not set` in each value cell. Repos has one row per repo, and Refs has one row per source. `Areas` in KB lists the areas that exist. The Dir row of Skills holds the `skills` directory, and `scripts/check.py` reads that row when `$MSTACK_SKILLS_DIR` is unset. The port rows of Skills are the rows `check.py --skills-only` prints, plus the Source column. Status is `ok`, `missing`, `malformed`, or `unbound`. Repo is `mstack` for mstack's own skill, `local` for a plain directory, and the repo root for a symlinked skill. A symlink follows its repo's checked-out branch, so a repo that is not on `main` gets a warning.

The GPU lock row holds commands, not paths. The Picker cell is the full picker command line, which prints one HIP index, as the GPU claim stage of `validate-kernel-pr` runs it. The Lock cell is the lock prefix with `<id>` for that index, such as `flock /tmp/gpu-<id>.lock`. **verify-gpu-kernel** runs both cells as written.

Then write `~/.cursor/rules/mstack-env.mdc`, overwriting it in full:

```
---
description: mstack machine facts
alwaysApply: true
---
mstack machine facts (hosts, containers, forge, Jira sites, GPU lock) and local resources (repos, skills, kb, refs, tickets) are in ~/.cursor/mstack/env.md. Read it before a GPU run, a container exec, a PR, or a Jira read. A missing file or a `not set` required fact means: stop and ask the user to run /setup-mstack env. A `not set` optional resource (kb, refs) means: skip it, write one line, and ask once per session whether the user has it.
```

### 11. Report

Show the env file as a short table per section. List each fact that is `not set`, and which skill stops on it. List each resource that is `not set` and what skipping it costs: `kb` and `refs` lose cited notes and peaks, `tickets` stops ticket work, `repos` stops GPU runs and PRs, `skills` stops every port. List each Skills row that is not `ok` or has a warning, and the port it breaks. Show what changed since the last run.

## Part C. Verification

### 12. Offer a verification skill (optional)

GPU kernels already have **verify-gpu-kernel**. Skip this step when the project's surface is a kernel or a kernel script. For any other surface, check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever mstack is installed: workspace, user, or plugin). On no, move on without pushing.
