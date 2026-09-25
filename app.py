from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
from tempfile import TemporaryDirectory
from werkzeug.utils import secure_filename

from breakers.orchestrator import run_scan

app = Flask(__name__)
ROOT = Path(__file__).parent
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

ALLOWED_EVIDENCE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".md", ".json", ".yaml", ".yml",
    ".csv", ".log", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".xml",
    ".html", ".zip", ".apk", ".ipa",
}


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


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

        with TemporaryDirectory(prefix="breakers-scan-") as tmp:
            target = Path(tmp) / filename
            uploaded.save(target)
            try:
                return jsonify(run_scan(str(target)))
            except ValueError as exc:
                return jsonify(error=str(exc)), 400

    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    if not data.get("authorized") or not target:
        return jsonify(error="authorization and target required"), 400
    try:
        return jsonify(run_scan(target))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error="file too large; maximum size is 100 MB"), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
