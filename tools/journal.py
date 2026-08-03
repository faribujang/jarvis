"""
tools/journal.py — journal read/write helpers for Jarvis.

Journal lives at memory/journal/YYYY-MM-DD.md. One file per day.
Morning section written by brief; Evening section appended by debrief.
Never overwrites existing sections — always appends.

Claude Code may update this file as it sees fit.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL_DIR = ROOT / "memory" / "journal"


def today() -> date:
    return date.today()


def journal_path(d: date | None = None) -> Path:
    """Return the path to the journal file for a given date (default: today)."""
    d = d or today()
    return JOURNAL_DIR / f"{d.isoformat()}.md"


def read_journal(d: date | None = None) -> str:
    """Read the journal file for a given date. Returns empty string if not found."""
    path = journal_path(d)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def has_section(content: str, heading: str) -> bool:
    """Check if a journal file already has a given ## section (line-based, exact)."""
    target = f"## {heading}"
    return any(line.strip() == target for line in content.splitlines())


def write_section(heading: str, content: str, d: date | None = None) -> Path:
    """
    Append a new ## section to the journal file for a given date.

    - If the file doesn't exist, creates it with a date header.
    - If the section already exists, does nothing (no duplicates).
    - Always appends — never overwrites existing content.
    """
    d = d or today()
    path = journal_path(d)
    existing = read_journal(d)

    if has_section(existing, heading):
        return path  # idempotent — already written

    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%H:%M")
    content = content.rstrip()
    if "\n" in content:
        # Multi-line content (e.g. a full brief) — timestamp on its own line
        section_text = f"\n## {heading}\n\n_{timestamp}_\n\n{content}\n"
    else:
        section_text = f"\n## {heading}\n\n_{timestamp}_ — {content}\n"

    if not existing:
        header = f"# Journal — {d.strftime('%A, %B %d, %Y')}\n"
        path.write_text(header + section_text, encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(section_text)

    return path


def append_bullet(heading: str, text: str, d: date | None = None) -> Path:
    """
    Append a timestamped bullet under a ## section, creating the section if absent.

    Unlike write_section (idempotent, for one-shot blocks like Morning/Evening),
    this ALWAYS appends — so repeated captures under the same heading all persist.
    The bullet lands at the end of that section, before the next ## or EOF.
    """
    d = d or today()
    path = journal_path(d)
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%H:%M")
    bullet = f"- _{timestamp}_ {text.strip()}"
    existing = read_journal(d)

    if not existing:
        header = f"# Journal — {d.strftime('%A, %B %d, %Y')}\n"
        path.write_text(f"{header}\n## {heading}\n\n{bullet}\n", encoding="utf-8")
        return path

    if not has_section(existing, heading):
        # New section at the end of the file.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {heading}\n\n{bullet}\n")
        return path

    # Section exists — insert the bullet at the end of that section.
    lines = existing.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        out.append(lines[i])
        if lines[i].strip() == f"## {heading}":
            # advance to the end of this section (next '## ' or EOF)
            j = i + 1
            while j < n and not lines[j].startswith("## "):
                j += 1
            # copy section body, then drop trailing blank lines before inserting
            body = lines[i + 1:j]
            while body and body[-1].strip() == "":
                body.pop()
            out.extend(body)
            out.append(bullet)
            out.append("")
            i = j
            continue
        i += 1
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return path


def append_raw(content: str, d: date | None = None) -> Path:
    """Append raw markdown text to the journal file with no section wrapper."""
    d = d or today()
    path = journal_path(d)
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        header = f"# Journal — {d.strftime('%A, %B %d, %Y')}\n\n"
        path.write_text(header + content.rstrip() + "\n", encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + content.rstrip() + "\n")

    return path


def list_journal_dates() -> list[date]:
    """Return all dates that have journal files, newest first."""
    dates = []
    for f in JOURNAL_DIR.glob("*.md"):
        if f.name == ".gitkeep":
            continue
        try:
            dates.append(date.fromisoformat(f.stem))
        except ValueError:
            continue
    return sorted(dates, reverse=True)
