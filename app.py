from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path

from breakers.orchestrator import run_scan

app = Flask(__name__)
ROOT = Path(__file__).parent


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.post("/api/scan")
def scan():
    data = request.get_json(force=True) or {}
    target = str(data.get("target", "")).strip()
    if not data.get("authorized") or not target:
        return jsonify(error="authorization and target required"), 400
    try:
        return jsonify(run_scan(target))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
