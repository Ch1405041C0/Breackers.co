from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ModelRequest:
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    system: str = ""


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
    vendor-specific SDK.
    """

    name: str

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...

    def health(self) -> dict[str, Any]:
        ...
