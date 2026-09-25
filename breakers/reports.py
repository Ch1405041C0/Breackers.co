from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import uuid

from .antecedents import build_scan_antecedent_snapshot
from .interventions import generate_public_breakers_id
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
        scan_id, report_id, intervention_id, created_at = uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex, _now()
        public_breakers_id = generate_public_breakers_id("scan")
        summary = build_public_summary(scan_id, report_id, full_report)
        snapshot = build_scan_antecedent_snapshot(
            breakers_id=public_breakers_id, created_at=created_at, full_report=full_report
        )
        with self.database.connect() as connection:
            connection.execute("INSERT INTO scans(scan_id, created_at) VALUES (?, ?)", (scan_id, created_at))
            connection.execute(
                "INSERT INTO reports(report_id, scan_id, public_summary, full_report, created_at) VALUES (?, ?, ?, ?, ?)",
                (report_id, scan_id, json.dumps(summary), json.dumps(full_report), created_at),
            )
            connection.execute(
                "INSERT INTO interventions(intervention_id, public_breakers_id, product, resource_id, created_at) VALUES (?, ?, 'scan', ?, ?)",
                (intervention_id, public_breakers_id, scan_id, created_at),
            )
            connection.execute(
                "INSERT INTO scan_antecedents(intervention_id, snapshot, created_at) VALUES (?, ?, ?)",
                (intervention_id, json.dumps(snapshot), created_at),
            )
        summary["breakers_id"] = public_breakers_id
        return summary

    def get_public_summary(self, report_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT public_summary FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        return json.loads(row["public_summary"]) if row else None

    def get_full_report(self, report_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT full_report FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        return json.loads(row["full_report"]) if row else None

    def get_intervention_by_public_id(self, public_breakers_id: str) -> dict | None:
        """Internal resolver only. Resolving identity does not authorize antecedent access."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM interventions WHERE public_breakers_id = ?", (public_breakers_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_scan_antecedent_for_intervention(self, intervention_id: str) -> dict | None:
        """Internal storage primitive; no public route exposes this method."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT snapshot FROM scan_antecedents WHERE intervention_id = ?", (intervention_id,)
            ).fetchone()
        return json.loads(row["snapshot"]) if row else None

    def get_report_context(self, report_id: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT r.full_report, r.created_at, i.public_breakers_id
                   FROM reports r
                   JOIN interventions i ON i.resource_id = r.scan_id AND i.product = 'scan'
                   WHERE r.report_id = ?""",
                (report_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "full_report": json.loads(row["full_report"]),
            "created_at": row["created_at"],
            "breakers_id": row["public_breakers_id"],
        }
