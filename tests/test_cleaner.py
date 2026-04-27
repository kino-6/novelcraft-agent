from novelcraft_agent.cleaner import extract_json_block, remove_thinking, strip_ansi


def test_strip_ansi() -> None:
    raw = "hello\x1b[K world\x1b[31m!\x1b[0m"
    assert strip_ansi(raw) == "hello world!"


def test_remove_thinking() -> None:
    raw = "start<think>private chain of thought</think>end\nThinking... abc ...done thinking."
    assert remove_thinking(raw) == "startend\n"


def test_extract_json_block_from_fence() -> None:
    raw = "```json\n{\"a\": 1, \"b\": 2}\n```"
    assert extract_json_block(raw) == '{"a": 1, "b": 2}'
