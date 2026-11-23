from __future__ import annotations

from typing import Any, Callable

from .registry import AgentRegistry
from .state import AgenticRunState


Planner = Callable[[AgenticRunState, AgentRegistry], list[str]]
Evaluator = Callable[[AgenticRunState], bool]


class AgenticEngine:
    """Minimal cyclic orchestration core for Breakers.

    The engine itself is model-agnostic: planners and agents can be deterministic,
    local-model backed, cloud-model backed, or mixed.
    """

    def __init__(self, registry: AgentRegistry, planner: Planner, evaluator: Evaluator) -> None:
        self.registry = registry
        self.planner = planner
        self.evaluator = evaluator

    def run(self, objective: str, context: dict[str, Any] | None = None, max_cycles: int = 3) -> AgenticRunState:
        state = AgenticRunState(objective=objective, context=context or {}, max_cycles=max_cycles)

        while state.cycle < state.max_cycles:
            state.next_cycle()
            state.plan = self.planner(state, self.registry)
            state.record("plan_created", agents=list(state.plan))

            if not state.plan:
                state.finish("no_agents_selected")
                break

            for agent_name in state.plan:
                agent = self.registry.get(agent_name)
                payload = {
                    "objective": state.objective,
                    "context": state.context,
                    "cycle": state.cycle,
                    "findings": list(state.findings),
                    "gaps": list(state.gaps),
                }
                result = agent.handler(payload) or {}
                findings = result.get("findings") or []
                gaps = result.get("gaps") or []
                decisions = result.get("decisions") or []
                state.findings.extend(findings)
                state.gaps.extend(gaps)
                state.decisions.extend(decisions)
                state.record(
                    "agent_completed",
                    agent=agent_name,
                    findings=len(findings),
                    gaps=len(gaps),
                    decisions=len(decisions),
                )

            if self.evaluator(state):
                state.finish("evaluation_satisfied")
                break

            state.record("replan_required", gaps=len(state.gaps))

        if state.status != "completed":
            state.finish("max_cycles_reached")

        return state
