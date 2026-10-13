---
name: setup-mstack
description: Configure mstack for this user and this machine. Part A sets the model per role and the reasoning budget. Part B detects the GPU hosts, containers, forge, Jira sites, and GPU lock, asks the user for each local resource (`repos`, `skills`, `refs`, `tickets`) and each optional module (`kb`, `wavescope`) instead of guessing names or locations, maps the knowledge base's folders to roles, and writes the machine-local env file every kernel skill reads. Use for /setup-mstack, /setup-mstack models, /setup-mstack env, "configure mstack", "mstack budget", or when a skill reports that ~/.cursor/mstack/env.md is missing or a fact in it is `not set`, or offers to add a resource.
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

Machine facts live in `~/.cursor/mstack/env.md`, never in the plugin. The plugin's [`references/env.md`](../ateam-mode/references/env.md) holds only the schema and the rules. [`references/resources.md`](../ateam-mode/references/resources.md) is the contract for the six resources: `repos`, `skills`, `kb`, `wavescope`, `refs`, and `tickets`. A resource is optional on a machine until a step requires it. Every command in this part is read-only. Never `docker exec`, start, stop, or remove a container here, and never write a token or secret into the file.

### 7. Load current state

If `~/.cursor/mstack/env.md` exists, read it. A fact marked `user` is the user's answer. Keep it unless detection now contradicts it, and then show both values and ask. A fact marked `detected` is refreshed by step 8. A resource value that no longer passes its check is treated as not found.

### 8. Detect

Run these and keep the raw output for step 10. A command that fails or is missing is a fact too. Record it as `absent`.

Look it up before you ask. Run `python3 <plugin>/scripts/find-resources.py`, where `<plugin>` is the mstack plugin root, two directories above this SKILL.md. It finds each local resource by what it contains, never by its name or location. It prints each resource as `found`, `ambiguous`, or `not found`, with the signature that matched. `--json` prints the same data.

Search policy.

- Read-only. Never write, never run a repo's code. The one exception is the WaveScope CLI check.
- Bounded. Search only the user's home, to depth 4, with a time limit per search (`--time-limit`). A search that hits the limit says so, and the resource is asked in step 9.
- Skip `.git` internals, `node_modules`, caches, build outputs, linked git worktrees (a `.git` file, not a directory), and every path outside the user's home. Do not follow a symlink out of it.
- Read only what identifies a thing: remote URLs, index files, frontmatter, and file names under a candidate. Read a file body only for `refs`.

A row that carries the marker `(probe)` names a conventional tool location, such as a folder Cursor loads skills from. It is a guess to test, never a fact. Record a path only after the test passes. Run the Tickets row before the rows that read the ticket folders.

| Fact | Command |
|---|---|
| Host name | `hostname` |
| GPUs and arch | `rocminfo \| grep -o 'gfx[0-9a-f]*' \| sort \| uniq -c`, `rocm-smi --showproductname` |
| Host ROCm | `readlink -f /opt/rocm` |
| Host torch | `python3 -c 'import torch'` (expected `absent`: runs go in a container) |
| The user's containers | `docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}'`, then `docker inspect --format '{{.Name}} {{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}' <name>`. Keep only containers with a mount under `$HOME`. Every other container belongs to someone else. List it nowhere |
| Tickets | The finder: folders that hold `ticket-raw.md`, `ticket-description.md`, or `ticket-description.txt`. The last two names are a load from before mstack. The root is the common parent of those folders. Folders under several parents: `ambiguous`. None: `not found` |
| Ticket containers | `<tickets>/*/.devcontainer/devcontainer.json`: the `--name=` entry in `runArgs`, and `workspaceMount`. Skipped when `tickets` is `not set` |
| Repos | The finder: a git checkout, a `.git` directory, whose remote URL ends in `ROCm/aiter`, `ROCm/FlyDSL`, or `triton-lang/triton`, with or without `.git`. The folder name does not count. Several checkouts of one repo: `ambiguous`. For each repo path, confirmed or given: `git -C <path> remote -v`, the current branch, and for each remote its push URL (`git -C <path> remote get-url --push <remote>`). Record the scheme of that URL: `ssh` for `git@host:` and `ssh://`, `https` for `https://`. Never assume `ssh`. Never change a remote's URL. None: `not found` |
| Forge | `gh auth status`, and `get_me` on each GitHub MCP namespace in the session. Per push remote, test push reachability read-only for its scheme. All schemes: `GIT_TERMINAL_PROMPT=0 timeout 15 git -C <path> ls-remote --heads <remote>`, so it never waits on a credential prompt. `ssh` only: `timeout 15 ssh -o BatchMode=yes -T git@<host>`. `https` only: note which credential path answers, a helper from `git config --get-all credential.helper` or `gh` when `gh auth status` succeeds. A public repo answers `ls-remote` without credentials, so `ls-remote` alone does not prove push for `https`: record `no helper` when no credential path exists. Never read, print, or store a token, and never put one in a URL. Per host or org, the push remote is the remote and scheme that pass. PR path is `gh` when `gh auth status` succeeds, or the MCP namespace whose sign-in covers that host or org. The order of use is in [`references/forge.md`](../ateam-mode/references/forge.md) |
| Jira sites | The `JIRA_URL` of each server in `~/.cursor/mcp.json`, and each remote Atlassian MCP namespace in the session. Seed project prefixes from the URL and `**Site:**` lines in `<tickets>/*/ticket-raw.md`: the key prefix maps to that site |
| GPU picker | `test -f <skills>/<pr.validate skill>/pick-idle-gpu.py`. `<skills>` is the directory of the `skills` resource, and `<pr.validate skill>` is the skill that `ports.md` binds to `pr.validate`. Skipped when `skills` is `not found` |
| `kb` | The finder: a directory whose root index file, whatever it is called, links to subfolders that have their own index files, with notes that carry YAML frontmatter (`name`, `description`). It excludes skills dirs and the detected repos. Several: `ambiguous`. None: `not found`. The finder also reads the git remote and proposes the role map (see Map the knowledge base) |
| `wavescope` | The finder: a git checkout whose remote URL ends in `/WaveScope`, or a directory that holds `src/cli/att.js`. Then `node <path>/src/cli/att.js` with no arguments: `runs` when it prints usage, `does not run` when it fails or `node` is absent. Several: `ambiguous`. None: `not found` |
| `skills` | `$MSTACK_SKILLS_DIR` when set. Else the folders Cursor loads user skills from, `~/.claude/skills` and `~/.cursor/skills` (probe), whichever hold `*/SKILL.md` with valid frontmatter. The one that resolves the most bindings in [`references/ports.md`](../ateam-mode/references/ports.md) wins. A tie: `ambiguous`. Then run `MSTACK_SKILLS_DIR=<dir> python3 <plugin>/scripts/check.py --skills-only`. It resolves every binding, checks each bound skill's frontmatter, names each installed skill that no port binds, and prints the Skills table. A symlinked skill's row carries its repo and checked-out branch. Exit 1 means at least one row is not `ok`. Record the rows either way. None: `not found` |
| `refs` | The finder: markdown under the `docs` folder of each detected repo, and under the detected KB, that mentions peaks (`TB/s`, `TFLOPS`, `peak`), roofline, or numerics at least twice. Each hit is a proposed source with those topics. None: `not found` |

### 9. Ask what detection cannot settle

Look it up first, and ask the human only when you cannot find it. Step 8 already looked. Ask only for a resource that was `not found`, is `ambiguous`, or failed its check. A `found` resource is not asked. It is reported in step 11, and the user corrects it by rerunning `/setup-mstack env`.

Ask once, in one AskQuestion form. Offer the detected values as options, plus `none` or `skip` where it applies. Never guess a name or a location. Ask only what is unknown or contradicted:

- The SSH alias or aliases for this host, as other machines reach it.
- A required resource that was `not found`, as a path or `skip`:
  - `repos`: the checkout path of each repo the user works in, for GPU runs and PRs.
  - `skills`: the skills dir, for ports. `$MSTACK_SKILLS_DIR` also sets it.
  - `tickets`: the ticket root, for ticket work.
- An `ambiguous` resource: show the candidates and let the user pick one, or say none. That covers several checkouts of one repo, several skills dirs that tie, several knowledge bases, several WaveScope checkouts, and ticket folders under several parents.
- An optional module that was `not found`, once, and it may be skipped. Ask in this same form: "Do you have a knowledge base? Where?", "Do you use WaveScope? Where is its checkout?", and "Do you have reference docs? Where?". For `refs`, ask for a name, a path, and topics (`peaks`, `roofline`, `numerics`) per source, and allow more than one source. mstack works without any of them.
- A value that failed its check: a path that is not a git checkout (`git -C <path> rev-parse --show-toplevel`), a path that does not exist, or a WaveScope CLI that does not run. Show the failing test. Ask again, or record `not set`.
- A search that hit its time limit. Ask for the path directly.
- Other GPU hosts, one per arch not present here (for example `gfx942` when this host is `gfx950`). For each: SSH alias, default container, and repo path. `none` is a valid answer.
- For each confirmed repo: the remote to push branches to (name and scheme), and the upstream PRs target.
- For each repo: the default container and its mount path, when no ticket names one.
- The GPU lock convention. The default is `flock /tmp/gpu-<id>.lock` with the picker that the `pr.validate` port's skill ships. Offer `team convention` as free text.
- The Jira MCP namespace for each site it cannot map, and the project prefixes for each site it has no ticket for. A prefix maps to exactly one site.
- The PR path for each GitHub host or org (`gh` or an MCP namespace name), when detection finds none or more than one. The push remote is asked only when its reachability test fails or an `https` remote has no credential path. Show the remote URL without any credential, the scheme, and the failing test. Never offer to switch the scheme.

When the user gives a path, run the same signature test on it. A path that fails the test is asked again.

**Map the knowledge base.** Run this once the root is found or given. A knowledge base has its own layout, so map it before you record anything.

```
root found ──► read root index and each folder index ──► score each role per folder
                         (read-only)                                  │
                                                one folder clearly ◄──┴──► several or none
                                                    │                          │
                                              map it, no ask             ask the user
```

1. The finder lists the top-level folders. It reads the root index file and the index of each folder, and scores each role in [`references/resources.md`](../ateam-mode/references/resources.md) against that text.
2. A role that one folder clearly matches is mapped without a question. A role may map to a subfolder. Several roles may share one folder.
3. A role that matches several folders, or none, is asked in the same form, with the candidates as options. A role with no match that the user does not supply is `not set`.
4. Do not rename or require any folder.
5. Record the root, the index file, and the git remote if any, with the map, in step 10. The report in step 11 shows the map, so the user can change any role.

A fact or a resource the user skips is written as `not set`. A skill that needs a `not set` required fact stops and asks. A step that wants a `not set` optional resource skips it with a note (`references/resources.md`). Nothing ever guesses.

### 10. Write the env file

Overwrite `~/.cursor/mstack/env.md` in full, so a rerun stays idempotent. Every row ends with its source: `detected <date>` or `user <date>`. A detected resource records the signature that matched, as in `detected <date>, remote ROCm/aiter`. Use this shape:

```
# mstack environment (machine-local, written by /setup-mstack env)

## Hosts
| Host | SSH alias | Arch | GPUs | Host ROCm | Host torch | Source |

## Containers
| Container | Image | Status | Mounts (host:container) | Use | Source |

## Repos
| Repo | Path | Push remote (name, scheme) | PR target | Default container | Path in container | Source |

## Forge
| Host or org | Push remote (name, scheme) | PR path (`gh` or MCP namespace) | Source |

## Jira
| Site | MCP namespace | Project prefixes | Source |

## GPU lock
| Picker | Lock | Source |

## KB
| Root | Index file | Remote | Source |

| Role | Path inside the KB | Source |

## WaveScope
| Path | CLI runs | Source |

## Refs
| Name | Path | Topics | Source |

## Tickets
| Root | Source |

## Skills
| Dir | Source |

| Port | Skill | Status | Repo | Branch | Warning | Source |
```

Each resource has a section named for its key: Repos, Skills, KB, WaveScope, Refs, and Tickets. A resource the user skipped gets one row with `not set` in each value cell. Repos has one row per repo, and Refs has one row per source. KB has one row for the root, the index file, and the remote if any, then one row per role: `hardware`, `method`, `levers`, `failure-modes`, `papers`, `dsl`. Path inside the KB is relative to the root. A role with no folder is `not set`. A skipped KB has `not set` in the root row and in every role row. WaveScope has one row. CLI runs is `runs` or `does not run`. The Dir row of Skills holds the `skills` directory, and `scripts/check.py` reads that row when `$MSTACK_SKILLS_DIR` is unset. The port rows of Skills are the rows `check.py --skills-only` prints, plus the Source column. Status is `ok`, `missing`, `malformed`, or `unbound`. Repo is `mstack` for mstack's own skill, `local` for a plain directory, and the repo root for a symlinked skill. A symlink follows its repo's checked-out branch, so a repo that is not on `main` gets a warning.

The GPU lock row holds commands, not paths. The Picker cell is the full picker command line, which prints one HIP index, as the GPU claim stage of `validate-kernel-pr` runs it. The Lock cell is the lock prefix with `<id>` for that index, such as `flock /tmp/gpu-<id>.lock`. **verify-gpu-kernel** runs both cells as written.

Then write `~/.cursor/rules/mstack-env.mdc`, overwriting it in full:

```
---
description: mstack machine facts
alwaysApply: true
---
mstack machine facts (hosts, containers, forge, Jira sites, GPU lock) and local resources (repos, skills, kb, wavescope, refs, tickets) are in ~/.cursor/mstack/env.md. Read it before a GPU run, a container exec, a PR, or a Jira read. A missing file or a `not set` required fact means: stop and ask the user to run /setup-mstack env. A `not set` optional resource (kb, wavescope, refs) means: skip it, write one line, and ask once per session whether the user has it. A KB role that is `not set` is skipped the same way.
```

### 11. Report

List every resource with its value and how it was identified, so the user can correct any of them by rerunning `/setup-mstack env`. Use one table.

```
| Resource | Value | Identified by |
```

The `Identified by` cell is the signature that matched and `detected <date>`, or `user <date>` for a path the user gave, or `not set`. Show the KB role map under the table. Then show the env file as a short table per section. List each fact that is `not set`, and which skill stops on it. List each resource that is `not set` and what skipping it costs: `kb` and `refs` lose cited notes and peaks, `kb` also loses `kb.capture`, `wavescope` loses the annotation loop (trace findings go in the reply or the ticket folder), a KB role that is `not set` loses its notes only, `tickets` stops ticket work, `repos` stops GPU runs and PRs, `skills` stops every port. List each Skills row that is not `ok` or has a warning, and the port it breaks. Show what changed since the last run.

## Part C. Verification

### 12. Offer a verification skill (optional)

**verify-gpu-kernel** runs one command on one locked GPU. For each repo in the `repos` resource, check whether it has a `verify-<lib>` skill that maps its op families to correctness, perf, and ISA checks. If not, offer once: "want a repo-local verification skill for <lib>, so agents know what to run per op family and can prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever mstack is installed: workspace, user, or plugin). On no, move on without pushing.
