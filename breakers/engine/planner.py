from __future__ import annotations

from .registry import AgentRegistry
from .state import AgenticRunState


def default_planner(state: AgenticRunState, registry: AgentRegistry) -> list[str]:
    """Deterministic planner for Breakers Agentic Engine v1.

    Rules remain authoritative. When an AI agent is registered it is used as an
    additional analyst, never as the only source of quality decisions.
    """

    available = set(registry.names())

    if state.cycle <= 1:
        preferred = [
            "requirements",
            "risk",
            "coverage",
            "evidence",
            "ai_risk",
        ]
    else:
        preferred = [
            "risk",
            "coverage",
            "evidence",
            "ai_risk",
        ]

    return [name for name in preferred if name in available]
