import json
from pathlib import Path
import tempfile

from .base import ScanResult, Scanner
from ..normalizer import normalize_finding


class GitleaksScanner(Scanner):
    name = "Gitleaks"
    executable = "gitleaks"

    def scan(self, target: str) -> ScanResult:
        with tempfile.TemporaryDirectory(prefix="breakers-gitleaks-") as tmp:
            output = Path(tmp) / "gitleaks.json"
            result = self.run_command([
                self.executable, "dir", target, "--report-format", "json",
                "--report-path", str(output), "--no-banner"
            ], 120)
            if isinstance(result, tuple):
                return self.failed(result[1])

            # Gitleaks uses exit code 1 when leaks are found; that is a successful analysis.
            if result.returncode not in (0, 1):
                return self.failed(f"scanner exited with code {result.returncode}")
            if not output.exists():
                return self.failed("scanner completed without producing its JSON report")
            try:
                data = json.loads(output.read_text(encoding="utf-8") or "[]")
            except (OSError, json.JSONDecodeError):
                return self.failed("scanner produced an unreadable JSON report")

        findings = [
            normalize_finding(self.name, "HIGH", item.get("Description", "Secret detected"), f"{item.get('File', '')}:{item.get('StartLine', '')}", "secret")
            for item in data
        ]
        return ScanResult(self.name, "completed", findings=findings)
