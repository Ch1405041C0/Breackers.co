import time

from breakers.jobs import ScanJobStore, STAGE_DATA
from breakers.orchestrator import run_scan


def test_job_progress_uses_real_stage_percentages():
    store = ScanJobStore(ttl_seconds=60)
    job = store.create()

    job.progress("planning")
    status = job.public_status()

    assert status["stage"] == "planning"
    assert status["stage_label"] == "Eligiendo el mejor análisis para tu proyecto"
    assert status["percent"] == 25
    assert [s["status"] for s in status["stages"][:3]] == ["completed", "completed", "active"]
    assert status["stages"][3]["status"] == "pending"


def test_progress_does_not_advance_with_elapsed_time():
    store = ScanJobStore(ttl_seconds=60)
    job = store.create()
    job.progress("scanning")
    first = job.public_status()

    job.created_monotonic -= 20
    later = job.public_status()

    assert first["percent"] == 45
    assert later["percent"] == 45
    assert later["elapsed_seconds"] >= first["elapsed_seconds"] + 20


def test_public_progress_never_exposes_scanner_names():
    store = ScanJobStore(ttl_seconds=60)
    job = store.create()
    job.progress("scanning")

    payload = str(job.public_status())
    assert "Trivy" not in payload
    assert "Gitleaks" not in payload
    assert "Semgrep" not in payload
    assert "ZAP" not in payload


def test_completed_job_returns_result_and_100_percent():
    store = ScanJobStore(ttl_seconds=60)
    job = store.create()

    store.start(job, lambda progress: {"analysis_status": "completed", "score": 100})
    deadline = time.time() + 2
    while job.public_status()["state"] == "running" and time.time() < deadline:
        time.sleep(0.01)

    status = job.public_status()
    assert status["state"] == "completed"
    assert status["stage"] == "completed"
    assert status["percent"] == 100
    assert status["result"]["analysis_status"] == "completed"


def test_failed_job_keeps_last_real_stage_and_safe_error():
    store = ScanJobStore(ttl_seconds=60)
    job = store.create()

    def fail(progress):
        progress("scanning")
        raise RuntimeError("secret internal detail")

    store.start(job, fail)
    deadline = time.time() + 2
    while job.public_status()["state"] == "running" and time.time() < deadline:
        time.sleep(0.01)

    status = job.public_status()
    assert status["state"] == "failed"
    assert status["stage"] == "scanning"
    assert status["percent"] == STAGE_DATA["scanning"]["percent"]
    assert "secret internal detail" not in status["error"]


def test_finished_jobs_expire_after_ttl():
    store = ScanJobStore(ttl_seconds=1)
    job = store.create()
    store.start(job, lambda progress: {"analysis_status": "completed"})

    deadline = time.time() + 2
    while job.public_status()["state"] == "running" and time.time() < deadline:
        time.sleep(0.01)

    job.finished_monotonic -= 2
    assert store.get(job.id) is None


def test_run_scan_progress_follows_pipeline_boundaries(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr("breakers.orchestrator.TrivyScanner.available", lambda self: False)
    monkeypatch.setattr("breakers.orchestrator.GitleaksScanner.available", lambda self: False)

    stages = []
    report = run_scan(str(repo), progress=stages.append)

    assert stages == [
        "received",
        "identifying",
        "planning",
        "scanning",
        "checking",
        "evidence",
        "prioritizing",
        "reporting",
    ]
    assert report["analysis_status"] == "incomplete"


def test_run_scan_remains_compatible_without_progress(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr("breakers.orchestrator.TrivyScanner.available", lambda self: False)
    monkeypatch.setattr("breakers.orchestrator.GitleaksScanner.available", lambda self: False)

    report = run_scan(str(repo))
    assert report["source"]["type"] == "repository"
