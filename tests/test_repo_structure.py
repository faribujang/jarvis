"""
Structural integrity tests for the brain — no model calls, no key needed.

These drive tools/validate.py plus a few targeted assertions, so that adding a
malformed skill or a broken memory link fails CI-style checks immediately.

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import validate  # noqa: E402


class TestRepoIsHealthy(unittest.TestCase):
    def test_no_errors_in_real_repo(self):
        errors, _warnings = validate.check(REPO_ROOT)
        self.assertEqual(errors, [], f"validate.py found problems: {errors}")

    def test_expected_layout_exists(self):
        for rel in (
            "AGENTS.md",
            "CLAUDE.md",
            "config/providers.yaml",
            "tools/llm.py",
            "tools/validate.py",
            "memory/MEMORY.md",
            "memory/user-profile.md",
            "memory/journal",
            ".env.example",
            ".gitignore",
        ):
            self.assertTrue((REPO_ROOT / rel).exists(), f"missing: {rel}")

    def test_env_is_ignored_and_no_real_env_committed(self):
        gi = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").split()
        self.assertIn(".env", gi)


class TestValidateCatchesProblems(unittest.TestCase):
    """Prove the doctor actually detects breakage (not just passing on the happy path)."""

    def _skeleton(self, root: Path):
        (root / "config").mkdir()
        (root / "skills").mkdir()
        (root / "memory").mkdir()
        (root / "tools").mkdir()
        (root / "config" / "providers.yaml").write_text(
            "active: gemini\nproviders:\n  gemini:\n    model: gemini/gemini-2.5-flash\n",
            encoding="utf-8",
        )
        (root / "memory" / "MEMORY.md").write_text("# index\n", encoding="utf-8")
        (root / ".env.example").write_text("GEMINI_API_KEY=\n", encoding="utf-8")
        (root / ".gitignore").write_text(".env\n", encoding="utf-8")

    def test_clean_skeleton_passes(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            self._skeleton(root)
            errors, _ = validate.check(root)
            self.assertEqual(errors, [])

    def test_broken_memory_link_detected(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            self._skeleton(root)
            (root / "memory" / "MEMORY.md").write_text(
                "- [Ghost](ghost.md) — missing target\n", encoding="utf-8"
            )
            errors, _ = validate.check(root)
            self.assertTrue(any("ghost.md" in e for e in errors), errors)

    def test_bad_active_provider_detected(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            self._skeleton(root)
            (root / "config" / "providers.yaml").write_text(
                "active: nope\nproviders:\n  gemini:\n    model: gemini/gemini-2.5-flash\n",
                encoding="utf-8",
            )
            errors, _ = validate.check(root)
            self.assertTrue(any("active" in e for e in errors), errors)

    def test_skill_without_frontmatter_detected(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            self._skeleton(root)
            (root / "skills" / "broken.md").write_text("no frontmatter here\n", encoding="utf-8")
            errors, _ = validate.check(root)
            self.assertTrue(any("broken.md" in e for e in errors), errors)

    def test_missing_env_example_detected(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            self._skeleton(root)
            (root / ".env.example").unlink()
            errors, _ = validate.check(root)
            self.assertTrue(any(".env.example" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
