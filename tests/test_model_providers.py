import json

from breakers.providers import ModelRequest, OllamaProvider
from breakers.providers.factory import build_model_provider, build_vision_provider


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


def test_ollama_discovers_vision_capability(monkeypatch):
    provider = OllamaProvider(model="vision-model")

    def fake_post(path, payload):
        assert path == "/api/show"
        assert payload["model"] == "vision-model"
        return {"capabilities": ["completion", "vision", "tools"]}

    monkeypatch.setattr(provider, "_post", fake_post)
    capabilities = provider.capabilities()
    assert capabilities.text is True
    assert capabilities.vision is True
    assert capabilities.tools is True


def test_vision_request_sends_images_only_to_vision_model(monkeypatch):
    provider = OllamaProvider(model="vision-model")
    calls = []

    def fake_post(path, payload):
        calls.append((path, payload))
        if path == "/api/show":
            return {"capabilities": ["completion", "vision"]}
        assert path == "/api/generate"
        assert payload["images"]
        return {"response": "{}"}

    monkeypatch.setattr(provider, "_post", fake_post)
    provider.generate(ModelRequest(task="Analyze image", images=[b"fake-image"]))
    assert calls[-1][0] == "/api/generate"


def test_vision_provider_is_selected_by_capability_not_model_name(monkeypatch):
    monkeypatch.setenv("BREAKERS_MODEL_PROVIDER", "ollama")
    monkeypatch.setenv("BREAKERS_VISION_MODEL", "anything-with-vision")

    def fake_capabilities(self):
        from breakers.providers import ModelCapabilities
        return ModelCapabilities(text=True, vision=self.model == "anything-with-vision")

    monkeypatch.setattr(OllamaProvider, "capabilities", fake_capabilities)
    provider = build_vision_provider()
    assert provider is not None
    assert provider.model == "anything-with-vision"
