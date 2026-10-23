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
