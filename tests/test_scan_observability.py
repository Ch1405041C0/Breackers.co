import json
import logging
from pathlib import Path

import pytest

from breakers.engine.integration import analyze_scan_report
from breakers.memory import JsonMemoryStore
from breakers.orchestrator import run_scan
from breakers.reports import build_public_summary
from breakers.scanners.base import ScanResult
from breakers.scanners import GitleaksScanner, TrivyScanner


@pytest.mark.parametrize(
    ("trivy_available", "gitleaks_available", "expected_status", "expected_engines"),
    [
        (True, True, "completed", ["Trivy", "Gitleaks"]),
        (False, True, "partial", ["Gitleaks"]),
        (True, False, "partial", ["Trivy"]),
        (False, False, "incomplete", []),
    ],
)
def test_repository_scanner_coverage_and_structured_logs(
    monkeypatch,
    tmp_path,
    caplog,
    trivy_available,
    gitleaks_available,
    expected_status,
    expected_engines,
):
    repository = tmp_path / "repo"
    (repository / ".git" / "objects").mkdir(parents=True)
    (repository / "README.md").write_text("demo", encoding="utf-8")
    (repository / ".git" / "objects" / "ignored").write_text("metadata", encoding="utf-8")
    (repository / "Makefile").write_text("all:", encoding="utf-8")

    monkeypatch.setattr(TrivyScanner, "available", lambda self: trivy_available)
    monkeypatch.setattr(GitleaksScanner, "available", lambda self: gitleaks_available)
    monkeypatch.setattr(
        TrivyScanner,
        "scan",
        lambda self, target: ScanResult(self.name, "completed"),
    )
    monkeypatch.setattr(
        GitleaksScanner,
        "scan",
        lambda self, target: ScanResult(self.name, "completed"),
    )
    monkeypatch.setattr(
        "breakers.orchestrator.analyze_scan_report",
        lambda report, job_id=None: {
            "observations": [],
            "decisions": [],
            "model_provider": {"name": "test", "health": {"ok": True}},
        },
    )

    caplog.set_level(logging.INFO, logger="app.scan")
    report = run_scan(str(repository), job_id="job-test")
    events = [json.loads(record.message) for record in caplog.records if record.name == "app.scan"]

    assert report["analysis_status"] == expected_status
    assert report["engines"] == expected_engines
    assert report["score"] == (100 if expected_status == "completed" else None)
    assert all(event["job_id"] == "job-test" for event in events)

    discovered = next(event for event in events if event["event"] == "files_discovered")
    assert discovered["total"] == 2
    assert discovered["by_extension"] == {".md": 1, "[sin_extension]": 1}
    assert ".git" not in str(discovered)

    selected = next(
        event for event in events
        if event["event"] == "analyzers_selected" and event["category"] == "technical"
    )
    assert selected["required_engines"] == ["Trivy", "Gitleaks"]
    assert {event["name"] for event in events if event["event"] == "analyzer_unavailable"} == {
        name
        for name, available in (("Trivy", trivy_available), ("Gitleaks", gitleaks_available))
        if not available
    }
    assert {event["name"] for event in events if event["event"] == "analyzer_completed"} == set(expected_engines)
    completed = next(event for event in events if event["event"] == "scan_completed")
    assert completed["analysis_status"] == expected_status
    assert completed["coverage"] is (expected_status == "completed")
    assert completed["score"] == report["score"]


def test_remote_repository_fetch_is_logged_without_temporary_path(monkeypatch, caplog):
    captured = {}

    def fake_clone(url, destination):
        destination = Path(destination)
        destination.mkdir(parents=True)
        (destination / "README.md").write_text("demo", encoding="utf-8")
        captured["path"] = str(destination)

    monkeypatch.setattr("breakers.orchestrator.clone_repository", fake_clone)
    monkeypatch.setattr("breakers.orchestrator.repository_commit_sha", lambda path: "a" * 40)
    monkeypatch.setattr(TrivyScanner, "available", lambda self: False)
    monkeypatch.setattr(GitleaksScanner, "available", lambda self: False)
    monkeypatch.setattr(
        "breakers.orchestrator.analyze_scan_report",
        lambda report, job_id=None: {"observations": [], "decisions": [], "model_provider": {"health": {"ok": False}}},
    )

    caplog.set_level(logging.INFO, logger="app.scan")
    run_scan("https://github.com/acme/demo", job_id="job-remote")
    messages = [record.message for record in caplog.records if record.name == "app.scan"]
    fetched = next(json.loads(message) for message in messages if '"event":"repository_fetched"' in message)

    assert fetched["success"] is True
    assert fetched["commit_sha"] == "a" * 40
    assert fetched["duration_ms"] >= 0
    assert captured["path"] not in "\n".join(messages)


def test_scanner_failure_is_logged_with_sanitized_error(monkeypatch, tmp_path, caplog):
    repository = tmp_path / "repo"
    repository.mkdir()
    monkeypatch.setattr(TrivyScanner, "available", lambda self: True)
    monkeypatch.setattr(GitleaksScanner, "available", lambda self: False)
    monkeypatch.setattr(
        TrivyScanner,
        "scan",
        lambda self, target: ScanResult(
            self.name,
            "failed",
            error=f"internal failure at {target} with token=private",
        ),
    )
    monkeypatch.setattr(
        "breakers.orchestrator.analyze_scan_report",
        lambda report, job_id=None: {
            "observations": [],
            "decisions": [],
            "model_provider": {"health": {"ok": True}},
        },
    )

    caplog.set_level(logging.INFO, logger="app.scan")
    report = run_scan(str(repository), job_id="job-error")
    events = [json.loads(record.message) for record in caplog.records if record.name == "app.scan"]
    failed = next(event for event in events if event["event"] == "analyzer_failed")

    assert failed["name"] == "Trivy"
    assert failed["status"] == "error"
    assert failed["duration_ms"] >= 0
    assert failed["error"] == "El analizador no pudo completar la ejecución."
    assert str(repository) not in failed["error"]
    assert "private" not in failed["error"]
    assert report["analysis_status"] == "incomplete"
    assert report["score"] is None


def test_ai_unavailable_is_reported_as_unavailable(caplog, tmp_path):
    class OfflineProvider:
        name = "test-offline"

        def generate(self, request):
            raise ConnectionError("private endpoint and token must not be logged")

        def health(self):
            return {"ok": False, "provider": self.name}

    caplog.set_level(logging.INFO, logger="app.scan")
    result = analyze_scan_report(
        {"source": {"type": "repository"}, "findings": []},
        memory_store=JsonMemoryStore(tmp_path / "memory.json"),
        model_provider=OfflineProvider(),
        job_id="job-ai",
    )
    events = [json.loads(record.message) for record in caplog.records if record.name == "app.scan"]

    assert result["model_provider"]["health"]["ok"] is False
    assert sum(item.get("type") == "ai_analysis_unavailable" for item in result["decisions"]) == 1
    ai_error = next(item for item in result["decisions"] if item.get("type") == "ai_analysis_unavailable")
    assert ai_error["error"] == "private endpoint and token must not be logged"
    assert len([event for event in events if event["event"] == "agents_planned"]) == 3
    unavailable = [event for event in events if event["event"] == "analyzer_unavailable" and event["name"] == "IA"]
    assert len(unavailable) == 1
    assert all(event["job_id"] == "job-ai" for event in unavailable)
    assert "private endpoint" not in "\n".join(record.message for record in caplog.records)


def test_incomplete_public_summary_does_not_claim_zero_findings():
    summary = build_public_summary(
        "scan-1",
        "report-1",
        {
            "analysis_status": "incomplete",
            "score": None,
            "required_engines": ["Trivy", "Gitleaks"],
            "engines": [],
            "unavailable_engines": ["Trivy", "Gitleaks"],
            "failed_engines": [],
            "findings": [],
            "agentic_analysis": {
                "decisions": [{"type": "ai_analysis_unavailable"}],
                "model_provider": {"health": {"ok": False}},
            },
        },
    )

    assert summary["analysis_status"] == "incomplete"
    assert summary["score"] is None
    assert summary["total_findings"] is None
    assert summary["technical_evidence_sufficient"] is False
    assert summary["by_severity"] is None
    assert summary["areas"] == []
    assert "No se ejecutó suficiente cobertura técnica" in summary["results_message"]
    assert summary["analyzer_statuses"] == [
        {"name": "Trivy", "status": "unavailable"},
        {"name": "Gitleaks", "status": "unavailable"},
        {"name": "IA", "status": "unavailable"},
    ]


def test_public_summary_distinguishes_ai_error_from_unavailable():
    summary = build_public_summary(
        "scan-2",
        "report-2",
        {
            "analysis_status": "incomplete",
            "required_engines": ["Trivy", "Gitleaks"],
            "unavailable_engines": ["Trivy", "Gitleaks"],
            "agentic_analysis": {
                "decisions": [{"type": "ai_analysis_failed", "error": "generation timeout"}],
                "model_provider": {"health": {"ok": True}},
            },
        },
    )

    assert summary["analyzer_statuses"][-1] == {"name": "IA", "status": "error"}
