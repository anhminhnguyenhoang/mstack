---
name: unslop
description: Cut AI tells from any writing.
disable-model-invocation: true
---

# Unslop

Edit text to remove AI patterns. Scan for the patterns below, then rewrite. Preserve meaning and match the intended tone. In agent-facing text such as a skill or a prompt, a dropped condition changes what the agent does, so keep every step, number, default, and exception. When you cannot expand a compressed line without guessing its meaning, leave it and say so.

`python3 scripts/check.py` flags the unambiguous part of rules 7, 8, 13, 18, 19, 20, and 31 in mstack's own markdown. The other rules need a read.

## Patterns to detect and fix

Rule numbers are stable ids that other skills cite. A removed rule leaves a gap. Rules 13 to 16 and 33 govern sentences. An arrow, a label, or a table cell inside a diagram or a table is not a sentence, so they do not apply there. An arrow inside a list item or a paragraph is in a sentence, so they do. Leave code, quoted user text, and a deliberate bad example as they are.

### Content

3. **Superficial -ing phrases.** "highlighting...", "ensuring...", "reflecting...", "showcasing...", "fostering...". Delete or expand with real sources.
5. **Vague attributions.** "Experts believe", "Industry reports suggest", "Some critics argue". Name the source or delete.

### Language

7. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore, vibrant. Replace with plain words.
8. **Fancy ways to say "is".** "serves as", "stands as", "boasts", "features". Say "is" or "has".
9. **"Not just X, but Y."** State the point directly instead.
10. **Rule of three.** Don't force ideas into groups of three. Use the natural number. Stacked near-synonyms are the same tell: "careful, cautious, and precise" becomes "careful".
11. **Synonym cycling.** Protagonist, main character, central figure, hero all in one paragraph. Pick one, repeat it.
12. **False ranges.** "from X to Y" where X and Y aren't on a meaningful scale. List topics directly.

### Style

13. **Em dash overuse.** Avoid em dashes entirely. If a thought needs separation, end the sentence or use a comma. Do not swap the dash for parentheses, an en dash, or a spaced hyphen. A comma cannot join two full sentences, so "claims are cheap to verify — run the test first" becomes "claims are cheap to verify, so run the test first". Write a number range as "1 to 3", not "1–3" or "1-3".
14. **Colon overuse.** Colons are fine before a list or example, even an inline one ("three checks: the build, the test, and the bench"), not as mid-sentence connectors. "If you're coming from traditional automation: instead of registering event handlers, you describe conditions" adds nothing with the colon. Rewrite to let the point stand on its own without comparison framing. "Describing when the scheduler should fire works best as plain English." Same meaning, no crutch punctuation.
15. **Boldface overuse.** Don't bold every proper noun or acronym.
16. **Inline-header lists.** The tell is a bold label and colon that restates the line: "**Performance:** Performance improved...". Convert those to prose. A bold lead-in that ends in a period, names the item, and is followed by genuinely new detail ("**Schema in TypeScript.** Tables live in one file.") is fine, not a tell.
17. **Title case headings.** Use sentence case. Keep proper nouns, and keep a heading that a template tells the agent to emit word for word. When you recase a heading, recase the places that cite it by title.
18. **Decorative emojis.** Remove from headings and bullets.
19. **Curly quotes.** Use straight quotes.

### Communication artifacts

20. **Chatbot phrases.** "I hope this helps!", "Let me know if...", "Of course!", "Certainly!", "Found the smoking gun!", "You might be wondering...", "Here's the thing." Remove.
22. **Sycophantic tone.** "Great question! You're absolutely right!" Respond directly.

### Filler

23. **Filler phrases.** "In order to" becomes "To". "Due to the fact that" becomes "Because". Delete "It is important to note that".
24. **Excessive hedging.** "could potentially possibly be argued that it might" becomes "may".
25. **Generic conclusions.** "The future looks bright." State specific plans or facts.

### Jargon

26. **Abstract metaphor nouns.** Substrate (base), wedge, wedge in (add), vector (way, method), locus, vantage, nexus, primitive as a noun, harness as a metaphor, surface as in "API surface", bedrock, scaffolding as a metaphor, modality, paradigm, gold-plating (more than the job needs), ratchet as a metaphor (the mechanism's real name, or a limit that only tightens), evacuate for moving code (move out), endgame (the last phase), north star, flywheel, fence for scope. These read as technical but usually have a plainer concrete word. Pick the concrete word. The literal term stays: a test harness is a harness. So does a term the repo defines once and uses consistently, such as mstack's "surface" for the kind of artifact a change runs on, or the "scaffold" step in `architect`. "Surface" as a verb is rule 32.

### Plain speech

27. **Say what it does, not how it feels.** "the database stays close at hand", "SQL you can read", "types that follow your schema" name a feeling. The fix names the mechanism or a number: "`.toSQL()` returns the exact string sent to the database", "a column rename fails the build". Ask what the sentence tells the reader to do or know, then write that. If you can't restate it as a concrete instruction, fact, or number, cut it. One more check: if the sentence could appear unchanged in another project's docs, it says nothing about this one. Cut it.
28. **Shorten or split dense sentences.** If the reader has to backtrack to parse a sentence, break it in two or drop clauses. One idea per sentence.
29. **Active voice.** Prefer it. Catch "is/are/was/were + past participle" and name the actor: "queries are validated" becomes "the compiler validates queries", "the file is parsed by the loader" becomes "the loader parses the file". Passive is fine only when the actor is unknown or genuinely doesn't matter.
30. **Cut adverbs, or use a stronger verb.** "runs quickly" becomes "is fast" or the number, and "significantly improves" becomes the measured delta. An adverb propping up a weak verb means the verb is wrong. Keep an adverb that names real behavior ("silently drops the flag") and "just" when it means "only".
31. **Prefer the plain word.** "utilize" and "leverage" become "use", "facilitate" becomes "help", "numerous" becomes "many", "in the event that" becomes "if". The fancier synonym is rarely clearer.
32. **Mannered prose.** Metaphor or flourish where a literal phrase exists: aphorisms ("wire it or delete it"), rhetorical fragments for effect, personified code ("the plan holds it"), figurative verbs ("rides along", "stands on", "earns", "burns", "kills", "lands", "bolts on", "papers over", "surfaces"), stock framing phrases, capitals for emphasis ("BECAUSE"). "A dial worth turning" becomes "a parameter worth varying". To test a contrast line such as "tolerance is a decision, not a knob", replace the figure with its literal meaning. If the literal version still says something checkable, write that version. If it says nothing, cut the line. Rule 26 covers the metaphor nouns.
33. **Over-compression.** Dropped articles, verbless fragments, symbol-speak, and abbreviations that make the reader decode instead of read. "Parser rejects bad date → exit 2, no write" becomes "The parser rejects a bad date, exits with code 2, and writes nothing." Write whole sentences with their articles and verbs, and spell out arrows, `>`, `+`, and abbreviations. A short imperative ("Reproduce first.") is a sentence. A field list that a template defines, such as a playbook's closing "**Reply:**" line, may stay verbless.
