import json

from breakers.engine.integration import analyze_scan_report
from breakers.memory import JsonMemoryStore
from breakers.providers import ModelResponse


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


def test_memory_store_persists_and_recalls(tmp_path):
    store = JsonMemoryStore(tmp_path / "memory.json")
    store.remember("scan", "project-a", {"risk": "auth"})
    recalled = store.recall("scan", "project-a")
    assert len(recalled) == 1
    assert recalled[0]["payload"]["risk"] == "auth"


def test_agentic_scan_recalls_previous_run(tmp_path):
    store = JsonMemoryStore(tmp_path / "memory.json")
    report = {
        "source": {"type": "repository", "target": "project-a"},
        "analyzers": ["repository"],
        "findings": [{"type": "evidence", "value": "first"}],
        "risks": [{"id": "R1"}],
        "risk_summary": {"identified": 1, "limitations": []},
        "requirements": ["login works"],
    }

    provider = TestProvider()
    first = analyze_scan_report(report, memory_store=store, model_provider=provider)
    second = analyze_scan_report(report, memory_store=store, model_provider=provider)

    assert first["memory"]["recalled"] == 0
    assert second["memory"]["recalled"] == 1
    assert second["context"]["memory"][0]["payload"]["run_id"] == first["run_id"]
