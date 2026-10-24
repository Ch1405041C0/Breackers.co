from __future__ import annotations

import os

from .ollama import OllamaProvider


def _build_provider(provider: str, *, model: str):
    if provider == "ollama":
        return OllamaProvider(
            base_url=os.getenv("BREAKERS_OLLAMA_URL", "http://127.0.0.1:11434"),
            model=model,
        )
    raise ValueError(f"Unsupported model provider: {provider}")


def build_model_provider():
    """Build the configured text/reasoning provider.

    Default is deliberately local/private. A cloud provider must be selected
    explicitly; Breakers never silently sends customer material to a third party.
    """
    provider = os.getenv("BREAKERS_MODEL_PROVIDER", "ollama").strip().lower()
    model = os.getenv("BREAKERS_OLLAMA_MODEL", "qwen3:8b")
    return _build_provider(provider, model=model)


def build_vision_provider():
    """Build an optional vision-capable provider without hard-coding a model.

    If no dedicated vision model is configured, Breakers reuses the main model
    only when that model actually declares vision capability. Otherwise None is
    returned and document coverage remains partial rather than pretending that
    images were analyzed.
    """
    provider_name = os.getenv(
        "BREAKERS_VISION_PROVIDER",
        os.getenv("BREAKERS_MODEL_PROVIDER", "ollama"),
    ).strip().lower()
    model = os.getenv("BREAKERS_VISION_MODEL", "").strip()

    if model:
        provider = _build_provider(provider_name, model=model)
        return provider if provider.capabilities().vision else None

    provider = build_model_provider()
    return provider if provider.capabilities().vision else None
