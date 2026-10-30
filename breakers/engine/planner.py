from __future__ import annotations

from .registry import AgentRegistry
from .state import AgenticRunState


def default_planner(state: AgenticRunState, registry: AgentRegistry) -> list[str]:
    """Deterministic planner for Breakers Agentic Engine v1.

    Rules remain authoritative. When evidence/quality-context agents are registered
    they run first so downstream agents reason against explicit semantic context and
    measurable criteria. An AI agent is an additional analyst, never the only source
    of quality decisions.
    """

    available = set(registry.names())

    if state.cycle <= 1:
        preferred = [
            "evidence_understanding",
            "quality_context",
            "quality_criteria",
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
