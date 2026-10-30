from breakers.agents import build_core_agent_registry
from breakers.evidence_understanding import understand_evidence
from breakers.preflight import run_quality_preflight


def _context(text: str, source: dict | None = None):
    return {
        "scan_source": source or {"input_type": "file", "subtype": "document", "target": "evidence.txt"},
        "evidence_fragments": [{"text": text, "reference": "evidence.txt#fragment-1"}],
        "requirements": [],
        "evidence": [],
    }


def _profile_ids(result):
    return [item["id"] for item in result["inferred_profiles"]]


def test_performance_context_is_inferred_from_content_not_extension():
    result = understand_evidence(_context(
        "Concurrent users, response time, throughput and load profile must be measured."
    ))
    assert "performance" in _profile_ids(result)
    assert "performance_efficiency" in result["quality_focus_hints"]
    assert "performance_metrics" in result["semantic_evidence_types"]


def test_security_context_is_inferred_from_controls_and_sensitive_assets():
    result = understand_evidence(_context(
        "Sensitive customer data requires authentication, authorization and encryption."
    ))
    assert "security" in _profile_ids(result)
    assert "security" in result["quality_focus_hints"]
    assert "security_controls" in result["semantic_evidence_types"]


def test_mobile_context_is_inferred_from_runtime_conditions():
    result = understand_evidence(_context(
        "Android mobile app must preserve data while switching connectivity and screen orientation."
    ))
    assert "mobile" in _profile_ids(result)
    assert "compatibility" in result["quality_focus_hints"]


def test_ai_context_is_inferred_from_dataset_bias_and_explainability():
    result = understand_evidence(_context(
        "The machine learning model uses a training dataset and must be checked for bias and explainability."
    ))
    assert "ai_ml" in _profile_ids(result)
    assert "data_quality" in result["quality_focus_hints"]
    assert "ai_system" in result["semantic_evidence_types"]


def test_acceptance_context_is_inferred_from_user_story_and_acceptance_criteria():
    result = understand_evidence(_context(
        "User story: customer transfers funds. Acceptance criteria define the business rule and expected result."
    ))
    assert "requirements_acceptance" in _profile_ids(result)
    assert "acceptance_criteria" in result["semantic_evidence_types"]


def test_unknown_document_reports_unknown_instead_of_inventing_context():
    result = understand_evidence(_context("Internal notes for the project."))
    assert result["inferred_profiles"] == []
    assert "semantic_context" in result["unknowns"]
    assert "document_role" in result["unknowns"]


def test_repository_type_alone_does_not_invent_business_domain():
    result = understand_evidence(_context(
        "Python service utilities.",
        source={"input_type": "repository", "subtype": "repository", "target": "repo"},
    ))
    assert result["observed"]["technical_evidence_types"] == ["source_code_repository"]
    assert "repository_purpose" not in result["unknowns"]
    assert result["policy"]["profile_matches_are_evidence"] is False


def test_quality_registry_keeps_legacy_default_and_adds_quality_agents_explicitly():
    legacy = build_core_agent_registry()
    enriched = build_core_agent_registry(include_quality=True)

    assert legacy.names() == ["coverage", "evidence", "requirements", "risk"]
    assert "evidence_understanding" in enriched.names()
    assert "quality_context" in enriched.names()
    assert "quality_criteria" in enriched.names()


def test_quality_preflight_runs_agents_in_order_without_engines_or_model_calls():
    result = run_quality_preflight(
        {"input_type": "file", "subtype": "document", "target": "payments.md"},
        evidence_fragments=[{
            "reference": "payments.md#fragment-1",
            "text": "Acceptance criteria require authentication and measurable response time for transfers.",
        }],
    )

    completed = [
        item["agent"]
        for item in result["observations"]
        if item.get("kind") == "agent_completed"
    ]
    assert completed == ["evidence_understanding", "quality_context", "quality_criteria"]
    assert any(item.get("type") == "evidence_understanding" for item in result["findings"])
    assert any(item.get("type") == "quality_context" for item in result["findings"])
    assert any(item.get("type") == "quality_criterion" for item in result["findings"])
    assert result["execution"]["technical_engines_started"] is False
    assert result["execution"]["model_calls_started"] is False


def test_quality_preflight_preserves_observed_inferred_unknown_distinction():
    result = run_quality_preflight(
        {"input_type": "file", "subtype": "document", "target": "unknown.md"},
        evidence_fragments=[{"reference": "unknown.md#fragment-1", "text": "Project notes."}],
    )
    understanding = next(
        item["value"] for item in result["findings"]
        if item.get("type") == "evidence_understanding"
    )
    assert understanding["observed"]["technical_evidence_types"] == ["document"]
    assert understanding["inferred_profiles"] == []
    assert understanding["unknowns"]
