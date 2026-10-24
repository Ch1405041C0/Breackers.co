from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelCapabilities:
    text: bool = True
    vision: bool = False
    tools: bool = False
    thinking: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "text": self.text,
            "vision": self.vision,
            "tools": self.tools,
            "thinking": self.thinking,
        }


@dataclass
class ModelRequest:
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    system: str = ""
    images: list[bytes] = field(default_factory=list)


@dataclass
class ModelResponse:
    content: str
    provider: str
    model: str
    raw: dict[str, Any] = field(default_factory=dict)


class ModelProvider(Protocol):
    """Provider-neutral contract used by Breakers agents.

    Providers may run locally, in Breakers infrastructure, or inside a
    customer's private network. The Agentic Engine must not depend on any
    vendor-specific SDK or model name.
    """

    name: str

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...

    def capabilities(self) -> ModelCapabilities:
        ...

    def health(self) -> dict[str, Any]:
        ...
