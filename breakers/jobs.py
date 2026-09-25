from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import shutil
import threading
import time
import uuid
from typing import Callable


STAGES = (
    ("received", "Objetivo recibido", 5),
    ("identifying", "Identificando tu proyecto", 15),
    ("planning", "Eligiendo el mejor análisis para tu proyecto", 25),
    ("scanning", "Buscando riesgos", 45),
    ("checking", "Comprobando lo encontrado", 60),
    ("evidence", "Organizando la evidencia", 72),
    ("prioritizing", "Priorizando lo importante", 84),
    ("reporting", "Preparando tu reporte", 94),
    ("completed", "SCAN completo", 100),
)
STAGE_INDEX = {key: index for index, (key, _label, _percent) in enumerate(STAGES)}
STAGE_DATA = {key: {"key": key, "label": label, "percent": percent} for key, label, percent in STAGES}


@dataclass
class ScanJob:
    id: str
    created_monotonic: float
    created_at: str
    stage: str = "received"
    state: str = "running"
    result: dict | None = None
    error: str = ""
    finished_monotonic: float | None = None
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def progress(self, stage: str) -> None:
        if stage not in STAGE_INDEX:
            raise ValueError(f"unknown SCAN progress stage: {stage}")
        with self.lock:
            if self.state != "running":
                return
            if STAGE_INDEX[stage] >= STAGE_INDEX[self.stage]:
                self.stage = stage

    def public_status(self) -> dict:
        with self.lock:
            current = STAGE_DATA[self.stage]
            elapsed = max(0, int(time.monotonic() - self.created_monotonic))
            current_index = STAGE_INDEX[self.stage]
            stages = []
            for index, (key, label, percent) in enumerate(STAGES):
                if self.state == "failed" and index == current_index:
                    status = "active"
                elif index < current_index or (self.state == "completed" and index <= current_index):
                    status = "completed"
                elif index == current_index:
                    status = "active"
                else:
                    status = "pending"
                stages.append({"key": key, "label": label, "percent": percent, "status": status})
            payload = {
                "job_id": self.id,
                "state": self.state,
                "stage": current["key"],
                "stage_label": current["label"],
                "percent": current["percent"],
                "elapsed_seconds": elapsed,
                "stages": stages,
            }
            if self.state == "completed":
                payload["result"] = self.result
            elif self.state == "failed":
                payload["error"] = self.error or "SCAN no pudo completar el análisis."
            return payload


class ScanJobStore:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._jobs: dict[str, ScanJob] = {}
        self._lock = threading.Lock()

    def _cleanup_expired(self) -> None:
        now = time.monotonic()
        with self._lock:
            expired = [
                job_id for job_id, job in self._jobs.items()
                if job.finished_monotonic is not None
                and now - job.finished_monotonic >= self.ttl_seconds
            ]
            for job_id in expired:
                self._jobs.pop(job_id, None)

    def create(self) -> ScanJob:
        self._cleanup_expired()
        job = ScanJob(
            id=uuid.uuid4().hex,
            created_monotonic=time.monotonic(),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> ScanJob | None:
        self._cleanup_expired()
        with self._lock:
            return self._jobs.get(job_id)

    def start(self, job: ScanJob, work: Callable[[Callable[[str], None]], dict], cleanup_path: str | None = None) -> None:
        def runner():
            try:
                result = work(job.progress)
                if cleanup_path:
                    shutil.rmtree(cleanup_path, ignore_errors=True)
                job.progress("completed")
                with job.lock:
                    job.result = result
                    job.state = "completed"
                    job.finished_monotonic = time.monotonic()
            except Exception as exc:
                if cleanup_path:
                    shutil.rmtree(cleanup_path, ignore_errors=True)
                with job.lock:
                    job.state = "failed"
                    job.error = _safe_error(exc)
                    job.finished_monotonic = time.monotonic()

        threading.Thread(target=runner, name=f"scan-{job.id[:8]}", daemon=True).start()


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        message = str(exc).strip()
        if message and len(message) <= 300:
            return message
    return "SCAN no pudo completar el análisis."
