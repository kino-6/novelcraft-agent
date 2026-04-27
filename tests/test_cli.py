from pathlib import Path

from novelcraft_agent.cli import main


def test_cli_mock_run(tmp_path: Path) -> None:
    in_file = tmp_path / "sample.txt"
    in_file.write_text("Ari stood by the window.", encoding="utf-8")
    out_dir = tmp_path / "out"

    code = main(
        [
            str(in_file),
            "--iterations",
            "1",
            "--mock",
            "--out-dir",
            str(out_dir),
        ]
    )

    assert code == 0
    assert list(out_dir.glob("*_final_*.txt"))
