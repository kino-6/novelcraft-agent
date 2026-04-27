from __future__ import annotations

import json
import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .cleaner import clean_generated_text, extract_json_block
from .io import IterationArtifacts
from .ollama_client import TextGenerationClient
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
    tail_chars: int = 12000
    analysis_context_chars: int = 8000
    polish_context_chars: int = 6000
    no_polish: bool = False
    show_thinking: bool = False
    stream_planning: bool = False
    num_ctx: int = 32768
    writer_num_predict: int = 2200
    polish_num_predict: int = 2200
    analysis_num_predict: int = 1000
    director_num_predict: int = 800
    temperature: float = 0.75
    top_p: float = 0.9
    min_part_chars: int = 1500
    retry_short_output: bool = True
    min_polish_ratio: float = 0.9


@dataclass(slots=True)
class PipelineResult:
    continuation: str
    state_history: list[dict[str, Any]]
    artifacts: list[IterationArtifacts]
    story_memory: dict[str, Any]


class GeneratorClient(Protocol):
    def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        options: dict[str, Any] | None = None,
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
    raise ValueError(f"Director selected unknown skill: {selected}. Allowed: {sorted(available)}")


def should_discard_polish(writer_text: str, polished_text: str, threshold: float = 0.9) -> bool:
    if not writer_text.strip():
        return False
    return len(polished_text.strip()) < int(len(writer_text.strip()) * threshold)


def _slice_tail(text: str, size: int) -> str:
    if size <= 0:
        return ""
    return text[-size:]


def _init_story_memory() -> dict[str, Any]:
    return {
        "characters": [],
        "setting": "",
        "tone": "",
        "open_loops": [],
        "foreshadowing": [],
        "must_preserve": [],
        "latest_summary": "",
        "previous_directions": [],
        "used_skills": [],
    }


def run_pipeline(
    *,
    input_text: str,
    skills_dir: Path,
    config: PipelineConfig,
    client: TextGenerationClient,
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
    story_memory = _init_story_memory()
    skill_summaries = {name: skill.summary for name, skill in skills.items()}

    for i in range(1, config.iterations + 1):
        context = (input_text.rstrip() + "\n\n" + "\n\n".join(continuation_parts)).strip()
        writer_context = _slice_tail(context, config.tail_chars)
        analyzer_context = _slice_tail(context, config.analysis_context_chars)
        polish_context = _slice_tail(writer_context, config.polish_context_chars)
        shared_options = {"num_ctx": config.num_ctx, "temperature": config.temperature, "top_p": config.top_p}

        if on_phase:
            on_phase(f"Iteration {i}/{config.iterations} · Analyzer")
        analysis_raw = client.generate_stream(
            model=_select_model(config.analyzer_model, config.model),
            prompt=analyzer_prompt(analyzer_context),
            options={**shared_options, "num_predict": config.analysis_num_predict},
            on_response_chunk=on_stream if config.stream_planning else None,
        ).response
        analysis = _parse_json(analysis_raw)
        story_memory["characters"] = analysis.get("characters", [])
        story_memory["setting"] = analysis.get("setting", "")
        story_memory["tone"] = analysis.get("tone", "")
        story_memory["open_loops"] = analysis.get("open_loops", [])
        story_memory["foreshadowing"] = analysis.get("foreshadowing", [])
        story_memory["must_preserve"] = analysis.get("must_preserve", [])
        story_memory["latest_summary"] = analysis.get("plot_state", "")

        if on_phase:
            on_phase(f"Iteration {i}/{config.iterations} · Director")
        direction_raw = client.generate_stream(
            model=_select_model(config.director_model, config.model),
            prompt=director_prompt(story_memory, analysis, skill_summaries),
            options={**shared_options, "num_predict": config.director_num_predict},
            on_response_chunk=on_stream if config.stream_planning else None,
        ).response
        direction = _parse_json(direction_raw)
        selected_skill = _validate_selected_skill(direction.get("selected_skill", ""), skills)
        direction["selected_skill"] = selected_skill
        story_memory["previous_directions"] = (story_memory["previous_directions"] + [direction])[-5:]
        if selected_skill not in story_memory["used_skills"]:
            story_memory["used_skills"].append(selected_skill)

        if on_phase:
            on_phase(f"Iteration {i}/{config.iterations} · Writer")
        writer_res = client.generate_stream(
            model=_select_model(config.writer_model, config.model),
            prompt=writer_prompt(
                writer_context,
                story_memory,
                direction,
                skills[selected_skill].content,
                retry_for_length=False,
                min_part_chars=config.min_part_chars,
            ),
            options={**shared_options, "num_predict": config.writer_num_predict},
            on_response_chunk=on_stream,
            on_thinking_chunk=on_thinking if config.show_thinking else None,
        )
        writer_text = clean_generated_text(writer_res.response)
        if config.retry_short_output and len(writer_text.strip()) < config.min_part_chars:
            writer_retry = client.generate_stream(
                model=_select_model(config.writer_model, config.model),
                prompt=writer_prompt(
                    writer_context,
                    story_memory,
                    direction,
                    skills[selected_skill].content,
                    retry_for_length=True,
                    min_part_chars=config.min_part_chars,
                ),
                options={**shared_options, "num_predict": config.writer_num_predict},
                on_response_chunk=on_stream,
                on_thinking_chunk=on_thinking if config.show_thinking else None,
            )
            retry_text = clean_generated_text(writer_retry.response)
            if retry_text:
                writer_text = retry_text

        polished_text = writer_text
        if not config.no_polish:
            if on_phase:
                on_phase(f"Iteration {i}/{config.iterations} · Polish")
            polish_res = client.generate_stream(
                model=_select_model(config.polish_model, config.model),
                prompt=polish_prompt(f"{polish_context}\n\n{writer_text}".strip()),
                options={**shared_options, "num_predict": config.polish_num_predict},
                on_response_chunk=on_stream,
                on_thinking_chunk=on_thinking if config.show_thinking else None,
            )
            candidate = clean_generated_text(polish_res.response)
            if candidate and not should_discard_polish(writer_text, candidate, config.min_polish_ratio):
                polished_text = candidate

        continuation_parts.append(polished_text)
        state_history.append({"iteration": i, "analysis": analysis, "direction": direction})
        artifacts.append(
            IterationArtifacts(
                analysis=analysis,
                direction=direction,
                story_memory=copy.deepcopy(story_memory),
                writer_part=writer_text,
                polished_part=polished_text if not config.no_polish else writer_text,
                final_part=polished_text,
            )
        )

    continuation = "\n\n".join(part.strip() for part in continuation_parts if part.strip()).strip()
    return PipelineResult(
        continuation=continuation, state_history=state_history, artifacts=artifacts, story_memory=story_memory
    )
