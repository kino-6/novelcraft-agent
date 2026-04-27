from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Callable, Iterator, Protocol
from urllib import request

from .cleaner import strip_ansi

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


@dataclass(slots=True)
class GenerationResult:
    response: str
    thinking: str


class TextGenerationClient(Protocol):
    def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        options: dict | None = None,
        on_response_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
    ) -> GenerationResult: ...


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_URL, timeout: float = 300.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        options: dict | None = None,
        on_response_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
    ) -> GenerationResult:
        payload = {"model": model, "prompt": prompt, "stream": True}
        if options:
            payload["options"] = options
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.base_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        response_parts: list[str] = []
        thinking_parts: list[str] = []
        with request.urlopen(req, timeout=self.timeout) as resp:
            for item in self._iter_json_lines(resp):
                thinking = strip_ansi(item.get("thinking", ""))
                text = strip_ansi(item.get("response", ""))
                if thinking:
                    thinking_parts.append(thinking)
                    if on_thinking_chunk:
                        on_thinking_chunk(thinking)
                if text:
                    response_parts.append(text)
                    if on_response_chunk:
                        on_response_chunk(text)
                if item.get("done"):
                    break
        return GenerationResult(response="".join(response_parts), thinking="".join(thinking_parts))

    @staticmethod
    def _iter_json_lines(resp) -> Iterator[dict]:
        for raw in resp:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            yield json.loads(line)


class MockOllamaClient:
    """Deterministic client for local testing without an Ollama daemon."""

    def __init__(self) -> None:
        self.iteration = 0

    def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        options: dict | None = None,
        on_response_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
    ) -> GenerationResult:
        _ = model
        _ = options
        _ = on_thinking_chunk
        response = self._response_for_prompt(prompt)
        if on_response_chunk:
            on_response_chunk(response)
        return GenerationResult(response=response, thinking="")

    def _response_for_prompt(self, prompt: str) -> str:
        if prompt.startswith("You are a story analyzer"):
            self.iteration += 1
            return json.dumps(
                {
                    "characters": ["Sample Protagonist"],
                    "setting": "A moonlit library",
                    "tone": "reflective",
                    "plot_state": f"iteration_{self.iteration}",
                    "open_loops": ["hidden letter"],
                    "foreshadowing": ["a locked drawer"],
                    "must_preserve": ["first-person voice"],
                    "style_notes": ["short paragraphs"],
                }
            )

        if prompt.startswith("You are a story director"):
            skills = self._extract_skill_names(prompt)
            selected = skills[0] if skills else "unknown"
            return json.dumps(
                {
                    "intent": "Increase tension while preserving continuity",
                    "focus_character": "Sample Protagonist",
                    "scene_goal": "Reveal a clue and raise a question",
                    "selected_skill": selected,
                    "reason": "First listed skill keeps behavior deterministic",
                    "avoid": ["ending the story"],
                    "ending_style": "hook",
                    "length_target": "short",
                }
            )

        if prompt.startswith("Lightly polish the passage"):
            return "The letter slid free, and a single line changed everything."

        return "The drawer clicked open, and the envelope waited beneath the dust."

    @staticmethod
    def _extract_skill_names(prompt: str) -> list[str]:
        map_match = re.search(r"(\{[^\n]*\})\nOutput JSON only with this exact shape:", prompt)
        if map_match:
            try:
                parsed_map = json.loads(map_match.group(1))
            except json.JSONDecodeError:
                parsed_map = None
            if isinstance(parsed_map, dict):
                return [str(k) for k in parsed_map.keys()]

        marker = "Output JSON only with this exact shape:"
        if marker not in prompt:
            return []
        prefix = prompt.split(marker, 1)[0]
        lines = [line.strip() for line in prefix.splitlines() if line.strip()]
        if not lines:
            return []
        raw = lines[-1]
        try:
            parsed = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return []
