from pathlib import Path
import shutil
import subprocess


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
        except Exception as exc:
            return None, str(exc)
