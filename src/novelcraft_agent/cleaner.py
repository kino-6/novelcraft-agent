from __future__ import annotations

import re

ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)
THINK_LINE_RE = re.compile(r"Thinking\.\.\..*?done thinking\.", flags=re.DOTALL | re.IGNORECASE)
FENCE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", flags=re.DOTALL)
HEADING_RE = re.compile(
    r"^\s*(?:続き本文|整えた本文|本文|Continuation|Output|Polished)\s*[:：]\s*",
    flags=re.IGNORECASE | re.MULTILINE,
)


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def remove_thinking(text: str) -> str:
    text = THINK_BLOCK_RE.sub("", text)
    return THINK_LINE_RE.sub("", text)


def remove_code_fences(text: str) -> str:
    while True:
        updated = FENCE_RE.sub(lambda m: m.group(1).strip(), text)
        if updated == text:
            return text
        text = updated


def remove_headings(text: str) -> str:
    return HEADING_RE.sub("", text).strip()


def clean_generated_text(text: str) -> str:
    cleaned = strip_ansi(text)
    cleaned = remove_thinking(cleaned)
    cleaned = remove_code_fences(cleaned)
    cleaned = remove_headings(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_json_block(text: str) -> str:
    """Extract likely JSON body from mixed model output."""
    text = clean_generated_text(text)
    if text.startswith("{") and text.endswith("}"):
        return text
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in text")
    return match.group(0)
