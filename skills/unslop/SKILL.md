---
name: unslop
description: Cut AI tells from any writing.
disable-model-invocation: true
---

# Unslop

Edit text to remove AI patterns. Scan for the patterns below, then rewrite. Preserve meaning and match the intended tone. In agent-facing text such as a skill or a prompt, a dropped condition changes what the agent does, so keep every step, number, default, and exception. When you cannot expand a compressed line without guessing its meaning, leave it and say so.

`python3 scripts/check.py` flags the unambiguous part of rules 7, 8, 13, 18, 19, 20, and 31 in mstack's own markdown. The other rules need a read.

Rule numbers are stable ids that other skills cite. A removed rule leaves a gap. Rules 13 to 16 and 33 govern sentences. An arrow, a label, or a table cell inside a diagram or a table is not a sentence, so they do not apply there. An arrow inside a list item or a paragraph is in a sentence, so they do. Leave code, quoted user text, and a deliberate bad example as they are.

3. No trailing "-ing" phrases that add no fact ("highlighting...", "ensuring...").
5. No vague attributions ("experts believe"). Name the source or delete.
7. No AI vocabulary: additionally, crucial, delve, enhance, foster, landscape, pivotal, showcase, testament, underscore, vibrant.
8. Say "is" or "has", not "serves as", "stands as", "boasts", "features".
9. No "not just X, but Y". State the point.
10. Don't force ideas into threes. Stacked near-synonyms are the same tell: "careful, cautious, and precise" becomes "careful".
11. One name per thing. Repeat it.
12. No "from X to Y" unless X and Y sit on a real scale.
13. No em dashes, en dashes, or hyphens used as dashes, and no parentheses in their place. Use a period or a comma. A comma cannot join two full sentences, so "claims are cheap to verify — run the test first" becomes "claims are cheap to verify, so run the test first". Write a number range as "1 to 3", not "1–3" or "1-3".
14. A colon goes before a list or an example, even an inline one ("three checks: the build, the test, and the bench"), never mid-sentence as a connector.
15. Don't bold every proper noun or acronym.
16. No bold label and colon that restates its line ("**Performance:** Performance improved..."). A bold lead-in that ends in a period and adds new detail is fine.
17. Sentence case headings. Keep proper nouns, and keep a heading that a template tells the agent to emit word for word. When you recase a heading, recase the places that cite it by title.
18. No decorative emojis.
19. Straight quotes.
20. No chatbot phrases ("I hope this helps!", "Let me know if...", "You might be wondering...", "Here's the thing.").
22. No praise or agreement openers. Respond directly.
23. Cut filler. "In order to" becomes "to". Delete "it is important to note that".
24. One hedge at most: "may".
25. No generic conclusions. State specific plans or facts.
26. No abstract metaphor nouns: substrate, wedge, vector, nexus, primitive, harness, surface, scaffolding, paradigm, ratchet, north star, flywheel, fence for scope. Use the concrete word. The literal term stays: a test harness is a harness. So does a term the repo defines once and uses consistently, such as mstack's "surface" for the kind of artifact a change runs on, or the "scaffold" step in `architect`. "Surface" as a verb is rule 32.
27. Say what it does, not how it feels. "a blazing-fast kernel", "memory-friendly layout", and "attention that flies" name a feeling. Name the mechanism or the number: "reads each K tile from HBM once", "41 us to 33 us, 61% of HBM peak on gfx950". Cut a sentence that could appear unchanged in another project's docs.
28. One idea per sentence. Split a sentence the reader has to reread.
29. Active voice. Name the actor unless it is unknown or doesn't matter.
30. Cut adverbs or use a stronger verb. Give the number. Keep an adverb that names real behavior ("silently drops the flag") and "just" when it means "only".
31. Use the plain word: "use", not "utilize" or "leverage".
32. No metaphor, aphorism, personified code, or figurative verb where a literal phrase exists. Figurative verbs include "rides along", "stands on", "earns", "burns", "kills", "lands", "bolts on", "papers over", and "surfaces". Stock framing phrases and capitals for emphasis ("BECAUSE") count too. To test a contrast line such as "tolerance is a decision, not a knob", replace the figure with its literal meaning. If the literal version still says something checkable, write that version. If it says nothing, cut the line.
33. Write whole sentences with their articles and verbs. Spell out arrows, `>`, `+`, and abbreviations. A short imperative ("Reproduce first.") is a sentence. A field list that a template defines, such as a playbook's closing "**Reply:**" line, may stay verbless.
