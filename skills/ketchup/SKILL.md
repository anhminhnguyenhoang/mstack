---
name: ketchup
description: "Catch the user up on what changed in this chat since their last message, in plain words and small visuals. List every item waiting on them with what they need to decide it from the reply alone. Use for /ketchup."
disable-model-invocation: true
---

# Ketchup

Catch the user up on what changed in this chat since the last message they wrote before `/ketchup`, and help them understand each change, not only where it stands. Then lay out every call waiting on them so they can make it from your reply alone. Notifications and subagent results are not their messages. Assume the user remembers their last message and nothing after it. The Writing the reply section of the **ateam-mode** skill still holds. Where it and this skill differ, this skill decides.

Use [`/bro`](../bro/SKILL.md)'s voice, not its task: plain words, short sentences, like one person catching up another. Kernel terms the user works with every day, such as MFMA, LDS, VGPR, spill, occupancy, and ATT, are plain words here. Say what changed for the user, not how you did it. Say "the tests pass", not "CI is green". Leave out hashes, file paths, commands, and build numbers unless a call binds to one, such as a verdict at one head SHA or a draft for one Jira key. Call each PR, ticket, branch, or agent by a name the user would know, not by a label you invented. If a fact needs context to make sense, give the context or leave the fact out.

A perf number that a result or a call rests on keeps its full measurement line: number, unit, run count, range, and percent of peak with the peak's source, per the **explain-the-number** principle skill. Leave out the numbers that no call rests on.

## Gather what changed

Keep this turn read-only. Make visuals only from what you already have: do not change code, start a GPU run or a job, or post anything. Collect your own work since that message, reports from subagents, and messages from anyone else in this chat. Check the current state of each PR, CI run, GPU run, ticket, or agent this chat touched. Check each number you will show against the artifact it comes from, and say so when you correct one.

An action item is a call or step only the user can take, such as a design choice, an approval, an irreversible action, or access you lack. The Always-pause items in the Autonomy section of the **ateam-mode** skill are the usual ones: a Jira write, a PR on a public upstream, marking a PR ready, a fork PR's code on a shared GPU, and text that names a customer or an NDA model. For a Jira write, show the drafted text. Include any item still waiting on the user, even one raised before their last message. Work you can still do yourself is not an action item. Never make up a call to fill the reply. A step the user did not ask for and the work does not need is not an action item, unless it is irreversible and waiting on the user: give it one line and no visual.

One call can cover many items, such as each PR in a set awaiting merge. For each item, collect its link, what it changes for the kernel's users, the evidence behind your pick, its risk, and your pick. Write "unknown" for a fact the call needs that you do not know. Leave out a link you do not have.

## Write the reply

Spend words on the calls, not on the story. Keep what happened under 100 words, not counting pictures, and shorter when less happened. Leave out work that changed nothing for the user. Give each item about 30 words. The reply grows with the number of items: two items need well under 150 words in all, not counting pictures, and thirty need far more. Never cut items or shrink them to stay under a word count: no count in place of a list, and no link in place of an item. A link can add depth, but the reply alone must be enough to decide.

Open with one short sentence that names what waits on the user, or says nothing does. The action items give the detail. If nothing happened and nothing waits on the user, say so and stop.

Then show what happened, pictures first. Embed inline the charts, trace screenshots, and diagrams the work produced. Then sum up in one short bullet per thing the user asked for: what came of it, and whether it is done, still running, failed, or not checked. Write each line the way you would say it out loud: "The decode kernel was slow from LDS bank conflicts", not "Decode review: done" or "Slow decode: LDS conflicts". Name any bug found and fixed on the way. Each line must stay true when read alone. Never mark something done that still waits on the user, and leave out anything the action items say. Under the summary, give at most three short lines that change what the user knows or must do. Then name in one line any work left that you can do yourself.

Then list the action items. Ask the call the user owns, such as merge, approve, or pick, and give your pick. A step you would take first goes in your pick. So does anything that must happen first, and anything that cannot be undone. Give the number or link of each PR, ticket, or agent a call is about, also in a call between options.

Fit the shape to the call. A call about one item is one bullet: the call, your pick, what it changes for the kernel's users, the evidence behind your pick, and its risk, with the item named once. When items share a call, write the call and your pick once, then give each item its own bullet, riskiest first: its link and name, what it changes for users, the evidence behind your pick, and its risk. Name an item's pick only where it differs from the call's. Give each item's risk even when it is low, such as "Low risk: only the test shapes change." Say what waiting costs only when it is more than a delay, such as a release cut or a held GPU.

For a call between options, give every option the work weighed, each with what it gets the user and what it costs, and the current state when there is one. Those costs are the call's risk, so add no separate risk line. When a chart above shows the options, write each option's gain and cost under it.

## Visuals

A visual is a picture: a chart, a trace screenshot, a Mermaid diagram, a chart or diagram from `/visualize`, or a generated image. A Markdown table is not a visual, even with before and after columns. A per-shape table can still carry numbers in the text.

When something is easier to grasp as a picture than as sentences, draw it: how a kernel or pipeline works, a PR stack with each PR's state, a before and after of a fix, or options side by side. Never draw a status list, a list of action items, or boxes with nothing connecting them. Never give a fact twice, in text or across visuals.

Keep each visual small enough to read at a glance: at most six boxes, with at most eight words in each. Write labels as plain words a person would say, not tags like "Tests: pass". A fact that needs a sentence belongs in the text, or nowhere.

Kernel pictures come from the run's artifacts: a before and after chart per shape from the bench artifact, the kernel's place on the roofline, an ATT or WaveScope screenshot of the stall, or the ISA resource diff. Embed them inline, not only as links. If a perf change has no artifact yet, mark its summary line "No artifact yet," and say there what was measured. Use a Mermaid diagram for how things connect and a `/visualize` chart for numbers. Link the ticket's HTML page when one exists. Never invent a number, and never draw a chart or trace you did not produce. Link only artifacts that exist.
