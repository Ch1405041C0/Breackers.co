from __future__ import annotations

import base64
import json
from time import perf_counter
from typing import Any
from urllib import error, request as http_request

from .base import ModelCapabilities, ModelRequest, ModelResponse


class OllamaGenerationError(RuntimeError):
    def __init__(self, message: str, metadata: dict[str, Any]) -> None:
        super().__init__(message)
        self.metadata = metadata


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "qwen3:8b", timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._capabilities: ModelCapabilities | None = None

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = http_request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with http_request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def capabilities(self) -> ModelCapabilities:
        if self._capabilities is not None:
            return self._capabilities
        try:
            data = self._post("/api/show", {"model": self.model})
            declared = {str(item).lower() for item in data.get("capabilities") or []}
            self._capabilities = ModelCapabilities(
                text="completion" in declared or not declared,
                vision="vision" in declared,
                tools="tools" in declared,
                thinking="thinking" in declared,
            )
        except (OSError, ValueError, error.URLError):
            self._capabilities = ModelCapabilities()
        return self._capabilities

    def generate(self, request: ModelRequest) -> ModelResponse:
        if request.images and not self.capabilities().vision:
            raise ValueError(f"Model {self.model} does not declare vision capability")
        prompt = request.task
        context_json = ""
        if request.context:
            context_json = json.dumps(request.context, ensure_ascii=False, default=str)
            prompt += "\n\nBREAKERS CONTEXT:\n" + context_json
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": request.system,
            "stream": False,
            "think": False,
            "format": request.response_schema or "json",
            "options": {
                "temperature": 0,
                "num_predict": 256,
                "num_ctx": 8192,
            },
        }
        if request.images:
            payload["images"] = [base64.b64encode(image).decode("ascii") for image in request.images]
        payload_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        started = perf_counter()
        try:
            data = self._post("/api/generate", payload)
        except Exception as exc:
            metadata = {
                "model": self.model,
                "duration_ms": round((perf_counter() - started) * 1000),
                "context_bytes": len(context_json.encode("utf-8")),
                "payload_bytes": payload_bytes,
            }
            raise OllamaGenerationError(str(exc), metadata) from exc
        metadata = {
            "model": str(data.get("model") or self.model),
            "duration_ms": round((perf_counter() - started) * 1000),
            "context_bytes": len(context_json.encode("utf-8")),
            "payload_bytes": payload_bytes,
            "thinking_enabled": False,
            "prompt_eval_count": data.get("prompt_eval_count"),
            "eval_count": data.get("eval_count"),
            "ollama_total_duration_ms": round(data["total_duration"] / 1_000_000)
            if isinstance(data.get("total_duration"), (int, float))
            else None,
        }
        return ModelResponse(
            content=str(data.get("response") or ""),
            provider=self.name,
            model=metadata["model"],
            raw={**data, "_breakers_observability": metadata},
        )

    def health(self) -> dict[str, Any]:
        try:
            req = http_request.Request(f"{self.base_url}/api/tags", method="GET")
            with http_request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            models = [item.get("name") for item in data.get("models") or []]
            return {
                "ok": True,
                "provider": self.name,
                "model": self.model,
                "available_models": models,
                "capabilities": self.capabilities().to_dict(),
            }
        except (OSError, ValueError, error.URLError) as exc:
            return {"ok": False, "provider": self.name, "model": self.model, "error": str(exc)}
