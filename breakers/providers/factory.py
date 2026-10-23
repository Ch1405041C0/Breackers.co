from __future__ import annotations

import os

from .ollama import OllamaProvider


def build_model_provider():
    """Build the configured AI provider without coupling Breakers to a vendor.

    Default is deliberately local/private. A cloud provider must be selected
    explicitly; Breakers never silently sends customer material to a third party.
    """
    provider = os.getenv("BREAKERS_MODEL_PROVIDER", "ollama").strip().lower()

    if provider == "ollama":
        return OllamaProvider(
            base_url=os.getenv("BREAKERS_OLLAMA_URL", "http://127.0.0.1:11434"),
            model=os.getenv("BREAKERS_OLLAMA_MODEL", "qwen3:8b"),
        )

    raise ValueError(f"Unsupported BREAKERS_MODEL_PROVIDER: {provider}")
