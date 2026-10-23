from __future__ import annotations

import json
from typing import Any
from urllib import error, request as http_request

from .base import ModelRequest, ModelResponse


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen3:8b", timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = http_request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with http_request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate(self, request: ModelRequest) -> ModelResponse:
        prompt = request.task
        if request.context:
            prompt += "\n\nBREAKERS CONTEXT:\n" + json.dumps(request.context, ensure_ascii=False, default=str)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": request.system,
            "stream": False,
            "format": "json",
        }
        data = self._post("/api/generate", payload)
        return ModelResponse(
            content=str(data.get("response") or ""),
            provider=self.name,
            model=self.model,
            raw=data,
        )

    def health(self) -> dict[str, Any]:
        try:
            req = http_request.Request(f"{self.base_url}/api/tags", method="GET")
            with http_request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            models = [item.get("name") for item in data.get("models") or []]
            return {"ok": True, "provider": self.name, "model": self.model, "available_models": models}
        except (OSError, ValueError, error.URLError) as exc:
            return {"ok": False, "provider": self.name, "model": self.model, "error": str(exc)}
