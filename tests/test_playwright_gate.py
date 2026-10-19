from pathlib import Path

import pytest

from breakers.playwright_gate import gate_exit_code, GateResult, run_playwright_gate


def test_gate_exit_code_pass():
    result = GateResult("PASS", "https://example.test", "suite", 0, False)
    assert gate_exit_code(result) == 0


def test_gate_exit_code_block():
    result = GateResult("BLOCK", "https://example.test", "suite", 1, True)
    assert gate_exit_code(result) == 1


def test_gate_rejects_non_http_target(tmp_path: Path):
    suite = tmp_path / "suite"
    suite.mkdir()
    with pytest.raises(ValueError, match="http"):
        run_playwright_gate("localhost:5000", str(suite))


def test_gate_requires_existing_suite():
    with pytest.raises(ValueError, match="does not exist"):
        run_playwright_gate("https://example.test", "missing-playwright-suite")
