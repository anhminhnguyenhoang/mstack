### Kernel environment

Where kernel work runs. Read this before a GPU run, a container exec, a worktree, a PR, or a Jira read. The **verify-gpu-kernel** skill owns the commands. This file owns the rules.

```
host ──► container ──► repo path ──► test command ──► arch
```

The facts for this machine are not in the plugin. They are in `~/.cursor/mstack/env.md`, which `/setup-mstack env` writes (**setup-mstack**, Part B). That file has the hosts and their SSH aliases, the user's containers and mounts, the forge and the push remote with its scheme (SSH or HTTPS), the Jira site to MCP namespace map, the GPU lock convention, and one table per local resource: `repos`, `skills`, `kb`, `wavescope`, `refs`, and `tickets`. [`resources.md`](resources.md) is the contract for them. A resource is optional unless its row there says it is required.

- The file is missing → stop, and ask the user to run `/setup-mstack env`. An optional resource alone (`kb`, `wavescope`, `refs`) is skipped with a note instead, per `resources.md`.
- A fact you need is `not set` → stop, and ask the user for it or to rerun `/setup-mstack env`. Do not guess a host, a container, or a remote.
- A fact looks stale (a container that no longer exists, a different arch) → run the **verify-gpu-kernel** doctor, then ask the user to rerun `/setup-mstack env`.

A ticket can override the defaults. `<tickets>/<KEY>/.devcontainer/devcontainer.json` names the ticket's container (`--name=` in `runArgs`) and its mount (`workspaceMount`). Prefer it over the env file's default container.

Rules.

- The host has no torch. Run every test and benchmark in the container, never on the bare host.
- A container sees only its bind mounts. A path outside a mount is invisible to it. Make worktrees inside the mount.
- Touch only the user's containers, as listed in the env file. Never `docker exec`, stop, or remove anyone else's.
- Pick, lock, and isolate the GPU per the `bench.run` port (**verify-gpu-kernel**, Lock one idle GPU). A container's default GPU is not necessarily idle.
- Run in the worktree, with `-w <wt>` and `PYTHONPATH` set to it, per **verify-gpu-kernel**. A script in `op_tests/` otherwise imports the installed checkout.
- Check the arch from inside the container (`rocminfo | grep -m1 gfx`) before you trust a number.
- A ticket's scripts, artifacts, and notes live in `<tickets>/<KEY>/`, mounted in its container.
- Pick the Jira MCP namespace from the ticket URL's site, or from the project-prefix map for a bare key, per the env file's Jira table. Pick the GitHub path per its Forge table.
- Resolve the forge, and map `gh` to MCP tools, per [`forge.md`](forge.md).
