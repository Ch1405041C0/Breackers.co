from flask import Flask, jsonify, request, send_file, send_from_directory
from pathlib import Path
import os
import shutil
import tempfile
from io import BytesIO
from werkzeug.utils import secure_filename

from breakers.jobs import ScanJobStore
from breakers.orchestrator import run_scan
from breakers.orders import OrderStore
from breakers.pdf_report import build_scan_pdf
from breakers.reports import ReportStore
from breakers.storage import SQLiteStore
from breakers.strike.http_adapter import StrikeHttpError, execute_strike_request

app = Flask(__name__)
ROOT = Path(__file__).parent
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("BREAKERS_MAX_REQUEST_BYTES", 100 * 1024 * 1024))
app.config["STRIKE_MAX_FILE_BYTES"] = int(os.environ.get("BREAKERS_STRIKE_MAX_FILE_BYTES", 5 * 1024 * 1024))
scan_jobs = ScanJobStore(ttl_seconds=900)

DATABASE_PATH = os.environ.get("BREAKERS_DB_PATH", str(ROOT / "data" / "breakers.db"))
database = SQLiteStore(DATABASE_PATH)
report_store = ReportStore(database)
order_store = OrderStore(database)

ALLOWED_EVIDENCE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".md", ".json", ".yaml", ".yml",
    ".csv", ".log", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".xml",
    ".html", ".zip", ".apk", ".ipa",
}

@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")

@app.get("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ROOT / "assets", filename)

def _start_scan_job(target: str, cleanup_path: str | None = None):
    job = scan_jobs.create()

    def scan_once(progress):
        full_report = run_scan(target, progress=progress)
        return report_store.save_scan_result(full_report)

    scan_jobs.start(job, scan_once, cleanup_path=cleanup_path)
    return jsonify(job_id=job.id, state="running"), 202

@app.post("/api/scan")
def scan():
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        authorized = request.form.get("authorized", "").lower() == "true"
        uploaded = request.files.get("file")
        if not authorized or uploaded is None or not uploaded.filename:
            return jsonify(error="authorization and file required"), 400
        filename = secure_filename(uploaded.filename)
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EVIDENCE_EXTENSIONS:
            return jsonify(error=f"unsupported evidence type: {suffix or 'unknown'}"), 400
        workspace = tempfile.mkdtemp(prefix="breakers-scan-")
        target = Path(workspace) / filename
        try:
            uploaded.save(target)
        except Exception:
            shutil.rmtree(workspace, ignore_errors=True)
            raise
        return _start_scan_job(str(target), cleanup_path=workspace)

    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    if not data.get("authorized") or not target:
        return jsonify(error="authorization and target required"), 400
    return _start_scan_job(target)

@app.get("/api/scan/<job_id>")
def scan_status(job_id: str):
    job = scan_jobs.get(job_id)
    if job is None:
        return jsonify(error="SCAN job not found or expired"), 404
    return jsonify(job.public_status())

@app.post("/api/strike")
def strike():
    try:
        payload = execute_strike_request(
            request,
            max_file_bytes=app.config["STRIKE_MAX_FILE_BYTES"],
        )
        return jsonify(payload), 200
    except StrikeHttpError as exc:
        return jsonify(exc.body()), exc.status
    except Exception:
        app.logger.exception("Unexpected STRIKE API failure")
        return jsonify(error={"code": "STRIKE_INTERNAL_ERROR", "message": "STRIKE could not complete the analysis"}), 500

@app.post("/api/reports/<report_id>/orders")
def create_report_order(report_id: str):
    if report_store.get_public_summary(report_id) is None:
        return jsonify(error="Informe no encontrado."), 404
    existing = order_store.find_for_resource("scan", report_id)
    order = existing or order_store.create("scan", report_id)
    return jsonify({
        "order_id": order["order_id"],
        "product": order["product"],
        "report_id": report_id,
        "currency": order["currency"],
        "amount": order["amount"],
        "status": order["status"],
        "payment_methods": [],
        "payments_configured": False,
    }), 201 if existing is None else 200

@app.get("/api/orders/<order_id>")
def order_status(order_id: str):
    order = order_store.get(order_id)
    if order is None:
        return jsonify(error="Orden no encontrada."), 404
    return jsonify({
        "order_id": order["order_id"],
        "product": order["product"],
        "resource_id": order["resource_id"],
        "currency": order["currency"],
        "amount": order["amount"],
        "status": order["status"],
        "payment_methods": [],
        "payments_configured": False,
    })

@app.get("/api/reports/<report_id>/pdf")
def download_scan_pdf(report_id: str):
    context = report_store.get_report_context(report_id)
    if context is None:
        return jsonify(error="Informe no encontrado."), 404
    pdf = build_scan_pdf(
        breakers_id=context["breakers_id"],
        created_at=context["created_at"],
        report=context["full_report"],
    )
    filename = f'{context["breakers_id"]}-SCAN.pdf'
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )

@app.get("/api/reports/<report_id>/full")
def full_report(report_id: str):
    if report_store.get_public_summary(report_id) is None:
        return jsonify(error="Informe no encontrado."), 404
    if not order_store.has_approved_access("scan", report_id):
        return jsonify(error="El informe completo requiere una autorización de pago confirmada por Breakers."), 403
    report = report_store.get_full_report(report_id)
    return jsonify(report)

@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error={"code": "PAYLOAD_TOO_LARGE", "message": "request exceeds the configured upload limit"}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
