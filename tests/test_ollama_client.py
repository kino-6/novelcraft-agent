import json

from novelcraft_agent.ollama_client import OllamaClient


class _FakeResp:
    def __iter__(self):
        yield b'{"response":"ok","done":true}\n'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001,ANN201
        return False


def test_ollama_options_are_passed(monkeypatch) -> None:
    captured: dict = {}

    def _fake_urlopen(req, timeout):  # noqa: ANN001,ANN202
        captured["timeout"] = timeout
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp()

    monkeypatch.setattr("novelcraft_agent.ollama_client.request.urlopen", _fake_urlopen)
    client = OllamaClient()
    client.generate_stream(model="m", prompt="p", options={"num_ctx": 1, "num_predict": 2, "temperature": 0.7, "top_p": 0.8})
    assert captured["body"]["options"]["num_ctx"] == 1
    assert captured["body"]["options"]["num_predict"] == 2
    assert captured["body"]["options"]["temperature"] == 0.7
    assert captured["body"]["options"]["top_p"] == 0.8
