# Code Archaeology (git + in-repo)

## What this source contains

- Commit history (messages, dates, authors, diffs)
- PR descriptions, review comments, and discussion threads (via `gh`)
- Inline code comments, TODOs, FIXMEs, deprecation notes
- ADRs (architectural decision records) if the repo keeps them
- Tests, whose names and assertions often encode the edge cases that motivated a change
- Related files modified in the same commits (co-change signal)
- CHANGELOG entries and release notes in the repo
- Issue/ticket IDs in commit messages and PR bodies

The most trustworthy source, tied directly to the code, and the most complete. Everything that went through the repo should be here.

## How to search it

Expand the seed commit list:

```bash
# History through renames
git log --follow --oneline -- <file>

# Pickaxe: commits that added or removed this exact text
git log -S '<exact_string_from_code>' -- <file>

# Or for patterns:
git log -G '<regex>' -- <file>

# Who wrote each line and when
git blame -L <start>,<end> <file>

# One commit's full diff
git show <hash>

# Commits between two points affecting this file
git log <old>..<new> -p -- <file>
```

Look for out-of-band docs:

```bash
# ADRs often live in docs/adr/ or similar
rg -l -i 'architecture.decision' --glob '*.md'

# TODOs and FIXMEs near the target
rg -n -C2 '(TODO|FIXME|HACK|XXX|NOTE)' <target_file>

# Related tests
rg -l '<symbol>' --glob '*test*'
```

Look for kernel-specific records:

```bash
# Constants that encode a decision: tile sizes, thresholds, arch gates
git log -S 'BLOCK_M = 128' -- <file>
git log -G 'gfx9(42|50)' -- <file>

# Tuned config rows: who added a shape and when
git log -p --follow -- <config_csv>

# Dispatch and shape lists in tests
rg -n -C2 '<symbol>|<shape>' --glob '*test*'

# Revert and re-land pairs near the target
git log --oneline -i --grep='revert' -- <file>
```

## What good evidence looks like here

- A comment that states the limit: "256 spills VGPRs past 512".
- A test whose shape list names the edge case: a partial tail tile, an empty group, a varlen batch.
- A commit that adds a guard together with the test that fails without it.
- An arch gate added with a message that names the missing instruction.

## Common pitfalls

- **Rename and move noise.** `git blame -w -C -C` skips whitespace and moved lines. Use it before you trust the last-touch commit.
- **Mass reformat commits.** A format commit owns the line but not the idea. Step past it.
- **Tuned CSV churn.** Tuning commits rewrite many rows at once. Read the diff for the row you care about.
- **Code as its own proof.** A threshold in code shows what the code does. It does not show why. Look for text that states the reason.

For PR discussion, review threads, and issue text, see [`github.md`](./github.md).
