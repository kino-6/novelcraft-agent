from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class IterationArtifacts:
    analysis: dict[str, Any]
    direction: dict[str, Any]
    story_memory: dict[str, Any]
    writer_part: str
    polished_part: str
    final_part: str


def timestamp_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def resolve_output_dir(input_path: Path, out_dir: str | None) -> Path:
    if out_dir:
        return Path(out_dir)
    return input_path.parent / "output"


def save_outputs(
    *,
    input_path: Path,
    output_dir: Path,
    stamp: str,
    final_continuation: str,
    original_text: str,
    state_history: list[dict[str, Any]],
    artifacts: list[IterationArtifacts],
    story_memory: dict[str, Any],
    verbose: bool = False,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem

    final_path = output_dir / f"{stem}_final_{stamp}.txt"
    with_path = output_dir / f"{stem}_with_continuation_{stamp}.txt"
    state_path = output_dir / f"{stem}_state_history_{stamp}.json"
    memory_path = output_dir / "story_memory.json"

    final_path.write_text(final_continuation, encoding="utf-8")
    with_path.write_text(f"{original_text.rstrip()}\n\n{final_continuation}".rstrip() + "\n", encoding="utf-8")
    state_path.write_text(json.dumps(state_history, ensure_ascii=False, indent=2), encoding="utf-8")
    memory_path.write_text(json.dumps(story_memory, ensure_ascii=False, indent=2), encoding="utf-8")

    for index, item in enumerate(artifacts, start=1):
        prefix = output_dir / f"{stem}_{stamp}_part_{index:03d}"
        (prefix.with_name(prefix.name + "_analysis.json")).write_text(
            json.dumps(item.analysis, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (prefix.with_name(prefix.name + "_direction.json")).write_text(
            json.dumps(item.direction, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (prefix.with_name(prefix.name + "_story_memory.json")).write_text(
            json.dumps(item.story_memory, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (prefix.with_name(prefix.name + "_writer_part.txt")).write_text(item.writer_part, encoding="utf-8")
        (prefix.with_name(prefix.name + "_polished_part.txt")).write_text(item.polished_part, encoding="utf-8")
        (prefix.with_name(prefix.name + "_final_part.txt")).write_text(item.final_part, encoding="utf-8")

    return {"final": final_path, "with_continuation": with_path, "state_history": state_path, "story_memory": memory_path}
