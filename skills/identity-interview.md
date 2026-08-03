---
name: identity-interview
description: Interview Fakhri one question at a time to capture how he wants his assistant to behave, then write it into AGENTS.md. This is Phase 1 (Identity).
when_to_use: Once, early on, to fill the "About Fakhri" TODO in AGENTS.md. Re-run later to refresh preferences as they change.
---

# Skill: Identity Interview (Phase 1)

Turn Fakhri's own answers into the assistant's personality and standards. The engine
(you) conducts this conversation directly — **no `tools/llm.py` call is needed**; this is
orchestration, not a tool sub-task.

## Core rule
Ask **one question at a time** and wait for the answer before the next. Do not batch a
questionnaire. Keep it short and human. Never invent preferences — only record what Fakhri
actually says.

## Steps
1. Tell Fakhri this is a quick identity setup — a handful of questions, one at a time, and
   he can say "skip" or "that's enough" any time.
2. Ask, one at a time, covering (adapt wording to the conversation):
   - **Communication style:** length, tone, formality, how much formatting he likes.
   - **Standards:** what "good work" from you looks like; what earns his trust.
   - **Always / never:** things you should always do, and hard nos.
   - **Working rhythm:** typical hours, when a morning brief / evening debrief fits.
   - **Current focus:** what he's working on now (this jarvis project, plus anything else).
   - **Decision style:** when to just act vs. check with him first.
3. After each answer, briefly reflect it back in one line so he can correct it.
4. When he's done, compose the **"About Fakhri"** content in his own words, at an
   11th-grade reading level, concise.
5. **Update `AGENTS.md`:** replace the `<!-- TODO (Phase 1) ... -->` block in the
   "About Fakhri" section with the captured preferences. Keep the existing structure; do
   not rewrite the rest of the file.
6. **Update durable memory:** fold any lasting facts into `memory/user-profile.md` (and add
   new one-fact files + `memory/MEMORY.md` index lines for distinct people/projects/goals),
   following `skills/update-memory.md`. Skip sensitive data unless he says to keep it.
7. Confirm what changed and run `python tools/validate.py` to check nothing broke.

## Output
- An updated **"About Fakhri"** section in `AGENTS.md` (TODO comment removed).
- Refreshed `memory/user-profile.md` and any new durable fact files + index lines.

## Rules
- One question at a time; stop when he says stop.
- Only record what he actually said; reflect back before saving.
- Engine-agnostic: this procedure works under any runtime, since it only reads/writes files.
- Never store sensitive personal data (IDs, health, home address, secrets) unless asked.
