from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import uuid

from .storage import SQLiteStore

AREA_LABELS = {"dependency": "Dependencias y componentes", "configuration": "Seguridad y configuración", "secret": "Secretos / credenciales", "quality": "Calidad general"}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def build_public_summary(scan_id: str, report_id: str, full_report: dict) -> dict:
    findings = list(full_report.get("findings") or [])
    severities = Counter(str(item.get("severity") or "UNKNOWN").upper() for item in findings)
    areas = Counter(AREA_LABELS.get(str(item.get("category") or "quality"), "Otros controles") for item in findings)
    status = full_report.get("analysis_status") or "incomplete"
    score = full_report.get("score") if status == "completed" else None
    total = len(findings)
    if status == "partial":
        message = "Pudimos completar parte del análisis. Algunos controles no pudieron finalizar."
    elif status == "incomplete":
        message = "No hay evidencia suficiente para asignar un score."
    elif severities.get("CRITICAL", 0) or severities.get("HIGH", 0):
        message = "Encontramos problemas que requieren atención antes de una próxima entrega."
    elif total:
        message = "Encontramos oportunidades de mejora para revisar antes de una próxima entrega."
    else:
        message = "No encontramos hallazgos en los controles que pudieron completarse."
    return {
        "scan_id": scan_id, "report_id": report_id, "analysis_status": status, "score": score,
        "total_findings": total,
        "by_severity": {key: severities.get(key, 0) for key in ("CRITICAL", "HIGH", "MEDIUM", "LOW")},
        "areas": [{"label": label, "count": count} for label, count in areas.most_common()],
        "priority_message": message, "full_report_available": True,
    }

class ReportStore:
    def __init__(self, database: SQLiteStore):
        self.database = database

    def save_scan_result(self, full_report: dict) -> dict:
        scan_id, report_id, created_at = uuid.uuid4().hex, uuid.uuid4().hex, _now()
        summary = build_public_summary(scan_id, report_id, full_report)
        with self.database.connect() as connection:
            connection.execute("INSERT INTO scans(scan_id, created_at) VALUES (?, ?)", (scan_id, created_at))
            connection.execute("INSERT INTO reports(report_id, scan_id, public_summary, full_report, created_at) VALUES (?, ?, ?, ?, ?)", (report_id, scan_id, json.dumps(summary), json.dumps(full_report), created_at))
        return summary

    def get_public_summary(self, report_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT public_summary FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        return json.loads(row["public_summary"]) if row else None

    def get_full_report(self, report_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT full_report FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        return json.loads(row["full_report"]) if row else None
