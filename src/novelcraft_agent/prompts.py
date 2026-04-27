from __future__ import annotations

import json
from typing import Any


ANALYZER_SCHEMA = {
    "characters": [],
    "setting": "",
    "tone": "",
    "plot_state": "",
    "open_loops": [],
    "foreshadowing": [],
    "must_preserve": [],
    "style_notes": [],
}


DIRECTION_SCHEMA = {
    "intent": "",
    "focus_character": "",
    "scene_goal": "",
    "selected_skill": "",
    "reason": "",
    "avoid": [],
    "ending_style": "",
    "length_target": "",
}


def analyzer_prompt(context: str) -> str:
    return (
        "You are a story analyzer.\n"
        "必ず日本語で出力してください。英語で本文を書かないでください。\n"
        "Output JSON only with this exact shape:\n"
        f"{json.dumps(ANALYZER_SCHEMA, ensure_ascii=False)}\n"
        "Use concise strings/lists and no extra keys.\n"
        "JSONのキー名はそのまま維持し、値は必ず日本語で書いてください。\n\n"
        "Recent novel context:\n"
        f"{context}"
    )


def director_prompt(story_memory: dict[str, Any], analysis: dict[str, Any], skill_summaries: dict[str, str]) -> str:
    return (
        "You are a story director.\n"
        "必ず日本語で出力してください。英語で本文を書かないでください。\n"
        "Choose one next move and exactly one selected_skill from this list.\n"
        "Directorにはスキル本文を渡しません。以下の要約だけを使って判断してください:\n"
        f"{json.dumps(skill_summaries, ensure_ascii=False)}\n"
        "Output JSON only with this exact shape:\n"
        f"{json.dumps(DIRECTION_SCHEMA, ensure_ascii=False)}\n"
        "Do not choose a skill outside the list.\n"
        "JSONのキー名はそのまま維持し、値は必ず日本語で書いてください。\n\n"
        f"Story memory JSON:\n{json.dumps(story_memory, ensure_ascii=False)}\n\n"
        f"Analysis JSON:\n{json.dumps(analysis, ensure_ascii=False)}\n\n"
    )


def writer_prompt(
    context: str,
    story_memory: dict[str, Any],
    direction: dict[str, Any],
    selected_skill: str,
    retry_for_length: bool = False,
    min_part_chars: int = 1500,
) -> str:
    retry_line = ""
    if retry_for_length:
        retry_line = (
            f"前回の出力は短すぎました。最低{min_part_chars}字以上、日本語で、"
            "会話・行動・描写・状況変化を含めて続きを書き直してください。\n"
        )
    return (
        "Write the next continuation of the novel in Japanese body text only.\n"
        "必ず日本語で出力してください。英語で本文を書かないでください。\n"
        "Do not add headings, explanations, bullets, or analysis.\n"
        "Do not finish the whole story.\n"
        "Keep continuity with context and respect story_memory + direction + selected skill.\n"
        f"{retry_line}\n"
        f"Story memory:\n{json.dumps(story_memory, ensure_ascii=False)}\n\n"
        f"Direction:\n{json.dumps(direction, ensure_ascii=False)}\n\n"
        f"Selected skill content:\n{selected_skill}\n\n"
        f"Context:\n{context}"
    )


def polish_prompt(text: str) -> str:
    return (
        "Lightly polish the Japanese passage. Fix typos, awkward line breaks, and obvious wording inconsistencies.\n"
        "必ず日本語で出力してください。英語で本文を書かないでください。\n"
        "Do not rewrite plot, do not add content, and do not compress or aggressively shorten.\n"
        "Output only polished Japanese novel body text.\n\n"
        f"Text:\n{text}"
    )
