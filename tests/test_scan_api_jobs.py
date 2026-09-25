import io
from pathlib import Path
import time

import app as scan_app
from breakers.jobs import ScanJobStore
from breakers.orders import OrderStore
from breakers.reports import ReportStore
from breakers.storage import SQLiteStore


def _stores(monkeypatch, tmp_path):
    db = SQLiteStore(str(tmp_path / 'api.db'))
    monkeypatch.setattr(scan_app, 'report_store', ReportStore(db))
    monkeypatch.setattr(scan_app, 'order_store', OrderStore(db))


def _wait_for_terminal(client, job_id):
    deadline = time.time() + 2
    while time.time() < deadline:
        response = client.get(f"/api/scan/{job_id}")
        data = response.get_json()
        if data["state"] != "running":
            return response, data
        time.sleep(0.01)
    raise AssertionError("job did not finish")


def test_scan_post_requires_authorization(monkeypatch):
    monkeypatch.setattr(scan_app, "scan_jobs", ScanJobStore(ttl_seconds=60))
    client = scan_app.app.test_client()

    response = client.post("/api/scan", json={"target": "/tmp/demo", "authorized": False})

    assert response.status_code == 400


def test_scan_post_returns_job_id_and_polling_result(monkeypatch, tmp_path):
    _stores(monkeypatch, tmp_path)
    monkeypatch.setattr(scan_app, "scan_jobs", ScanJobStore(ttl_seconds=60))

    def fake_run_scan(target, progress=None):
        for stage in ("received", "identifying", "planning", "scanning", "checking", "evidence", "prioritizing", "reporting"):
            progress(stage)
        return {"analysis_status": "partial", "score": None, "findings": []}

    monkeypatch.setattr(scan_app, "run_scan", fake_run_scan)
    client = scan_app.app.test_client()

    response = client.post("/api/scan", json={"target": "https://github.com/acme/demo", "authorized": True})
    data = response.get_json()

    assert response.status_code == 202
    assert data["job_id"]

    status_response, status = _wait_for_terminal(client, data["job_id"])
    assert status_response.status_code == 200
    assert status["state"] == "completed"
    assert status["percent"] == 100
    assert status["result"]["analysis_status"] == "partial"
    assert status["result"]["score"] is None


def test_unknown_job_returns_404(monkeypatch):
    monkeypatch.setattr(scan_app, "scan_jobs", ScanJobStore(ttl_seconds=60))
    client = scan_app.app.test_client()

    response = client.get("/api/scan/not-a-real-job")

    assert response.status_code == 404


def test_uploaded_file_lives_for_job_and_workspace_is_cleaned(monkeypatch, tmp_path):
    _stores(monkeypatch, tmp_path)
    monkeypatch.setattr(scan_app, "scan_jobs", ScanJobStore(ttl_seconds=60))
    seen = {}

    def fake_run_scan(target, progress=None):
        path = Path(target)
        seen["target"] = path
        seen["exists_during_scan"] = path.exists()
        progress("received")
        progress("identifying")
        progress("planning")
        progress("scanning")
        progress("checking")
        progress("evidence")
        progress("prioritizing")
        progress("reporting")
        return {"analysis_status": "completed", "score": 100, "findings": []}

    monkeypatch.setattr(scan_app, "run_scan", fake_run_scan)
    client = scan_app.app.test_client()

    response = client.post(
        "/api/scan",
        data={
            "authorized": "true",
            "file": (io.BytesIO(b"evidence"), "evidence.txt"),
        },
        content_type="multipart/form-data",
    )
    job_id = response.get_json()["job_id"]
    _wait_for_terminal(client, job_id)

    assert seen["exists_during_scan"] is True
    assert not seen["target"].exists()
    assert not seen["target"].parent.exists()
