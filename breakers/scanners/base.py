from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess

from ..models import Finding


@dataclass
class ScanResult:
    engine: str
    status: str
    findings: list[Finding] = field(default_factory=list)
    error: str = ""


class Scanner:
    name = "Scanner"
    executable = ""

    def available(self) -> bool:
        return bool(shutil.which(self.executable))

    def supports(self, target: str) -> bool:
        return Path(target).exists()

    def run_command(self, cmd: list[str], timeout: int):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, f"timeout after {timeout}s"
        except OSError:
            return None, "scanner executable could not be started"

    def failed(self, message: str) -> ScanResult:
        return ScanResult(self.name, "failed", error=message)
