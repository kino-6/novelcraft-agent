from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Skill:
    name: str
    path: Path
    content: str
    summary: str


def _title_from_markdown(content: str, fallback: str) -> str:
    for line in content.splitlines():
        if line.strip().startswith("# "):
            return line.strip()[2:].strip()
    return fallback


def load_skills(skills_dir: Path) -> dict[str, Skill]:
    loaded: dict[str, Skill] = {}
    if not skills_dir.exists():
        return loaded
    for path in sorted(skills_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        canonical = _title_from_markdown(content, path.stem).strip()
        loaded[canonical] = Skill(name=canonical, path=path, content=content, summary=_summary_from_markdown(content))
    return loaded


def _summary_from_markdown(content: str) -> str:
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        return line[:120]
    return "No description."
