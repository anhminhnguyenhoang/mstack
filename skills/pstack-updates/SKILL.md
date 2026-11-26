---
name: pstack-updates
description: "Check upstream pstack for commits that mstack has not reviewed, and say which of them touch skills or agents mstack ships. Use for 'check pstack updates', 'what's new upstream', 'sync with pstack', or a recurring check such as /loop 1d /pstack-updates."
---

# pstack updates

**You list the upstream pstack commits after the reviewed one. For each commit that touches a shipped file, you say what changed and whether to port it.**

This skill reports only. It changes no file in mstack.

## Steps

1. Run `python3 <plugin>/scripts/pstack-updates.py`. `<plugin>` is the mstack plugin root, two directories above this SKILL.md. The script fetches upstream and prints a header, a commit table, and the mapped paths of each `review` commit.
2. Read the exit code.
   - `0` and the line `pstack up to date at <sha>`: reply with that line. Stop.
   - `0` with a table: every commit is decided. Reply with the table. Stop.
   - `2`: at least one commit is undecided. This is not an error. Continue.
   - `1`: the script failed. Show the error. Stop.
3. For each undecided `review` commit, read its diff with `git -C <clone> show <sha> -- <upstream paths>`. The clone path is on the second line of the output. Each upstream path is in the parentheses after `from`.
4. Judge each commit. Name the behavior change in one line. Then pick one call, with a reason:
   - `port`: the change fits the mstack file as it stands.
   - `adapt`: the behavior is wanted, but the mstack file differs. Name the difference.
   - `skip`: the change is for a pstack feature that mstack lacks, or for a model default or a doc that mstack does not carry.
   - A diff that only changes version numbers is `skip`, with the reason `version bump only`.
5. Give each `decided` commit the call `decided`, whatever its verdict. Give each other `skip-candidate` commit the call `skip`. Neither needs a diff read. Use the subject as the change for both.

## Reply

Start with the table, one row per commit:

| commit | version | what changed | call | reason |
|---|---|---|---|---|

Then give one line: the next move. Name the `port` or `adapt` commit to take first, or say that nothing needs a port.

A port is a separate change. Do not port in this run. A port follows the process in `UPSTREAM.md` in the mstack repo. Each port commit ends with an `Upstream-Pstack: <sha>` trailer. Then bump the `Reviewed through` row and add a Decisions row. The port goes through the [Opening a PR](../ateam-mode/playbooks/opening-a-pr.md) playbook.

For a daily check, run `/loop 1d /pstack-updates`.
