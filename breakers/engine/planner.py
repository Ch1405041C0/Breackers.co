from __future__ import annotations

from .registry import AgentRegistry
from .state import AgenticRunState


def default_planner(state: AgenticRunState, registry: AgentRegistry) -> list[str]:
    """Deterministic first planner for Breakers Agentic Engine v1.

    Cycle 1 performs broad analysis. Later cycles focus on agents that can
    reassess gaps and residual risk. This can later be replaced by an LLM-backed
    planner without changing the engine contract.
    """

    available = set(registry.names())

    if state.cycle <= 1:
        preferred = [
            "requirements",
            "risk",
            "coverage",
            "evidence",
        ]
    else:
        preferred = [
            "risk",
            "coverage",
            "evidence",
        ]

    return [name for name in preferred if name in available]
