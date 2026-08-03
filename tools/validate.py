"""
tools/validate.py — keyless "repo doctor" for the Jarvis brain.

Checks the brain's structural integrity WITHOUT making any model call or needing an
API key: config parses and routes, skills/memory files have valid frontmatter, the
memory index links resolve, and secret hygiene holds. Run it any time — especially
after adding a skill or memory fact — to catch mistakes early.

    python tools/validate.py        # prints problems; exit 1 if any errors

Claude Code may extend the checks as the brain grows. It must stay keyless and make
no network/model calls, so it's always safe to run.

Dependencies: pyyaml (already in tools/requirements.txt).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _parse_frontmatter(text: str) -> dict | None:
    """Return the YAML frontmatter block of a markdown file as a dict, or None."""
    import yaml

    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def check(root: Path = REPO_ROOT) -> tuple[list[str], list[str]]:
    """Run all structural checks. Returns (errors, warnings) as lists of messages."""
    import yaml

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Provider config parses and the active entry resolves to a model.
    cfg_path = root / "config" / "providers.yaml"
    if not cfg_path.exists():
        errors.append("config/providers.yaml is missing.")
    else:
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            cfg = {}
            errors.append(f"config/providers.yaml does not parse: {exc}")
        providers = cfg.get("providers", {})
        active = cfg.get("active")
        if not providers:
            errors.append("config/providers.yaml has no 'providers' map.")
        elif active not in providers:
            errors.append(
                f"config/providers.yaml 'active' ({active!r}) is not a key under 'providers'."
            )
        elif not providers[active].get("model"):
            errors.append(f"config/providers.yaml active provider {active!r} has no 'model'.")

    # 2. Every skill has frontmatter with at least name + description.
    skills_dir = root / "skills"
    for skill in sorted(skills_dir.glob("*.md")):
        fm = _parse_frontmatter(skill.read_text(encoding="utf-8"))
        rel = skill.relative_to(root)
        if fm is None:
            errors.append(f"{rel}: missing or invalid YAML frontmatter.")
            continue
        for field in ("name", "description"):
            if not fm.get(field):
                errors.append(f"{rel}: frontmatter missing '{field}'.")
        if not fm.get("when_to_use"):
            warnings.append(f"{rel}: frontmatter has no 'when_to_use' (recommended).")

    # 3. Memory fact files have frontmatter with name + description + type.
    memory_dir = root / "memory"
    for fact in sorted(memory_dir.glob("*.md")):
        if fact.name == "MEMORY.md":
            continue
        fm = _parse_frontmatter(fact.read_text(encoding="utf-8"))
        rel = fact.relative_to(root)
        if fm is None:
            errors.append(f"{rel}: missing or invalid YAML frontmatter.")
            continue
        for field in ("name", "description", "type"):
            if not fm.get(field):
                errors.append(f"{rel}: frontmatter missing '{field}'.")

    # 4. MEMORY.md index links all resolve to existing files.
    index = memory_dir / "MEMORY.md"
    if not index.exists():
        errors.append("memory/MEMORY.md is missing.")
    else:
        for target in re.findall(r"\]\(([^)]+\.md)\)", index.read_text(encoding="utf-8")):
            if not (memory_dir / target).exists():
                errors.append(f"memory/MEMORY.md links to missing file: {target}")

    # 5. Secret hygiene: .env.example exists, .gitignore ignores .env.
    if not (root / ".env.example").exists():
        errors.append(".env.example is missing (documents required keys).")
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        errors.append(".gitignore is missing.")
    elif ".env" not in gitignore.read_text(encoding="utf-8").split():
        errors.append(".gitignore does not ignore .env — secrets could be committed.")

    # 6. Any tools/*.py referenced by a skill actually exists.
    referenced = set()
    for skill in sorted(skills_dir.glob("*.md")):
        referenced.update(re.findall(r"tools/([A-Za-z0-9_]+\.py)", skill.read_text(encoding="utf-8")))
    for name in sorted(referenced):
        if not (root / "tools" / name).exists():
            errors.append(f"a skill references tools/{name}, which does not exist.")

    return errors, warnings


def main() -> int:
    errors, warnings = check()
    for w in warnings:
        print(f"⚠  {w}")
    for e in errors:
        print(f"❌ {e}")
    if errors:
        print(f"\nFAIL — {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"OK — brain structure valid ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
