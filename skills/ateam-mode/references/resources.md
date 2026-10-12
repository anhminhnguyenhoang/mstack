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
| `kb` | A knowledge base. Path, git remote, and which areas exist (`hardware`, `kernel-optimization`, `papers`, `dsl`) | Read before research and before a lever search. Receives a lesson through `kb.capture` | No | `## KB` |
| `refs` | A list of extra reference-doc sources. Each has a name, a path, and topics such as `peaks`, `roofline`, `numerics` | Cited for a peak, a roofline, or a numerics fact | No | `## Refs` |
| `tickets` | The root under which the `<KEY>/` ticket folders live | `<tickets>/<KEY>/` holds the artifacts of ticket work | Yes, for ticket work | `## Tickets` |

The values live only in `~/.cursor/mstack/env.md`. `/setup-mstack env` writes that file (**setup-mstack**, Part B). Cursor's own config paths are not resources. `~/.cursor/mstack/env.md` and `~/.cursor/rules/mstack-*.mdc` stay as they are.

## Rules

- Name a resource by its key, as in "the `kb` resource". Never write a disk path for it in mstack text.
- Resolve the value from `~/.cursor/mstack/env.md` when the step runs. Never from memory or from a default.
- A resource is usable only when its row is present and its value is not `not set`.
- Never guess a path. A path you did not read from the env file does not exist for mstack.
- An optional resource that is missing or `not set`: do the step without it. Write one line in the reply: `skipped <key>: not set`. In ticket work, write the same line in the decision log or in `STATUS.md`.
- Ask once per session, after the skip, whether the user has that resource. Ask in one sentence, and offer `/setup-mstack env` to add it. Do not ask again in the same session.
- A required resource that is missing or `not set`: stop the step. Name the key, and ask the user for the value or for `/setup-mstack env`. A port whose skill is missing is the `skills` case (`ports.md`).
- A resource row can be present and wrong, such as a path that no longer exists. Treat that as missing. Say so, and point at `/setup-mstack env`.

`python3 scripts/check.py` enforces the rules. It fails on a home-directory path, a real ticket key, or a file path inside a `kb` area in mstack text. Only a line that carries the `(probe)` marker in `skills/setup-mstack/SKILL.md` may name a default location, and only as a guess to test. Cursor's own config paths and the upstream `~/Library/Application` line are exempt. With no `skills` directory configured, the check skips the skills checks with a note.

## Reading the `kb` resource

Read in three levels: the root `README.md`, then the `README.md` of the matching area, then the note. Cite the note. Re-derive only what it does not cover. A reference to a file deeper than an area is a leak, because a note can be renamed.

## Reading the `refs` resource

Pick the source whose topics include the topic you need. Cite the source name and the file you read. When no source has the topic, say the peak or fact is stated with its public source.
