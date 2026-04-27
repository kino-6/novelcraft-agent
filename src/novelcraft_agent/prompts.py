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
        "You are a story analyzer. Output JSON only with this exact shape:\n"
        f"{json.dumps(ANALYZER_SCHEMA, ensure_ascii=False)}\n"
        "Use concise strings/lists and no extra keys.\n\n"
        "Recent novel context:\n"
        f"{context}"
    )


def director_prompt(context: str, analysis: dict[str, Any], skill_names: list[str]) -> str:
    return (
        "You are a story director. Choose one next move and exactly one selected_skill from this list:\n"
        f"{json.dumps(skill_names, ensure_ascii=False)}\n"
        "Output JSON only with this exact shape:\n"
        f"{json.dumps(DIRECTION_SCHEMA, ensure_ascii=False)}\n"
        "Do not choose a skill outside the list.\n\n"
        f"Analysis JSON:\n{json.dumps(analysis, ensure_ascii=False)}\n\n"
        f"Recent context:\n{context}"
    )


def writer_prompt(
    context: str,
    analysis: dict[str, Any],
    direction: dict[str, Any],
    selected_skill: str,
) -> str:
    return (
        "Write the next continuation of the novel in body text only.\n"
        "Do not add headings, explanations, bullets, or analysis.\n"
        "Do not finish the whole story.\n"
        "Keep continuity with context and respect analysis + direction + skill.\n\n"
        f"Analysis:\n{json.dumps(analysis, ensure_ascii=False)}\n\n"
        f"Direction:\n{json.dumps(direction, ensure_ascii=False)}\n\n"
        f"Skill:\n{selected_skill}\n\n"
        f"Context:\n{context}"
    )


def polish_prompt(text: str) -> str:
    return (
        "Lightly polish the passage. Fix typos, awkward line breaks, and obvious wording inconsistencies.\n"
        "Do not rewrite plot, do not add content, do not aggressively shorten.\n"
        "Output only polished body text.\n\n"
        f"Text:\n{text}"
    )
