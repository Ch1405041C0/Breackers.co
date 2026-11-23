from breakers.agents import build_core_agent_registry
from breakers.engine.evaluator import default_evaluator
from breakers.engine.loop import AgenticEngine
from breakers.engine.planner import default_planner


def test_core_registry_contains_breakers_qa_agents():
    registry = build_core_agent_registry()
    assert registry.names() == ["coverage", "evidence", "requirements", "risk"]


def test_engine_surfaces_scenarios_outside_requested_scope():
    engine = AgenticEngine(build_core_agent_registry(), default_planner, default_evaluator)
    state = engine.run(
        "Analyze login quality",
        context={
            "requirements": ["User can log in"],
            "requested_scenarios": ["valid login"],
            "discovered_scenarios": ["valid login", "locked user", "expired password", "MFA failure"],
            "risks": ["authentication bypass"],
            "evidence": ["requirements.md"],
        },
    )
    outside = [item["value"] for item in state.findings if item.get("type") == "scenario_outside_requested_scope"]
    assert outside == ["MFA failure", "expired password", "locked user"]
    assert any(item.get("type") == "scope_gap_detected" for item in state.decisions)


def test_engine_records_missing_evidence_as_gap():
    engine = AgenticEngine(build_core_agent_registry(), default_planner, default_evaluator)
    state = engine.run(
        "Analyze requirements",
        context={"requirements": ["Payment must be idempotent"]},
        max_cycles=1,
    )
    assert any(item.get("type") == "missing_evidence" for item in state.gaps)
