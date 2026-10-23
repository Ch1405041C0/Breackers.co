from breakers.engine.evaluator import default_evaluator
from breakers.engine.loop import AgenticEngine
from breakers.engine.planner import default_planner
from breakers.engine.registry import AgentRegistry


def test_engine_replans_until_gaps_resolved():
    registry = AgentRegistry()
    calls = {"risk": 0}

    def requirements(_payload):
        return {"findings": [{"type": "requirement", "title": "login"}]}

    def risk(_payload):
        calls["risk"] += 1
        if calls["risk"] == 1:
            return {"gaps": [{"id": "mfa", "title": "MFA not covered", "resolved": False}]}
        return {"gaps": [{"id": "mfa", "title": "MFA covered", "resolved": True}]}

    def coverage(_payload):
        return {}

    def evidence(_payload):
        return {}

    registry.register("requirements", "Analyze requirements", requirements)
    registry.register("risk", "Analyze risk", risk)
    registry.register("coverage", "Analyze coverage", coverage)
    registry.register("evidence", "Analyze evidence", evidence)

    engine = AgenticEngine(registry, default_planner, default_evaluator)
    state = engine.run("validate login", max_cycles=2)

    assert state.cycle == 2
    assert state.status == "completed"
    assert state.completed_reason in {"evaluation_satisfied", "max_cycles_reached"}
    assert calls["risk"] == 2


def test_engine_is_model_agnostic():
    registry = AgentRegistry()
    registry.register("requirements", "Deterministic agent", lambda payload: {})

    engine = AgenticEngine(
        registry,
        planner=lambda state, registry: ["requirements"],
        evaluator=lambda state: True,
    )

    state = engine.run("anything")

    assert state.completed_reason == "evaluation_satisfied"
    assert state.cycle == 1
