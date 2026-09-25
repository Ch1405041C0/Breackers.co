import json
import time

import app as scan_app
from breakers.jobs import ScanJobStore
from breakers.orders import OrderStore
from breakers.reports import ReportStore
from breakers.storage import SQLiteStore


FULL = {
    "analysis_status": "completed",
    "score": 34,
    "engines": ["InternalEngine"],
    "findings": [
        {"engine": "InternalEngine", "severity": "CRITICAL", "title": "CVE-SECRET", "evidence": "src/a.py:7", "category": "dependency"},
        {"engine": "InternalEngine", "severity": "HIGH", "title": "Credential", "evidence": "secret.txt:2", "category": "secret"},
        {"engine": "InternalEngine", "severity": "MEDIUM", "title": "Config", "evidence": "cfg.yml", "category": "configuration"},
    ],
}


def stores(tmp_path):
    db = SQLiteStore(str(tmp_path / "breakers.db"))
    return db, ReportStore(db), OrderStore(db)


def wait(client, job_id):
    deadline = time.time() + 2
    while time.time() < deadline:
        data = client.get(f"/api/scan/{job_id}").get_json()
        if data["state"] != "running":
            return data
        time.sleep(0.01)
    raise AssertionError("job timeout")


def configure_app(monkeypatch, tmp_path):
    db, reports, orders = stores(tmp_path)
    monkeypatch.setattr(scan_app, "scan_jobs", ScanJobStore(ttl_seconds=60))
    monkeypatch.setattr(scan_app, "database", db)
    monkeypatch.setattr(scan_app, "report_store", reports)
    monkeypatch.setattr(scan_app, "order_store", orders)
    return reports, orders


def test_public_summary_is_whitelisted_and_same_analysis(monkeypatch, tmp_path):
    reports, _ = configure_app(monkeypatch, tmp_path)
    calls = {"count": 0}

    def fake_scan(target, progress=None):
        calls["count"] += 1
        return FULL

    monkeypatch.setattr(scan_app, "run_scan", fake_scan)
    client = scan_app.app.test_client()
    job = client.post("/api/scan", json={"target": "demo", "authorized": True}).get_json()
    status = wait(client, job["job_id"])
    summary = status["result"]

    assert calls["count"] == 1
    assert summary["score"] == 34
    assert summary["total_findings"] == 3
    assert summary["by_severity"]["CRITICAL"] == 1
    serialized = json.dumps(summary)
    for forbidden in ("CVE-SECRET", "src/a.py:7", "InternalEngine"):
        assert forbidden not in serialized
    assert "findings" not in summary
    assert "engines" not in summary
    assert summary["breakers_id"].startswith("BRK-SCN-")
    assert reports.get_full_report(summary["report_id"]) == FULL


def test_partial_and_incomplete_public_score_is_null(tmp_path):
    _, reports, _ = stores(tmp_path)
    for status in ("partial", "incomplete"):
        summary = reports.save_scan_result({"analysis_status": status, "score": 100, "findings": []})
        assert summary["score"] is None


def test_price_is_backend_catalog_not_client_input(monkeypatch, tmp_path):
    reports, _ = configure_app(monkeypatch, tmp_path)
    summary = reports.save_scan_result(FULL)
    client = scan_app.app.test_client()
    response = client.post(f'/api/reports/{summary["report_id"]}/orders', json={"amount": 1, "currency": "USD"})
    order = response.get_json()
    assert order["amount"] == 99900
    assert order["currency"] == "ARS"
    assert order["status"] == "pending"


def test_report_id_and_nonapproved_states_do_not_unlock(monkeypatch, tmp_path):
    reports, orders = configure_app(monkeypatch, tmp_path)
    summary = reports.save_scan_result(FULL)
    report_id = summary["report_id"]
    client = scan_app.app.test_client()

    assert client.get(f"/api/reports/{report_id}/full").status_code == 403
    order = orders.create("scan", report_id)
    assert client.get(f"/api/reports/{report_id}/full").status_code == 403

    for state in ("rejected", "cancelled", "pending"):
        with orders.database.connect() as connection:
            connection.execute("UPDATE orders SET status = ? WHERE order_id = ?", (state, order["order_id"]))
        assert client.get(f"/api/reports/{report_id}/full").status_code == 403


def test_only_backend_approved_order_unlocks(monkeypatch, tmp_path):
    reports, orders = configure_app(monkeypatch, tmp_path)
    summary = reports.save_scan_result(FULL)
    order = orders.create("scan", summary["report_id"])
    client = scan_app.app.test_client()

    with orders.database.connect() as connection:
        connection.execute("UPDATE orders SET status = 'approved' WHERE order_id = ?", (order["order_id"],))
    response = client.get(f'/api/reports/{summary["report_id"]}/full')
    assert response.status_code == 200
    assert response.get_json()["findings"][0]["title"] == "CVE-SECRET"


def test_reopening_sqlite_preserves_report_and_order(tmp_path):
    path = str(tmp_path / "persistent.db")
    first = SQLiteStore(path)
    reports = ReportStore(first)
    orders = OrderStore(first)
    summary = reports.save_scan_result(FULL)
    order = orders.create("scan", summary["report_id"])

    reopened = SQLiteStore(path)
    assert ReportStore(reopened).get_full_report(summary["report_id"]) == FULL
    assert OrderStore(reopened).get(order["order_id"])["status"] == "pending"


def test_expired_job_does_not_delete_persistent_report(tmp_path):
    _, reports, _ = stores(tmp_path)
    summary = reports.save_scan_result(FULL)
    store = ScanJobStore(ttl_seconds=1)
    job = store.create()
    store.start(job, lambda progress: summary)
    deadline = time.time() + 2
    while job.public_status()["state"] == "running" and time.time() < deadline:
        time.sleep(0.01)
    job.finished_monotonic -= 2
    assert store.get(job.id) is None
    assert reports.get_full_report(summary["report_id"]) == FULL


def test_full_report_protection_is_unchanged_with_breakers_id(monkeypatch, tmp_path):
    reports, _ = configure_app(monkeypatch, tmp_path)
    summary = reports.save_scan_result(FULL)
    client = scan_app.app.test_client()
    assert summary["breakers_id"].startswith("BRK-SCN-")
    assert client.get(f'/api/reports/{summary["report_id"]}/full').status_code == 403
    assert client.get(f'/api/reports/{summary["breakers_id"]}/full').status_code == 404
