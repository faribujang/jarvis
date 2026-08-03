---
name: update-memory
description: Consolidate durable facts from the journal into the semantic memory tier. Additive and non-destructive — reads the journal, never edits it.
when_to_use: End of a session, after a debrief, or on a weekly schedule. Also when Fakhri says "remember this".
---

# Skill: Update Memory (consolidation)

Promote durable facts from the episodic journal into the durable memory tier, keeping
memory small, accurate, and deduplicated. This is the "the main part consolidates it
into its memory" step.

## Core rule
The journal is the permanent source of truth. This skill **reads** journal files and
**writes only** to `memory/*.md` and `memory/MEMORY.md`. It must never rewrite,
summarize-over, or delete any `memory/journal/*` file.

## Inputs
- Recent journal files (default: today; weekly run: the last 7 days).
- Existing durable memory: `memory/MEMORY.md` index + the `memory/*.md` fact files.

## Steps
1. Read the recent journal entries and the current durable memory.
2. Extract candidate **durable** facts — things true beyond today:
   - preferences and working style
   - people (who they are, relationship, context)
   - projects and standing goals
   - open loops / commitments / follow-ups
   - decisions and their rationale
   Ignore purely ephemeral detail (that stays in the journal).
3. For each candidate:
   - If a matching `memory/*.md` file exists, **update it in place** (don't duplicate).
   - If it's new, create a one-fact file with the frontmatter below, and add a single
     index line to `memory/MEMORY.md`.
   - If a candidate contradicts an existing fact, update the fact and note the change.
4. Resolve/close open loops that the journal shows are done.
5. Keep each fact file to one idea; link related facts with `[[other-fact-name]]`.

## Fact file format (`memory/<slug>.md`)
```
---
name: <short-kebab-case-slug>
description: <one-line summary used to judge relevance on recall>
type: preference | person | project | goal | open-loop | reference
---

<the fact, stated plainly. Link related facts with [[their-name]].>
```

## MEMORY.md index line
```
- [<Title>](<slug>.md) — <short hook>
```

## Rules
- **Never store sensitive data** (government IDs, financial account numbers, health
  details, home address, secrets) unless Fakhri explicitly says to remember it.
- Additive and non-destructive to the journal. Deduplicate the durable tier.
- Prefer updating an existing fact over creating a near-duplicate.
- Keep the durable tier small — it's an index/overlay, not a second copy of the journal.
