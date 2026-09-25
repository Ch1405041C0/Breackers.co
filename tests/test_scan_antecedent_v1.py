import json
import re
import subprocess

import app as scan_app
from breakers.interventions import generate_public_breakers_id
from breakers.models import Finding
from breakers.report import build_report
from breakers.reports import ReportStore
from breakers.storage import SQLiteStore
from breakers.inputs.repository import repository_commit_sha


ID_RE = re.compile(r"^BRK-SCN-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{12}$")


def store(tmp_path):
    return ReportStore(SQLiteStore(str(tmp_path / "antecedent.db")))


def report_with_findings(count=1):
    return {
        "target": "https://github.com/acme/demo",
        "source": {"type": "repository", "target": "https://github.com/acme/demo", "commit_sha": "a" * 40, "workspace": "temporary_clone"},
        "analysis_status": "completed",
        "score": 90,
        "summary": {"score": 90, "coverage_complete": True},
        "required_engines": ["Trivy"],
        "engines": ["Trivy"],
        "unavailable_engines": [],
        "failed_engines": [],
        "findings": [
            {"engine": "Trivy", "severity": "HIGH", "title": f"Finding {i}", "evidence": f"src/{i}.py:1", "category": "dependency"}
            for i in range(count)
        ],
        "risks": [],
        "risk_summary": {"identified": 0, "limitations": []},
    }


def test_breakers_id_format_and_uniqueness():
    ids = {generate_public_breakers_id("scan") for _ in range(500)}
    assert len(ids) == 500
    assert all(ID_RE.fullmatch(value) for value in ids)


def test_intervention_and_snapshot_are_persisted_without_source_artifacts(tmp_path):
    reports = store(tmp_path)
    summary = reports.save_scan_result(report_with_findings())
    assert ID_RE.fullmatch(summary["breakers_id"])
    intervention = reports.get_intervention_by_public_id(summary["breakers_id"])
    assert intervention["product"] == "scan"
    assert intervention["resource_id"] == summary["scan_id"]
    assert summary["scan_id"] not in summary["breakers_id"]
    assert summary["report_id"] not in summary["breakers_id"]

    snapshot = reports.get_scan_antecedent_for_intervention(intervention["intervention_id"])
    assert snapshot["identity"]["breakers_id"] == summary["breakers_id"]
    assert snapshot["analyzed"]["analyzed_state_reference"] == "a" * 40
    assert "workspace" not in snapshot["analyzed"]["source"]
    assert snapshot["evidence_policy"]["source_artifacts_retained"] is False
    assert snapshot["findings"][0]["evidence"][0]["availability"] == "source_not_retained"


def test_snapshot_preserves_more_than_200_findings(tmp_path):
    reports = store(tmp_path)
    summary = reports.save_scan_result(report_with_findings(225))
    intervention = reports.get_intervention_by_public_id(summary["breakers_id"])
    snapshot = reports.get_scan_antecedent_for_intervention(intervention["intervention_id"])
    assert len(snapshot["findings"]) == 225
    assert len(reports.get_full_report(summary["report_id"])["findings"]) == 225


def test_report_builder_no_longer_truncates_normalized_findings():
    findings = [Finding("T", "LOW", f"F{i}") for i in range(225)]
    report = build_report("demo", ["T"], findings, required_engines=["T"])
    assert len(report["findings"]) == 225


def test_repository_commit_sha(monkeypatch, tmp_path):
    sha = "b" * 40
    monkeypatch.setattr(
        "breakers.inputs.repository.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, sha + "\n", ""),
    )
    assert repository_commit_sha(tmp_path) == sha


def test_public_summary_does_not_leak_antecedent_snapshot(tmp_path):
    reports = store(tmp_path)
    summary = reports.save_scan_result(report_with_findings())
    serialized = json.dumps(summary)
    assert "Finding 0" not in serialized
    assert "commit_sha" not in serialized
    assert "antecedent" not in serialized
    assert summary["breakers_id"].startswith("BRK-SCN-")


def test_no_public_antecedent_recovery_route_exists():
    rules = {rule.rule for rule in scan_app.app.url_map.iter_rules()}
    assert not any("antecedent" in rule.lower() for rule in rules)
