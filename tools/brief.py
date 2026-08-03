"""
tools/brief.py — morning brief generator for Jarvis.

Reads memory + recent journal entries and builds a morning brief.

Two modes:
  - No API key: structured brief from memory files only — no LLM call, still useful.
  - With API key: uses tools/llm.py (Gemini Flash by default) for a natural-language brief.

Run from repo root:
    python tools/brief.py              # print brief (auto-detects key)
    python tools/brief.py --no-llm    # memory-only mode (no key needed)
    python tools/brief.py --write     # also write ## Morning to today's journal

Claude Code may update this file as it sees fit.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.journal import read_journal, write_section, list_journal_dates


# ---------------------------------------------------------------------------
# Memory readers
# ---------------------------------------------------------------------------

def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _read_memory_index() -> str:
    return _read_file(ROOT / "memory" / "MEMORY.md")


def _read_user_profile() -> str:
    return _read_file(ROOT / "memory" / "user-profile.md")


def _read_recent_journal(days: int = 3) -> str:
    entries = []
    for d in list_journal_dates()[:days]:
        content = read_journal(d)
        if content:
            entries.append(f"### {d.isoformat()}\n{content}")
    return "\n\n---\n\n".join(entries) if entries else "(No recent journal entries)"


# ---------------------------------------------------------------------------
# Brief builders
# ---------------------------------------------------------------------------

def build_brief_data() -> dict:
    return {
        "date": date.today().strftime("%A, %B %d, %Y"),
        "user_profile": _read_user_profile(),
        "memory_index": _read_memory_index(),
        "recent_journal": _read_recent_journal(days=3),
    }


def _extract_active_projects(profile: str) -> list[str]:
    """Pull bullet points from the Active projects section of user-profile.md."""
    projects = []
    in_section = False
    for line in profile.splitlines():
        if "## Active projects" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("##"):
                break
            if line.strip().startswith("-"):
                projects.append(line.strip())
    return projects


def _extract_recent_highlights(journal_text: str) -> list[str]:
    """Pull the Evening recap bullets from a journal entry, if any."""
    highlights = []
    in_recap = False
    for line in journal_text.splitlines():
        if "## Evening recap" in line:
            in_recap = True
            continue
        if in_recap:
            if line.startswith("##"):
                break
            if line.strip().startswith("-") or line.strip().startswith("*"):
                highlights.append(line.strip())
    return highlights


def format_brief_no_llm(data: dict) -> str:
    """Clean structured brief — readable and useful with zero API keys."""
    projects = _extract_active_projects(data["user_profile"])
    project_section = "\n".join(projects) if projects else "_No active projects listed._"

    # Pull highlights from the most recent journal entry if available
    dates = list_journal_dates()
    highlights: list[str] = []
    if dates:
        yesterday = read_journal(dates[0])
        highlights = _extract_recent_highlights(yesterday)

    # NOTE: no markdown ## / ### headers here — this text gets stored inside a journal
    # file whose sections are delimited by "## ". Use **bold** labels instead so the
    # brief stays a single, intact journal section.
    lines = [
        "**Active Projects**",
        project_section,
        "",
    ]

    if highlights:
        lines += [
            "**From yesterday**",
            "\n".join(highlights),
            "",
        ]

    lines += [
        "*Add* `GEMINI_API_KEY` *to* `.env` *for an AI-written brief that reads your journal and standing goals.*",
    ]
    return "\n".join(lines)


def format_brief_with_llm(data: dict) -> str:
    """Use LiteLLM (Gemini Flash) to write a natural-language brief."""
    from tools.llm import llm

    prompt = f"""You are Jarvis, Fakhri's personal assistant. Write a sharp morning brief for today.

**Date:** {data['date']}

**User profile:**
{data['user_profile']}

**Memory index:**
{data['memory_index']}

**Recent journal entries:**
{data['recent_journal']}

Rules:
- Start with a 1-sentence TL;DR of what matters today.
- Bold critical keywords at start of paragraphs.
- Use bullet points and **bold labels** for sections — do NOT use markdown "#" or "##" headers (this text is stored inside a journal file that uses ## as delimiters).
- Surface open loops or follow-ups from recent journal entries.
- Do NOT be verbose — every line must earn its place.
- Write as someone who knows Fakhri well, not a generic AI assistant.
"""
    return llm(prompt)


def generate_brief(use_llm: bool = True) -> str:
    """Generate the morning brief. Falls back gracefully if the key is missing."""
    data = build_brief_data()
    if not use_llm:
        return format_brief_no_llm(data)
    try:
        return format_brief_with_llm(data)
    except EnvironmentError:
        return format_brief_no_llm(data)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Jarvis morning brief")
    parser.add_argument("--no-llm", action="store_true", help="Memory-only mode, no API call")
    parser.add_argument("--write", action="store_true", help="Write brief to today's journal")
    args = parser.parse_args()

    brief = generate_brief(use_llm=not args.no_llm)
    print(brief)

    if args.write:
        path = write_section("Morning", brief)
        print(f"\n✓ Written to {path}")
