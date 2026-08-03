---
name: daily-brief
description: Assemble Fakhri's morning briefing and write it to today's journal file. Forward-looking — what's ahead today.
when_to_use: Each morning, on a schedule, or when Fakhri asks for his brief / "what's on my plate today".
---

# Skill: Daily Brief (morning)

Produce a short, forward-looking morning briefing and record it as the `## Morning`
section of today's journal file.

## Inputs
- `memory/MEMORY.md` + relevant durable facts (standing goals, projects, open loops).
- Yesterday's journal file (`memory/journal/<yesterday>.md`) — especially its
  `## Evening recap` and any unfinished items, so the days connect.
- **Live sources (Phase 4+, optional until connectors exist):** inbox summary,
  today's calendar, news headlines from the news tool, tracked tasks and deadlines.
  Pull these only via `tools/` scripts or configured MCP connectors — never guess.

## Steps
1. Determine today's date (use the system clock).
2. Read `memory/MEMORY.md`, the relevant durable fact files, and yesterday's journal
   file. Note carried-over open loops and any deadline that is near.
3. If live-data tools/connectors are configured, gather: unread/important email,
   today's calendar events, top news headlines from Fakhri's feed, tracked tasks, and
   upcoming deadlines. If a source isn't wired yet, skip it silently — do not fabricate.
4. If any summarization is needed, call it through `tools/llm.py` (provider layer).
5. Compose the brief in the format below — short, skimmable, forward-looking.
6. Create `memory/journal/<YYYY-MM-DD>.md` if it doesn't exist, and write/replace the
   `## Morning` section. Do **not** create a second file for today.
7. Deliver the brief to Fakhri.

## Output format (write to the journal file)
```
# <YYYY-MM-DD> — <weekday>

## Morning
**Focus today:** <1–2 lines: the most important thing(s)>

**Calendar:** <events, or "none / not connected yet">
**Inbox:** <2–4 bullets of what needs attention, or status>
**Tasks & open loops:** <tracked items, carried-over from yesterday flagged>
**Deadlines ahead:** <anything due soon, with dates>
**Headlines:** <3–5 relevant items, or "news not connected yet">

<optional one-line nudge or encouragement>
```

## Rules
- Keep it tight — a brief he can read in under a minute.
- Never fabricate data from an unconnected source; mark it "not connected yet".
- Forward-looking only. The recap of what actually happened belongs to `debrief`.
- Do not touch prior days' journal files.
