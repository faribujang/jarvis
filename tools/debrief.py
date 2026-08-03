"""
tools/debrief.py — evening debrief for Jarvis.

Reads today's journal, then appends an ## Evening recap section.

Two modes:
  - No API key: writes the user's raw input directly.
  - With API key: uses LiteLLM to synthesize the recap from the day's full journal.

Run from repo root:
    python tools/debrief.py                   # interactive (type your notes)
    python tools/debrief.py --text "..."      # pass recap text directly
    python tools/debrief.py --no-llm          # skip LLM synthesis

Claude Code may update this file as it sees fit.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.journal import read_journal, write_section


def generate_debrief(user_input: str, use_llm: bool = True) -> str:
    """Synthesize an evening recap. Falls back to raw input if no key."""
    if not use_llm:
        return user_input.strip()

    today_journal = read_journal()

    try:
        from tools.llm import llm

        prompt = f"""You are Jarvis. Write a concise evening recap based on today's journal and the user's notes.

**Today's journal:**
{today_journal or "(No morning brief was written today)"}

**User's notes:**
{user_input}

Rules:
- Summarize what actually happened today in bullet points.
- Call out open loops to carry forward tomorrow.
- Flag anything worth promoting to durable memory (tag with "→ memory").
- Bold headers, single-sentence bullets.
- Not verbose.
"""
        return llm(prompt)

    except EnvironmentError:
        return user_input.strip()


def _read_multiline() -> str:
    print("What happened today? (Enter a blank line twice to finish)\n")
    lines: list[str] = []
    try:
        while True:
            line = input()
            if not line and lines and not lines[-1]:
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Jarvis evening debrief")
    parser.add_argument("--text", help="Recap text (skip interactive prompt)")
    parser.add_argument("--no-llm", action="store_true", help="Write raw input, no LLM")
    args = parser.parse_args()

    user_input = args.text if args.text else _read_multiline()

    if not user_input.strip():
        print("Nothing to save.")
        sys.exit(0)

    recap = generate_debrief(user_input, use_llm=not args.no_llm)
    path = write_section("Evening recap", recap)

    print(f"\n✓ Written to {path}\n")
    print(recap)
