from pathlib import Path

from novelcraft_agent.io import resolve_output_dir


def test_output_dir_resolution_default(tmp_path: Path) -> None:
    input_path = tmp_path / "novel.txt"
    input_path.write_text("x", encoding="utf-8")
    assert resolve_output_dir(input_path, None) == tmp_path / "output"


def test_output_dir_resolution_override(tmp_path: Path) -> None:
    input_path = tmp_path / "novel.txt"
    assert resolve_output_dir(input_path, "custom/out") == Path("custom/out")
