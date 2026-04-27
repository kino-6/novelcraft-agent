from pathlib import Path

import pytest

from novelcraft_agent.pipeline import PipelineConfig, run_pipeline, should_discard_polish
from novelcraft_agent.ollama_client import GenerationResult


class FakeClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.i = 0
        self.calls: list[dict] = []

    def generate_stream(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        text = self.outputs[self.i]
        self.i += 1
        cb = kwargs.get("on_response_chunk")
        if cb:
            cb(text)
        return GenerationResult(response=text, thinking="")


def test_polish_discard_when_too_short() -> None:
    assert should_discard_polish("abcdef", "ab")


def test_skill_loading_and_final_assembly(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "one.md").write_text("# one\n## Purpose\nX", encoding="utf-8")

    outputs = [
        '{"characters":[],"setting":"s","tone":"t","plot_state":"p","open_loops":[],"foreshadowing":[],"must_preserve":[],"style_notes":[]}',
        '{"intent":"i","focus_character":"c","scene_goal":"g","selected_skill":"one","reason":"r","avoid":[],"ending_style":"hook","length_target":"short"}',
        "part one",
        "part one polished",
        '{"characters":[],"setting":"s","tone":"t","plot_state":"p2","open_loops":[],"foreshadowing":[],"must_preserve":[],"style_notes":[]}',
        '{"intent":"i2","focus_character":"c","scene_goal":"g","selected_skill":"one","reason":"r","avoid":[],"ending_style":"hook","length_target":"short"}',
        "part two",
        "p2",
    ]
    fake = FakeClient(outputs)
    result = run_pipeline(
        input_text="start",
        skills_dir=skills_dir,
        config=PipelineConfig(iterations=2, retry_short_output=False),
        client=fake,
    )
    assert "part one polished" in result.continuation
    assert "part two" in result.continuation
    assert len(result.artifacts) == 2
    assert "latest_summary" in result.story_memory


def test_writer_retry_triggers_on_short_output(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "one.md").write_text("# one\n## Purpose\nX", encoding="utf-8")
    outputs = [
        '{"characters":[],"setting":"s","tone":"t","plot_state":"p","open_loops":[],"foreshadowing":[],"must_preserve":[],"style_notes":[]}',
        '{"intent":"i","focus_character":"c","scene_goal":"g","selected_skill":"one","reason":"r","avoid":[],"ending_style":"hook","length_target":"short"}',
        "short",
        "x" * 1700,
    ]
    fake = FakeClient(outputs)
    result = run_pipeline(
        input_text="start",
        skills_dir=skills_dir,
        config=PipelineConfig(iterations=1, no_polish=True, min_part_chars=1500, retry_short_output=True),
        client=fake,
    )
    assert len(result.artifacts[0].writer_part) >= 1500
    writer_prompts = [c["prompt"] for c in fake.calls if "Write the next continuation" in c["prompt"]]
    assert len(writer_prompts) == 2
    assert "前回の出力は短すぎました" in writer_prompts[1]


def test_story_memory_is_compact_and_writer_uses_selected_skill_only(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "one.md").write_text("# one\none-full-text", encoding="utf-8")
    (skills_dir / "two.md").write_text("# two\ntwo-full-text", encoding="utf-8")
    outputs = [
        '{"characters":["a"],"setting":"s","tone":"t","plot_state":"summary","open_loops":[],"foreshadowing":[],"must_preserve":[],"style_notes":[]}',
        '{"intent":"i","focus_character":"c","scene_goal":"g","selected_skill":"two","reason":"r","avoid":[],"ending_style":"hook","length_target":"short"}',
        "x" * 1700,
    ]
    fake = FakeClient(outputs)
    result = run_pipeline(
        input_text="start",
        skills_dir=skills_dir,
        config=PipelineConfig(iterations=1, no_polish=True),
        client=fake,
    )
    assert "working_body" not in result.story_memory
    assert result.story_memory["used_skills"] == ["two"]
    writer_prompt = next(c["prompt"] for c in fake.calls if "Write the next continuation" in c["prompt"])
    assert "two-full-text" in writer_prompt
    assert "one-full-text" not in writer_prompt


def test_director_receives_skill_summaries_not_full_content(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "one.md").write_text("# one\nsummary-one\nLONG-CONTENT-ONE", encoding="utf-8")
    outputs = [
        '{"characters":[],"setting":"s","tone":"t","plot_state":"p","open_loops":[],"foreshadowing":[],"must_preserve":[],"style_notes":[]}',
        '{"intent":"i","focus_character":"c","scene_goal":"g","selected_skill":"one","reason":"r","avoid":[],"ending_style":"hook","length_target":"short"}',
        "x" * 1700,
    ]
    fake = FakeClient(outputs)
    run_pipeline(
        input_text="start",
        skills_dir=skills_dir,
        config=PipelineConfig(iterations=1, no_polish=True),
        client=fake,
    )
    director_prompt = next(c["prompt"] for c in fake.calls if "You are a story director." in c["prompt"])
    assert "summary-one" in director_prompt
    assert "LONG-CONTENT-ONE" not in director_prompt


def test_director_must_select_loaded_skill(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "one.md").write_text("# one\n## Purpose\nX", encoding="utf-8")

    outputs = [
        '{"characters":[],"setting":"s","tone":"t","plot_state":"p","open_loops":[],"foreshadowing":[],"must_preserve":[],"style_notes":[]}',
        '{"intent":"i","focus_character":"c","scene_goal":"g","selected_skill":"not_loaded","reason":"r","avoid":[],"ending_style":"hook","length_target":"short"}',
    ]
    fake = FakeClient(outputs)
    with pytest.raises(ValueError, match="Director selected unknown skill"):
        run_pipeline(
            input_text="start",
            skills_dir=skills_dir,
            config=PipelineConfig(iterations=1, no_polish=True),
            client=fake,
        )
