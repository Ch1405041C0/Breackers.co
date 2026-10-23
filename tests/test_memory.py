from breakers.engine.integration import analyze_scan_report
from breakers.memory import JsonMemoryStore


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

    first = analyze_scan_report(report, memory_store=store)
    second = analyze_scan_report(report, memory_store=store)

    assert first["memory"]["recalled"] == 0
    assert second["memory"]["recalled"] == 1
    assert second["context"]["memory"][0]["payload"]["run_id"] == first["run_id"]
