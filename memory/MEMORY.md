# MEMORY.md — durable memory index

> This public repo ships **example** memory data to demonstrate the system. Real personal
> memory (profile + daily journals) is git-ignored and stays local.

One line per durable fact. Read this first to recall who the operator is and the standing
context; open a linked file for detail. This tier is small, deduplicated, and additive —
it is built *from* the journal but never replaces it.

Episodic history lives in `journal/YYYY-MM-DD.md` (one permanent file per day, never
summarized over). Optional weekly rollups live in `weekly/`. To recall "what happened on
day X," read that day's journal file in full — not a summary.

## Facts
- [User profile](user-profile.md) — who Fakhri is, how he wants his assistant to work, current focus.
