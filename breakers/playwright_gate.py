"""Playwright-backed deployment quality gate for Breakers.

Runs an authorized pytest/Playwright suite and exposes a deterministic
PASS/BLOCK decision suitable for CI/CD pipelines.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import os
import subprocess
import sys


@dataclass(frozen=True)
class GateResult:
    status: str
    target_url: str
    suite: str
    exit_code: int
    blocking: bool

    def to_dict(self) -> dict:
        return asdict(self)


def run_playwright_gate(
    target_url: str,
    suite: str = "tests/playwright",
    *,
    browser: str = "chromium",
    timeout_seconds: int = 600,
) -> GateResult:
    """Run a Playwright test suite and return PASS or BLOCK.

    The target URL is exposed to tests as BREAKERS_TARGET_URL.
    A zero pytest exit code authorizes the pipeline to continue;
    any non-zero result blocks promotion/deployment.
    """
    target_url = str(target_url or "").strip()
    if not target_url.startswith(("http://", "https://")):
        raise ValueError("target_url must be an http(s) URL")

    suite_path = Path(suite)
    if not suite_path.exists():
        raise ValueError(f"Playwright suite does not exist: {suite}")

    env = os.environ.copy()
    env["BREAKERS_TARGET_URL"] = target_url

    command = [
        sys.executable,
        "-m",
        "pytest",
        str(suite_path),
        f"--browser={browser}",
    ]

    try:
        completed = subprocess.run(
            command,
            env=env,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
    except subprocess.TimeoutExpired:
        exit_code = 124

    passed = exit_code == 0
    return GateResult(
        status="PASS" if passed else "BLOCK",
        target_url=target_url,
        suite=str(suite_path),
        exit_code=exit_code,
        blocking=not passed,
    )


def gate_exit_code(result: GateResult) -> int:
    """Translate a gate result into the CI/CD process exit code."""
    return 1 if result.blocking else 0
