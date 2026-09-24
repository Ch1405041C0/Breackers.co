import json
from pathlib import Path
import tempfile

from .base import Scanner
from ..normalizer import normalize_finding


class TrivyScanner(Scanner):
    name = "Trivy"
    executable = "trivy"

    def scan(self, target: str):
        findings = []
        with tempfile.TemporaryDirectory(prefix="breakers-trivy-") as tmp:
            output = Path(tmp) / "trivy.json"
            result = self.run_command([
                self.executable, "fs", "--scanners", "vuln,misconfig,secret",
                "--format", "json", "-o", str(output), target
            ], 180)
            if isinstance(result, tuple):
                return findings
            if not output.exists():
                return findings
            try:
                data = json.loads(output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return findings
        for group in data.get("Results", []):
            for item in group.get("Vulnerabilities") or []:
                findings.append(normalize_finding(self.name, item.get("Severity"), item.get("VulnerabilityID"), item.get("Title") or item.get("PkgName"), "dependency"))
            for item in group.get("Misconfigurations") or []:
                findings.append(normalize_finding(self.name, item.get("Severity"), item.get("Title"), item.get("Message"), "configuration"))
            for item in group.get("Secrets") or []:
                findings.append(normalize_finding(self.name, "HIGH", item.get("Title", "Secret detected"), item.get("RuleID", ""), "secret"))
        return findings
