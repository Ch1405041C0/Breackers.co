import json

from breakers.providers import ModelRequest, OllamaProvider
from breakers.providers.factory import build_model_provider


def test_provider_defaults_to_private_local_ollama(monkeypatch):
    monkeypatch.delenv("BREAKERS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("BREAKERS_OLLAMA_URL", raising=False)
    provider = build_model_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "http://127.0.0.1:11434"


def test_ollama_provider_uses_provider_neutral_request(monkeypatch):
    provider = OllamaProvider(model="test-model")

    def fake_post(path, payload):
        assert path == "/api/generate"
        assert payload["model"] == "test-model"
        assert payload["format"] == "json"
        return {"response": json.dumps({"findings": [], "gaps": []})}

    monkeypatch.setattr(provider, "_post", fake_post)
    response = provider.generate(ModelRequest(task="Analyze risk", context={"risk": "R1"}))
    assert response.provider == "ollama"
    assert response.model == "test-model"
    assert "findings" in response.content
