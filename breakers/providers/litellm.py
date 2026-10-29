from __future__ import annotations

import json
import os
from time import perf_counter
from typing import Any
from urllib import error, request

from .base import ModelCapabilities, ModelRequest, ModelResponse


class LiteLLMProviderError(RuntimeError):
    def __init__(self, message: str, metadata: dict[str, Any]) -> None:
        super().__init__(message)
        self.metadata = metadata


class LiteLLMProvider:
    name = "litellm"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 120,
        api_key: str | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("LiteLLM base URL must not be empty")
        if not model.strip():
            raise ValueError("LiteLLM model must not be empty")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.api_key = api_key or os.getenv("BREAKERS_LITELLM_API_KEY")

    @property
    def chat_completions_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    @property
    def health_url(self) -> str:
        root_url = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        return f"{root_url}/health/liveliness"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        return headers

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self.chat_completions_url,
            data=body,
            headers=self._headers(),
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get(self, url: str) -> None:
        req = request.Request(url, headers=self._headers(), method="GET")
        with request.urlopen(req, timeout=min(self.timeout, 5)) as response:
            response.read()

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(text=True)

    def generate(self, model_request: ModelRequest) -> ModelResponse:
        if model_request.images:
            raise ValueError("LiteLLM provider does not declare vision capability")

        context_json = json.dumps(
            model_request.context,
            ensure_ascii=False,
            default=str,
        ) if model_request.context else ""
        user_content = model_request.task
        if context_json:
            user_content += "\n\nBREAKERS CONTEXT:\n" + context_json

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": model_request.system},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "max_tokens": 256,
            "reasoning_effort": "none",
            "stream": False,
        }
        if model_request.response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "breakers_scan_analysis",
                    "strict": True,
                    "schema": model_request.response_schema,
                },
            }

        payload_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        context_bytes = len(context_json.encode("utf-8"))
        started = perf_counter()
        try:
            envelope = self._post(payload)
        except Exception as exc:
            metadata = {
                "model": self.model,
                "duration_ms": round((perf_counter() - started) * 1000),
                "context_bytes": context_bytes,
                "payload_bytes": payload_bytes,
                "thinking_enabled": False,
            }
            raise LiteLLMProviderError(str(exc), metadata) from exc

        try:
            choice = envelope["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("LiteLLM returned non-text message content")
        except (IndexError, KeyError, TypeError) as exc:
            metadata = {
                "model": str(envelope.get("model") or self.model),
                "duration_ms": round((perf_counter() - started) * 1000),
                "context_bytes": context_bytes,
                "payload_bytes": payload_bytes,
                "thinking_enabled": False,
            }
            raise LiteLLMProviderError(
                "LiteLLM returned an invalid chat completion response",
                metadata,
            ) from exc

        returned_model = str(envelope.get("model") or self.model)
        usage = envelope.get("usage") or {}
        metadata = {
            "provider": self.name,
            "requested_model": self.model,
            "model": returned_model,
            "duration_ms": round((perf_counter() - started) * 1000),
            "context_bytes": context_bytes,
            "payload_bytes": payload_bytes,
            "thinking_enabled": False,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "prompt_eval_count": usage.get("prompt_tokens"),
            "eval_count": usage.get("completion_tokens"),
        }
        return ModelResponse(
            content=content,
            provider=self.name,
            model=returned_model,
            raw={**envelope, "_breakers_observability": metadata},
        )

    def health(self) -> dict[str, Any]:
        try:
            self._get(self.health_url)
            return {
                "ok": True,
                "provider": self.name,
                "model": self.model,
            }
        except (OSError, ValueError, error.URLError) as exc:
            return {
                "ok": False,
                "provider": self.name,
                "model": self.model,
                "error": str(exc),
            }
