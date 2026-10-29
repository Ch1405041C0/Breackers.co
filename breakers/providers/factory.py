from __future__ import annotations

import os

from .litellm import LiteLLMProvider
from .ollama import OllamaProvider


def configured_ollama_base_url() -> str:
    """Support both the SCAN and legacy STRIKE environment variable names."""
    return (
        os.getenv("BREAKERS_OLLAMA_URL")
        or os.getenv("BREAKERS_OLLAMA_BASE_URL")
        or "http://127.0.0.1:11434"
    )


def _env_timeout(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer number of seconds") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _build_provider(provider: str, *, model: str, timeout: int):
    if provider == "ollama":
        return OllamaProvider(
            base_url=configured_ollama_base_url(),
            model=model,
            timeout=timeout,
        )
    if provider == "litellm":
        base_url = os.getenv("BREAKERS_LITELLM_URL", "").strip()
        if not base_url:
            raise ValueError("BREAKERS_LITELLM_URL must be set when using LiteLLM")
        return LiteLLMProvider(
            base_url=base_url,
            model=model,
            timeout=timeout,
            api_key=os.getenv("BREAKERS_LITELLM_API_KEY"),
        )
    raise ValueError(f"Unsupported model provider: {provider}")


def build_model_provider():
    """Build the configured text/reasoning provider.

    Default is deliberately local/private. A cloud provider must be selected
    explicitly; Breakers never silently sends customer material to a third party.
    """
    provider = os.getenv("BREAKERS_MODEL_PROVIDER", "ollama").strip().lower()
    if provider == "litellm":
        model = os.getenv("BREAKERS_LITELLM_MODEL", "").strip()
        if not model:
            raise ValueError("BREAKERS_LITELLM_MODEL must be set when using LiteLLM")
    else:
        model = os.getenv("BREAKERS_OLLAMA_MODEL", "qwen3:8b")
    timeout = _env_timeout("BREAKERS_MODEL_TIMEOUT", 120)
    return _build_provider(provider, model=model, timeout=timeout)


def build_vision_provider():
    """Build an optional vision-capable provider without hard-coding a model.

    Vision gets its own timeout because local multimodal inference can be much
    slower than text generation, especially on first load. If no dedicated
    vision model is configured, Breakers reuses the main model only when it
    actually declares vision capability.
    """
    provider_name = os.getenv(
        "BREAKERS_VISION_PROVIDER",
        os.getenv("BREAKERS_MODEL_PROVIDER", "ollama"),
    ).strip().lower()
    model = os.getenv("BREAKERS_VISION_MODEL", "").strip()
    timeout = _env_timeout("BREAKERS_VISION_TIMEOUT", 600)

    if model:
        provider = _build_provider(provider_name, model=model, timeout=timeout)
        return provider if provider.capabilities().vision else None

    provider = build_model_provider()
    return provider if provider.capabilities().vision else None
