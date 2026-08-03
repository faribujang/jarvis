---
name: debrief
description: End-of-day check-in. Recap what happened, capture how Fakhri is feeling, and append it to today's journal file. Then trigger memory consolidation.
when_to_use: Evening, on a schedule or when Fakhri says he's wrapping up / "let's debrief".
---

# Skill: Debrief (evening)

Run a short, reflective end-of-day check-in and **append** an `## Evening recap`
section to today's journal file (the same file the morning brief created). This is
semi-interactive: ask Fakhri a couple of light questions rather than guessing his
inner state.

## Inputs
- Today's journal file (`memory/journal/<today>.md`), including its `## Morning`
  section (what was planned) so you can compare plan vs. reality.
- The day's conversation/context with Fakhri and anything logged to the journal.
- Tracked tasks / open loops (to mark what got done or moved).

## Steps
1. Read today's journal file, especially the `## Morning` focus and tasks.
2. Draft a factual recap of what actually happened: what got done, what moved, what
   didn't, decisions made, anything notable from conversations. Use `tools/llm.py` if
   summarization helps.
3. **Ask Fakhri, briefly** (1–3 short questions, not a form): how the day went, how
   he's feeling, anything on his mind or worth remembering. Keep it human and light —
   one line back is fine. Do not push if he's terse.
4. Compose the `## Evening recap` in the format below.
5. **Append** it to `memory/journal/<today>.md`. Never create a second file; never
   overwrite the `## Morning` section.
6. Update tracked tasks/open loops (done / carried over).
7. Invoke `skills/update-memory.md` to consolidate today's durable facts.

## Output format (append to today's journal file)
```

## Evening recap
**Done:** <what got completed / progressed>
**Didn't get to:** <carried over — becomes tomorrow's open loops>
**Notable:** <decisions, events, things worth remembering>
**How Fakhri's doing:** <his own words / mood — captured from the check-in, not inferred>
**For tomorrow:** <1–3 things to carry forward>
```

## Rules
- Reflective and honest, never toxic-positive. If it was a rough day, acknowledge it
  plainly; don't over-reassure or amplify negativity — steady and kind.
- The "how Fakhri's doing" line should come from what he actually said. If he didn't
  share, write "not shared" rather than guessing his emotions.
- Never store sensitive personal data (health, IDs, etc.) unless he explicitly asks.
- Append only. The morning section and all prior days stay untouched.
- Wellbeing: if he expresses real distress, respond as a caring person first — drop the
  recap format and be present. Don't treat a hard day as a data-capture task.
