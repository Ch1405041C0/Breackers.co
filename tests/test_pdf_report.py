import io

import app as scan_app
from breakers.orders import OrderStore
from breakers.reports import ReportStore
from breakers.storage import SQLiteStore


REPORT = {
    "target": "https://github.com/acme/demo",
    "source": {"type": "repository", "target": "https://github.com/acme/demo", "commit_sha": "a" * 40},
    "analysis_status": "completed",
    "score": 82,
    "summary": {"score": 82, "coverage_complete": True},
    "required_engines": ["Trivy"],
    "engines": ["Trivy"],
    "unavailable_engines": [],
    "failed_engines": [],
    "findings": [
        {"engine": "Trivy", "severity": "HIGH", "title": "Dependency risk", "evidence": "requirements.txt", "category": "dependency"}
    ],
    "risks": [],
    "risk_summary": {"identified": 0, "limitations": []},
}


def configure(monkeypatch, tmp_path):
    db = SQLiteStore(str(tmp_path / "pdf.db"))
    reports = ReportStore(db)
    monkeypatch.setattr(scan_app, "report_store", reports)
    monkeypatch.setattr(scan_app, "order_store", OrderStore(db))
    return reports


def test_pdf_download_is_available_for_manual_test_without_payment(monkeypatch, tmp_path):
    reports = configure(monkeypatch, tmp_path)
    summary = reports.save_scan_result(REPORT)
    client = scan_app.app.test_client()

    response = client.get(f'/api/reports/{summary["report_id"]}/pdf')

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")
    assert summary["breakers_id"].encode() in response.data or len(response.data) > 1000
    assert f'{summary["breakers_id"]}-SCAN.pdf' in response.headers["Content-Disposition"]


def test_pdf_download_does_not_unlock_json_full_report(monkeypatch, tmp_path):
    reports = configure(monkeypatch, tmp_path)
    summary = reports.save_scan_result(REPORT)
    client = scan_app.app.test_client()

    assert client.get(f'/api/reports/{summary["report_id"]}/pdf').status_code == 200
    assert client.get(f'/api/reports/{summary["report_id"]}/full').status_code == 403


def test_unknown_pdf_report_returns_404(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    response = scan_app.app.test_client().get("/api/reports/missing/pdf")
    assert response.status_code == 404
