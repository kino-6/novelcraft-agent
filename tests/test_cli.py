from pathlib import Path

from novelcraft_agent.cli import main


def test_cli_mock_mode_writes_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.txt"
    input_path.write_text("A small beginning.", encoding="utf-8")

    code = main(
        [
            str(input_path),
            "--iterations",
            "1",
            "--mock",
            "--verbose",
            "--preview-chars",
            "120",
        ]
    )

    assert code == 0
    output_dir = tmp_path / "output"
    assert output_dir.exists()
    assert any(output_dir.glob("*_final_*.txt"))


def test_cli_dry_run_alias(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.txt"
    input_path.write_text("Alias path.", encoding="utf-8")

    code = main([str(input_path), "--iterations", "1", "--dry-run"])
    assert code == 0
