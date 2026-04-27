from novelcraft_agent.prompts import analyzer_prompt, director_prompt, polish_prompt, writer_prompt


def test_all_prompts_include_japanese_instruction() -> None:
    marker = "必ず日本語で出力してください。英語で本文を書かないでください。"
    assert marker in analyzer_prompt("ctx")
    assert marker in director_prompt({}, {}, {"skill": "desc"})
    assert marker in writer_prompt("ctx", {}, {}, "skill-body")
    assert marker in polish_prompt("text")
