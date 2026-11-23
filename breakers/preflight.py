from __future__ import annotations

from typing import Any

from breakers.agents import build_quality_agent_registry
from breakers.engine.evaluator import default_evaluator
from breakers.engine.loop import AgenticEngine
from breakers.engine.planner import default_planner


def run_quality_preflight(
    source: dict[str, Any],
    *,
    evidence_fragments: list[dict[str, Any]] | None = None,
    requirements: list[Any] | None = None,
    quality_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Understand evidence and establish quality criteria before selecting engines.

    This stage is intentionally engine-free and model-free. It gives BREAKERS a
    deterministic, auditable context baseline. A model-backed analyst may refine the
    baseline later, but external technical engines must not run here.
    """
    engine = AgenticEngine(
        registry=build_quality_agent_registry(),
        planner=default_planner,
        evaluator=default_evaluator,
    )
    state = engine.run(
        objective=(
            "Understand what the supplied evidence represents and establish grounded, "
            "measurable quality criteria before any technical engine is selected."
        ),
        context={
            "scan_source": dict(source or {}),
            "evidence_fragments": list(evidence_fragments or []),
            "requirements": list(requirements or []),
            "quality_hints": dict(quality_hints or {}),
            "evidence": [],
        },
        max_cycles=1,
    )
    result = state.to_dict()
    result["contract"] = "quality-preflight/v0.1"
    result["execution"] = {
        "technical_engines_started": False,
        "model_calls_started": False,
    }
    return result
