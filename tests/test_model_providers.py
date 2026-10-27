import json

from breakers.providers import ModelRequest, OllamaProvider
from breakers.providers.factory import build_model_provider, build_vision_provider


def test_provider_defaults_to_private_local_ollama(monkeypatch):
    monkeypatch.delenv("BREAKERS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("BREAKERS_OLLAMA_URL", raising=False)
    monkeypatch.delenv("BREAKERS_OLLAMA_BASE_URL", raising=False)
    provider = build_model_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "http://127.0.0.1:11434"


def test_scan_model_and_both_ollama_url_variables_are_honored(monkeypatch):
    monkeypatch.setenv("BREAKERS_MODEL_PROVIDER", "ollama")
    monkeypatch.setenv("BREAKERS_OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("BREAKERS_OLLAMA_BASE_URL", "http://legacy-host:11434")
    monkeypatch.delenv("BREAKERS_OLLAMA_URL", raising=False)
    provider = build_model_provider()
    assert provider.model == "qwen3:8b"
    assert provider.base_url == "http://legacy-host:11434"

    monkeypatch.setenv("BREAKERS_OLLAMA_URL", "http://scan-host:11434")
    assert build_model_provider().base_url == "http://scan-host:11434"


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


def test_ollama_generation_disables_thinking_and_reports_actual_model_and_sizes(monkeypatch):
    provider = OllamaProvider(model="qwen3:8b")
    sent = {}

    def fake_post(path, payload):
        sent.update(payload)
        assert path == "/api/generate"
        return {
            "model": "qwen3:8b",
            "response": '{"findings":[],"gaps":[],"decisions":[]}',
            "total_duration": 5_000_000,
            "prompt_eval_count": 22,
            "eval_count": 8,
        }

    monkeypatch.setattr(provider, "_post", fake_post)
    context = {"evidence": [{"value": "á"}]}
    response = provider.generate(ModelRequest(task="Analyze", context=context))
    metadata = response.raw["_breakers_observability"]
    assert sent["model"] == "qwen3:8b"
    assert sent["think"] is False
    assert sent["format"] == "json"
    assert sent["stream"] is False
    assert response.model == "qwen3:8b"
    assert metadata["context_bytes"] == len(json.dumps(context, ensure_ascii=False).encode("utf-8"))
    assert metadata["payload_bytes"] > metadata["context_bytes"]
    assert metadata["thinking_enabled"] is False
    assert metadata["ollama_total_duration_ms"] == 5
    assert metadata["prompt_eval_count"] == 22
    assert metadata["eval_count"] == 8


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
