from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
import tempfile
from werkzeug.utils import secure_filename

from breakers.jobs import ScanJobStore
from breakers.orchestrator import run_scan

app = Flask(__name__)
ROOT = Path(__file__).parent
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
scan_jobs = ScanJobStore(ttl_seconds=900)

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
    scan_jobs.start(job, lambda progress: run_scan(target, progress=progress), cleanup_path=cleanup_path)
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
            Path(workspace).rmdir()
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


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error="file too large; maximum size is 100 MB"), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
