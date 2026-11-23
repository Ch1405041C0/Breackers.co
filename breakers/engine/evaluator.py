from __future__ import annotations

from .state import AgenticRunState


def default_evaluator(state: AgenticRunState) -> bool:
    """Stop when there are no unresolved gaps.

    Agentic Engine v1 keeps evaluation intentionally explicit and deterministic.
    Future versions can combine rule-based checks with model judgment.
    """

    unresolved = [gap for gap in state.gaps if not gap.get("resolved", False)]
    return len(unresolved) == 0
