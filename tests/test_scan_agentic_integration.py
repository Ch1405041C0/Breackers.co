from breakers.engine.integration import analyze_scan_report, context_from_scan_report


def test_scan_report_becomes_agentic_context():
    report = {
        "source": {"type": "repository", "target": "demo"},
        "analyzers": ["repository"],
        "findings": [{"rule": "secret", "severity": "high"}],
        "risks": [{"id": "R1", "severity": "high"}],
        "risk_summary": {"identified": 1, "limitations": ["dynamic execution not performed"]},
    }
    context = context_from_scan_report(report)
    assert context["risks"] == report["risks"]
    assert context["evidence"]
    assert context["limitations"] == ["dynamic execution not performed"]


def test_agentic_analysis_runs_over_scan_report():
    report = {
        "source": {"type": "functional_document", "target": "requirements.md"},
        "analyzers": ["requirements"],
        "findings": [{"type": "requirement_evidence", "value": "login"}],
        "risks": [{"id": "AUTH", "severity": "medium"}],
        "risk_summary": {"identified": 1, "limitations": []},
        "requirements": ["User can log in"],
        "requested_scenarios": ["valid login"],
        "discovered_scenarios": ["valid login", "locked account"],
    }
    analysis = analyze_scan_report(report)
    assert analysis["status"] == "completed"
    assert any(item.get("type") == "scope_gap_detected" for item in analysis["decisions"])
