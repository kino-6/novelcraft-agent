from pathlib import Path

from novelcraft_agent.io import IterationArtifacts
from novelcraft_agent.pipeline import PipelineConfig, run_pipeline, should_discard_polish
from novelcraft_agent.ollama_client import GenerationResult


class FakeClient:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.i = 0

    def generate_stream(self, **kwargs):  # noqa: ANN003
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
        config=PipelineConfig(iterations=2),
        client=fake,
    )
    assert "part one polished" in result.continuation
    assert "part two" in result.continuation
    assert len(result.artifacts) == 2
