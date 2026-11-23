from breakers.engine.integration import analyze_scan_report, context_from_scan_report
from breakers.memory import JsonMemoryStore
from breakers.providers import ModelResponse
import json
import logging


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
    class TestProvider:
        name = "test"

        def generate(self, request):
            return ModelResponse(
                content=json.dumps({"findings": [], "gaps": [], "decisions": []}),
                provider=self.name,
                model="test-model",
            )

        def health(self):
            return {"ok": True}

    analysis = analyze_scan_report(report, model_provider=TestProvider())
    assert analysis["status"] == "completed"
    assert any(item.get("type") == "scope_gap_detected" for item in analysis["decisions"])


def test_scan_invokes_ai_once_and_logs_call_telemetry(monkeypatch, tmp_path, caplog):
    class RecordingProvider:
        name = "ollama"
        model = "qwen3:8b"

        def __init__(self):
            self.calls = 0

        def generate(self, request):
            self.calls += 1
            assert request.context
            return ModelResponse(
                content=json.dumps({"findings": [], "gaps": [], "decisions": []}),
                provider=self.name,
                model=self.model,
                raw={
                    "_breakers_observability": {
                        "duration_ms": 1234,
                        "context_bytes": 512,
                        "payload_bytes": 768,
                        "thinking_enabled": False,
                        "prompt_eval_count": 60,
                        "eval_count": 20,
                        "ollama_total_duration_ms": 1200,
                    }
                },
            )

        def health(self):
            return {"ok": True, "model": self.model}

    provider = RecordingProvider()
    monkeypatch.setattr("breakers.engine.integration.default_evaluator", lambda state: False)
    caplog.set_level(logging.INFO, logger="app.scan")
    analysis = analyze_scan_report(
        {"source": {"type": "repository", "target": "demo"}, "findings": []},
        max_cycles=3,
        memory_store=JsonMemoryStore(tmp_path / "memory.json"),
        model_provider=provider,
        job_id="job-telemetry",
    )
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "app.scan"
    ]

    assert provider.calls == 1
    assert sum(event["event"] == "analyzer_started" and event["name"] == "IA" for event in events) == 1
    completed = next(
        event
        for event in events
        if event["event"] == "analyzer_completed" and event["name"] == "IA"
    )
    assert completed["model"] == "qwen3:8b"
    assert completed["duration_ms"] == 1234
    assert completed["context_bytes"] == 512
    assert completed["payload_bytes"] == 768
    assert completed["thinking_enabled"] is False
    assert all(item["type"] != "ai_analysis_unavailable" for item in analysis["decisions"])
