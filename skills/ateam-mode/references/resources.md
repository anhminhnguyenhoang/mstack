# Resources

A resource is a thing on one user's disk that another user may not have. mstack works on any machine, so it names each resource by a key and never by a path.

```
step wants a resource
   │
   ▼
env.md row present and not `not set`?
   │ yes                         │ no
   ▼                             ▼
use it                  required?  ──yes──► stop, ask for `/setup-mstack env`
                           │ no
                           ▼
                  do the step without it
                  write one line: skipped
                  ask once per session
```

## Keys

| Key | What it is | How a step uses it | Required | Value lives in |
|---|---|---|---|---|
| `repos` | The domain git repos (aiter, FlyDSL, triton). Per repo: path, push remote, PR target, container, path in container | GPU runs, worktrees, PRs, SHA records | Yes, for a GPU run, a worktree, or a PR | `## Repos` |
| `skills` | The directory of domain skills that the ports bind. `$MSTACK_SKILLS_DIR` overrides it | Every step that names a port (`ports.md`) | Yes, for a port | `## Skills` |
| `kb` | A knowledge base the user points to. Root, index file, remote if any, and a map from roles to folders inside it (KB roles) | Read by role before research and before a lever search. Receives a lesson through `kb.capture` | No | `## KB` |
| `wavescope` | A WaveScope checkout. Path, and whether its CLI runs | The human verifies trace findings in it, and replies in `notes.json` (`trace.annotate`). Its capture profiles serve `trace.capture` | No | `## WaveScope` |
| `refs` | A list of extra reference-doc sources. Each has a name, a path, and topics such as `peaks`, `roofline`, `numerics` | Cited for a peak, a roofline, or a numerics fact | No | `## Refs` |
| `tickets` | The root under which the `<KEY>/` ticket folders live | `<tickets>/<KEY>/` holds the artifacts of ticket work | Yes, for ticket work | `## Tickets` |

The values live only in `~/.cursor/mstack/env.md`. `/setup-mstack env` writes that file (**setup-mstack**, Part B). Cursor's own config paths are not resources. `~/.cursor/mstack/env.md` and `~/.cursor/rules/mstack-*.mdc` stay as they are.

## Rules

- Name a resource by its key, as in "the `kb` resource". Never write a disk path for it in mstack text.
- Name KB content by role, as in "the `levers` role of the `kb` resource". Never write a folder of the KB in mstack text.
- Resolve the value from `~/.cursor/mstack/env.md` when the step runs. Never from memory or from a default.
- A resource is usable only when its row is present and its value is not `not set`.
- Never guess a path. A path you did not read from the env file does not exist for mstack.
- An optional resource that is missing or `not set`: do the step without it. Write one line in the reply: `skipped <key>: not set`. In ticket work, write the same line in the decision log or in `STATUS.md`.
- Ask once per session, after the skip, whether the user has that resource. Ask in one sentence, and offer `/setup-mstack env` to add it. Do not ask again in the same session.
- A required resource that is missing or `not set`: stop the step. Name the key, and ask the user for the value or for `/setup-mstack env`. A port whose skill is missing is the `skills` case (`ports.md`).
- A resource row can be present and wrong, such as a path that no longer exists. Treat that as missing. Say so, and point at `/setup-mstack env`.

`python3 scripts/check.py` enforces the rules. It fails on a home-directory path, a real ticket key, or a folder of the `kb` resource in mstack text. That covers the legacy folder names, a path token in a sentence that names the `kb` resource, and any path that the KB role table of the env file records. Only a line that carries the `(probe)` marker in `skills/setup-mstack/SKILL.md` may name a default location, and only as a guess to test. Cursor's own config paths and the upstream `~/Library/Application` line are exempt. With no `skills` directory configured, the check skips the skills checks with a note.

## KB roles

No two knowledge bases share one layout. mstack never assumes a folder name, a root name, or a location. It asks for a role, and the env file maps that role to a folder.

| Role | What it holds |
|---|---|
| `hardware` | Chip facts and peaks |
| `method` | Measurement, diagnosis, and the optimization loop |
| `levers` | One note per optimization lever |
| `failure-modes` | Dead ends and decision heuristics |
| `papers` | Papers |
| `dsl` | DSL-specific notes |

```
user's KB                      env file, ## KB              mstack text
├─ folder A      ──setup──►    levers  → <path in KB>  ◄──  "the `levers` role
├─ folder B/sub  maps roles    hardware → <path in KB>       of the `kb` resource"
└─ README        (user         papers  → not set
   (index file)   confirms)
```

- A role maps to a folder or a subfolder.
- Several roles may share one folder.
- A role with no match is `not set`.
- A role that is `not set` is skipped with one line: `skipped kb <role>: not set`. Ask once per session whether the user has that part of a KB. Offer `/setup-mstack env`.
- The env file records the root, the index file, the remote if any, and one row per role (**setup-mstack**, Part B).

## Reading the `kb` resource

Read a role in three levels.

```
index file of the KB ──► index of the role's folder ──► note
 (env file names it)                                    cite this
```

Cite the note. Re-derive only what it does not cover. Pick the role that fits the topic. A reference to a file deeper than the role's folder index is a leak, because a note can be renamed.

## Reading the `wavescope` resource

The `wavescope` resource is usable when its row is present, its path exists, and its CLI runs. The check is `node <path>/src/cli/att.js` with no arguments. Setup asks for the path and detects nothing by name.

When `wavescope` is not set, or the `trace.annotate` skill is missing, every WaveScope step changes in one way:

- Deliver the trace findings in the reply or the ticket folder.
- Skip the `notes.json` loop.
- Write `skipped wavescope: not set`.
- Ask once per session whether the user uses WaveScope.

## Reading the `refs` resource

Pick the source whose topics include the topic you need. Cite the source name and the file you read. When no source has the topic, say the peak or fact is stated with its public source.
