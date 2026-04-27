from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .cleaner import clean_generated_text, extract_json_block
from .io import IterationArtifacts
from .ollama_client import GenerationResult
from .prompts import analyzer_prompt, director_prompt, polish_prompt, writer_prompt
from .skills import load_skills


@dataclass(slots=True)
class PipelineConfig:
    model: str = "llama3.1"
    analyzer_model: str | None = None
    director_model: str | None = None
    writer_model: str | None = None
    polish_model: str | None = None
    iterations: int = 3
    tail_chars: int = 4000
    no_polish: bool = False
    show_thinking: bool = False


@dataclass(slots=True)
class PipelineResult:
    continuation: str
    state_history: list[dict[str, Any]]
    artifacts: list[IterationArtifacts]


class GeneratorClient(Protocol):
    def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        on_response_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
    ) -> GenerationResult: ...


def _select_model(primary: str | None, fallback: str) -> str:
    return primary or fallback


def _parse_json(text: str) -> dict[str, Any]:
    return json.loads(extract_json_block(text))


def _validate_selected_skill(selected: str, available: dict[str, Any]) -> str:
    if selected in available:
        return selected
    lowered = {k.lower(): k for k in available}
    if selected.lower() in lowered:
        return lowered[selected.lower()]
    raise ValueError(f"Director selected unknown skill: {selected}")


def should_discard_polish(writer_text: str, polished_text: str, threshold: float = 0.85) -> bool:
    if not writer_text.strip():
        return False
    return len(polished_text.strip()) < int(len(writer_text.strip()) * threshold)


def run_pipeline(
    *,
    input_text: str,
    skills_dir: Path,
    config: PipelineConfig,
    client: GeneratorClient,
    on_stream: Callable[[str], None] | None = None,
    on_phase: Callable[[str], None] | None = None,
    on_thinking: Callable[[str], None] | None = None,
) -> PipelineResult:
    skills = load_skills(skills_dir)
    if not skills:
        raise ValueError(f"No skills found in {skills_dir}")

    continuation_parts: list[str] = []
    state_history: list[dict[str, Any]] = []
    artifacts: list[IterationArtifacts] = []

    for i in range(1, config.iterations + 1):
        context = (input_text.rstrip() + "\n\n" + "\n\n".join(continuation_parts)).strip()
        tail = context[-config.tail_chars :]

        if on_phase:
            on_phase(f"Iteration {i}/{config.iterations} · Analyzer")
        analysis_raw = client.generate_stream(
            model=_select_model(config.analyzer_model, config.model),
            prompt=analyzer_prompt(tail),
        ).response
        analysis = _parse_json(analysis_raw)

        if on_phase:
            on_phase(f"Iteration {i}/{config.iterations} · Director")
        direction_raw = client.generate_stream(
            model=_select_model(config.director_model, config.model),
            prompt=director_prompt(tail, analysis, list(skills.keys())),
        ).response
        direction = _parse_json(direction_raw)
        selected_skill = _validate_selected_skill(direction.get("selected_skill", ""), skills)
        direction["selected_skill"] = selected_skill

        if on_phase:
            on_phase(f"Iteration {i}/{config.iterations} · Writer")
        writer_res = client.generate_stream(
            model=_select_model(config.writer_model, config.model),
            prompt=writer_prompt(tail, analysis, direction, skills[selected_skill].content),
            on_response_chunk=on_stream,
            on_thinking_chunk=on_thinking if config.show_thinking else None,
        )
        writer_text = clean_generated_text(writer_res.response)

        polished_text = writer_text
        if not config.no_polish:
            if on_phase:
                on_phase(f"Iteration {i}/{config.iterations} · Polish")
            polish_res = client.generate_stream(
                model=_select_model(config.polish_model, config.model),
                prompt=polish_prompt(writer_text),
                on_response_chunk=on_stream,
                on_thinking_chunk=on_thinking if config.show_thinking else None,
            )
            candidate = clean_generated_text(polish_res.response)
            if candidate and not should_discard_polish(writer_text, candidate):
                polished_text = candidate

        continuation_parts.append(polished_text)
        state_history.append({"iteration": i, "analysis": analysis, "direction": direction})
        artifacts.append(
            IterationArtifacts(
                analysis=analysis,
                direction=direction,
                writer_part=writer_text,
                polished_part=polished_text if not config.no_polish else writer_text,
                final_part=polished_text,
            )
        )

    continuation = "\n\n".join(part.strip() for part in continuation_parts if part.strip()).strip()
    return PipelineResult(continuation=continuation, state_history=state_history, artifacts=artifacts)
