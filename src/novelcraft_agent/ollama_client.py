from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Iterator
from urllib import request

from .cleaner import strip_ansi

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


@dataclass(slots=True)
class GenerationResult:
    response: str
    thinking: str


class MockOllamaClient:
    """Deterministic client for local pipeline smoke tests."""

    def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        on_response_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
    ) -> GenerationResult:
        _ = (model, on_thinking_chunk)
        if "You are a story analyzer." in prompt:
            response = (
                '{"characters":["Ari"],"setting":"workshop","tone":"tense","plot_state":"unstable",'
                '"open_loops":["letter"],"foreshadowing":[],"must_preserve":["voice"],"style_notes":[]}'
            )
        elif "You are a story director." in prompt:
            response = (
                '{"intent":"advance","focus_character":"protagonist","scene_goal":"move scene",'
                '"selected_skill":"character_conflict","reason":"raise stakes","avoid":["summary"],'
                '"ending_style":"hook","length_target":"short"}'
            )
        elif "Lightly polish the passage." in prompt:
            response = "The corridor light trembled once, and Ari kept walking."
        else:
            response = "Ari folded the letter and stepped into the dark corridor."
        if on_response_chunk:
            on_response_chunk(response)
        return GenerationResult(response=response, thinking="")


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_URL, timeout: float = 300.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def generate_stream(
        self,
        *,
        model: str,
        prompt: str,
        on_response_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
    ) -> GenerationResult:
        body = json.dumps({"model": model, "prompt": prompt, "stream": True}).encode("utf-8")
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
