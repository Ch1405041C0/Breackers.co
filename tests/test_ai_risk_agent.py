import json

from breakers.agents.ai import build_ai_risk_agent
from breakers.providers import ModelResponse


class FakeProvider:
    name = "fake-private"

    def generate(self, request):
        return ModelResponse(
            content=json.dumps({
                "findings": [{"type": "ai_risk", "value": "MFA bypass"}],
                "gaps": [{"type": "coverage_gap", "message": "MFA failure not tested"}],
                "decisions": [{"type": "recommend_test", "scenario": "MFA failure"}],
            }),
            provider=self.name,
            model="qa-model",
        )

    def health(self):
        return {"ok": True}


class OfflineProvider(FakeProvider):
    name = "offline"

    def generate(self, request):
        raise ConnectionError("provider unavailable")

    def health(self):
        return {"ok": False}


class FailingProvider(FakeProvider):
    def generate(self, request):
        raise TimeoutError("Ollama generation exceeded its configured timeout")


def test_ai_agent_returns_structured_model_analysis():
    agent = build_ai_risk_agent(FakeProvider())
    result = agent({"objective": "login", "cycle": 1, "context": {"requirements": ["login"]}})
    assert result["findings"][0]["value"] == "MFA bypass"
    assert result["gaps"][0]["type"] == "coverage_gap"
    assert any(item["type"] == "ai_analysis_completed" for item in result["decisions"])


def test_ai_failure_does_not_stop_breakers():
    agent = build_ai_risk_agent(OfflineProvider())
    result = agent({"objective": "login", "cycle": 1, "context": {}})
    assert result["findings"] == []
    assert result["gaps"] == []
    assert result["decisions"][0]["type"] == "ai_analysis_unavailable"


def test_ai_agent_sends_deduplicated_source_and_quality_context_only():
    provider = FakeProvider()
    captured = {"schema": None}
    original_generate = provider.generate

    def capture(request):
        captured["context"] = request.context
        captured["schema"] = request.response_schema
        return original_generate(request)

    provider.generate = capture
    agent = build_ai_risk_agent(provider)
    agent({
        "objective": "objective",
        "cycle": 1,
        "context": {
            "requirements": ["login", "login"],
            "risks": [{"id": "R1"}],
            "evidence": [{"id": "E1"}],
            "evidence_fragments": [
                {"reference": "requirements.md#1", "text": "login requires authentication"},
                {"reference": "requirements.md#1", "text": "login requires authentication"},
            ],
            "limitations": [],
            "requested_scenarios": ["valid login"],
            "discovered_scenarios": ["locked account"],
            "memory": [{"payload": {"findings": [{"value": "old"}]}}],
        },
        "findings": [
            {"type": "evidence_understanding", "value": {"inferred_profiles": [{"id": "security"}]}},
            {"type": "quality_context", "value": {"quality_focus": ["security"]}},
            {"type": "quality_criterion", "value": {"id": "QC-001", "focus": "security"}},
            {"type": "quality_evidence_need", "value": {"criterion_id": "QC-001", "evidence_required": ["access_controls"]}},
            {"type": "quality_context", "value": {"quality_focus": ["security"]}},
        ],
        "gaps": [{"value": "not forwarded directly"}],
    })

    assert captured["context"] == {
        "requirements": ["login"],
        "risks": [{"id": "R1"}],
        "evidence": [{"id": "E1"}],
        "evidence_fragments": [{"reference": "requirements.md#1", "text": "login requires authentication"}],
        "limitations": [],
        "requested_scenarios": ["valid login"],
        "discovered_scenarios": ["locked account"],
        "evidence_understanding": [{"inferred_profiles": [{"id": "security"}]}],
        "quality_context": [{"quality_focus": ["security"]}],
        "quality_criteria": [{"id": "QC-001", "focus": "security"}],
        "quality_evidence_needs": [{"criterion_id": "QC-001", "evidence_required": ["access_controls"]}],
    }
    assert captured["schema"]["required"] == ["findings", "gaps", "decisions"]


def test_ai_generation_error_is_preserved_and_distinguished_from_unavailable():
    result = build_ai_risk_agent(FailingProvider())({
        "objective": "login",
        "cycle": 1,
        "context": {},
    })
    decision = result["decisions"][0]
    assert decision["type"] == "ai_analysis_failed"
    assert decision["error_type"] == "TimeoutError"
    assert decision["error"] == "Ollama generation exceeded its configured timeout"
