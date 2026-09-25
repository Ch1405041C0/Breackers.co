import subprocess

from breakers.models import Finding
from breakers.report import build_report
from breakers.scanners.base import ScanResult, Scanner
from breakers.scanners.gitleaks import GitleaksScanner


def test_completed_analysis_with_no_findings_can_score_100():
    report = build_report(
        "/repo", ["Trivy", "Gitleaks"], [],
        required_engines=["Trivy", "Gitleaks"],
    )
    assert report["analysis_status"] == "completed"
    assert report["score"] == 100
    assert report["summary"]["coverage_complete"] is True


def test_incomplete_analysis_has_null_score_and_missing_engines():
    report = build_report(
        "/repo", [], [],
        required_engines=["Trivy", "Gitleaks"],
        unavailable_engines=["Trivy", "Gitleaks"],
    )
    assert report["analysis_status"] == "incomplete"
    assert report["score"] is None
    assert report["unavailable_engines"] == ["Trivy", "Gitleaks"]


def test_partial_analysis_has_null_score():
    report = build_report(
        "/repo", ["Trivy"], [],
        required_engines=["Trivy", "Gitleaks"],
        unavailable_engines=["Gitleaks"],
    )
    assert report["analysis_status"] == "partial"
    assert report["score"] is None


def test_failed_engine_has_null_score_and_diagnostic():
    report = build_report(
        "/repo", ["Trivy"], [],
        required_engines=["Trivy", "Gitleaks"],
        failed_engines=[{"engine": "Gitleaks", "error": "timeout after 120s"}],
    )
    assert report["analysis_status"] == "partial"
    assert report["score"] is None
    assert report["failed_engines"][0]["engine"] == "Gitleaks"


def test_completed_findings_are_scored():
    finding = Finding("Trivy", "HIGH", "CVE-demo")
    report = build_report(
        "/repo", ["Trivy", "Gitleaks"], [finding],
        required_engines=["Trivy", "Gitleaks"],
    )
    assert report["analysis_status"] == "completed"
    assert report["score"] == 94


def test_scanner_timeout_is_failure_not_empty_success(monkeypatch, tmp_path):
    scanner = Scanner()
    scanner.name = "Demo"
    scanner.executable = "demo"

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="demo", timeout=3)

    monkeypatch.setattr("breakers.scanners.base.subprocess.run", timeout)
    result = scanner.run_command(["demo"], 3)
    assert isinstance(result, tuple)
    assert "timeout" in result[1]


def test_gitleaks_exit_one_is_success_with_findings(monkeypatch, tmp_path):
    def fake_run(cmd, timeout):
        output = cmd[cmd.index("--report-path") + 1]
        with open(output, "w", encoding="utf-8") as handle:
            handle.write('[{"Description":"secret","File":"x.txt","StartLine":2}]')
        return subprocess.CompletedProcess(cmd, 1, "", "")

    scanner = GitleaksScanner()
    monkeypatch.setattr(scanner, "run_command", fake_run)
    result = scanner.scan(str(tmp_path))
    assert isinstance(result, ScanResult)
    assert result.status == "completed"
    assert len(result.findings) == 1
