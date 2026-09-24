import json
from pathlib import Path
import tempfile

from .base import Scanner
from ..normalizer import normalize_finding


class GitleaksScanner(Scanner):
    name = "Gitleaks"
    executable = "gitleaks"

    def scan(self, target: str):
        with tempfile.TemporaryDirectory(prefix="breakers-gitleaks-") as tmp:
            output = Path(tmp) / "gitleaks.json"
            result = self.run_command([
                self.executable, "dir", target, "--report-format", "json",
                "--report-path", str(output), "--no-banner"
            ], 120)
            if isinstance(result, tuple) or not output.exists():
                return []
            try:
                data = json.loads(output.read_text(encoding="utf-8") or "[]")
            except (OSError, json.JSONDecodeError):
                return []
        return [
            normalize_finding(self.name, "HIGH", item.get("Description", "Secret detected"), f"{item.get('File', '')}:{item.get('StartLine', '')}", "secret")
            for item in data
        ]
