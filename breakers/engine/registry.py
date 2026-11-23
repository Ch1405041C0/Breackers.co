from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


AgentHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    handler: AgentHandler


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, name: str, description: str, handler: AgentHandler) -> None:
        if name in self._agents:
            raise ValueError(f"agent already registered: {name}")
        self._agents[name] = AgentDefinition(name=name, description=description, handler=handler)

    def get(self, name: str) -> AgentDefinition:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(f"unknown agent: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._agents)
