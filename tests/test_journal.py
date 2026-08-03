"""
Tests for tools/journal.py — journal read/write, especially the append behavior.

No model calls, no network. Uses a temp journal dir so the real journal is untouched.

Run from the repo root:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

import tools.journal as journal


class TestJournalAppend(unittest.TestCase):
    def setUp(self):
        self._orig = journal.JOURNAL_DIR
        self.tmp = Path(tempfile.mkdtemp())
        journal.JOURNAL_DIR = self.tmp
        self.d = date(2026, 7, 11)

    def tearDown(self):
        journal.JOURNAL_DIR = self._orig

    def test_append_bullet_keeps_every_item(self):
        """Regression: repeated captures under one section must ALL persist."""
        journal.append_bullet("Open loops", "call the bank", self.d)
        journal.append_bullet("Open loops", "review PR", self.d)
        journal.append_bullet("Open loops", "email advisor", self.d)

        content = journal.read_journal(self.d)
        self.assertIn("call the bank", content)
        self.assertIn("review PR", content)
        self.assertIn("email advisor", content)
        # exactly one "Open loops" heading — items grouped, not duplicated sections
        self.assertEqual(content.count("## Open loops"), 1)

    def test_append_bullet_separate_sections(self):
        journal.append_bullet("Open loops", "a loop", self.d)
        journal.append_bullet("Quick capture", "an idea", self.d)
        content = journal.read_journal(self.d)
        self.assertIn("## Open loops", content)
        self.assertIn("## Quick capture", content)

    def test_append_bullet_into_existing_middle_section(self):
        """A bullet must land in its section even when a later section exists."""
        journal.append_bullet("Open loops", "first", self.d)
        journal.append_bullet("Later", "something", self.d)
        journal.append_bullet("Open loops", "second", self.d)
        content = journal.read_journal(self.d)
        loops_block = content.split("## Later")[0]
        self.assertIn("first", loops_block)
        self.assertIn("second", loops_block)  # inserted into Open loops, not appended after Later

    def test_write_section_is_idempotent(self):
        """Morning/Evening blocks are write-once (unchanged behavior)."""
        journal.write_section("Morning", "brief one", self.d)
        journal.write_section("Morning", "brief two", self.d)
        content = journal.read_journal(self.d)
        self.assertEqual(content.count("## Morning"), 1)
        self.assertIn("brief one", content)
        self.assertNotIn("brief two", content)

    def test_has_section_is_exact_not_substring(self):
        """Regression: section detection must be line-exact, not a loose substring —
        the capture `section` name is user-controlled, so '## Morning' mentioned inside
        a bullet must NOT count as the Morning section existing."""
        content = "# Journal\n\n## Notes\n\n- talked about my ## Morning routine\n"
        self.assertFalse(journal.has_section(content, "Morning"))
        self.assertTrue(journal.has_section(content, "Notes"))

    def test_append_bullet_not_fooled_by_heading_in_prose(self):
        """A bullet mentioning '## Open loops' in its text must not block a real
        Open loops section from being created."""
        journal.append_bullet("Notes", "reminder about ## Open loops formatting", self.d)
        journal.append_bullet("Open loops", "a genuine loop", self.d)
        content = journal.read_journal(self.d)
        # count real heading LINES (not the substring that appears inside the prose bullet)
        heading_lines = [ln for ln in content.splitlines() if ln.strip() == "## Open loops"]
        self.assertEqual(len(heading_lines), 1)
        self.assertIn("a genuine loop", content)


if __name__ == "__main__":
    unittest.main()
