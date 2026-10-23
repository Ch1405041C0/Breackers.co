from breakers.agents.core import coverage_agent, evidence_agent, risk_agent


def _memory(findings=None, gaps=None):
    return [{"payload": {"findings": findings or [], "gaps": gaps or [], "decisions": []}}]


def test_risk_agent_detects_recurring_new_and_resolved_risks():
    previous = [
        {"type": "risk", "value": {"id": "R1"}},
        {"type": "risk", "value": {"id": "R2"}},
    ]
    result = risk_agent({"context": {"risks": [{"id": "R1"}, {"id": "R3"}], "memory": _memory(previous)}})
    delta = next(item for item in result["decisions"] if item["type"] == "risk_delta")
    assert delta == {"type": "risk_delta", "recurring": 1, "new": 1, "resolved": 1}


def test_coverage_agent_tracks_historical_scope_gaps():
    previous = [
        {"type": "scenario_outside_requested_scope", "value": "MFA failure"},
        {"type": "scenario_outside_requested_scope", "value": "locked user"},
    ]
    result = coverage_agent({"context": {
        "requested_scenarios": ["valid login"],
        "discovered_scenarios": ["valid login", "MFA failure", "expired password"],
        "memory": _memory(previous),
    }})
    delta = next(item for item in result["decisions"] if item["type"] == "coverage_delta")
    assert delta == {"type": "coverage_delta", "persistent": 1, "new": 1, "resolved": 1}


def test_evidence_agent_marks_previous_gap_as_resolved():
    result = evidence_agent({"context": {
        "evidence": [{"type": "scan_source", "value": "repo"}],
        "memory": _memory(gaps=[{"type": "missing_evidence"}]),
    }})
    assert {"type": "evidence_gap_resolved"} in result["decisions"]
