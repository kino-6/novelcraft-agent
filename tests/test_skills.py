from pathlib import Path

from novelcraft_agent.skills import load_skills


def test_skill_loading(tmp_path: Path) -> None:
    p = tmp_path / "skills"
    p.mkdir()
    (p / "a.md").write_text("# alpha\n## Purpose\n...", encoding="utf-8")
    loaded = load_skills(p)
    assert "alpha" in loaded
