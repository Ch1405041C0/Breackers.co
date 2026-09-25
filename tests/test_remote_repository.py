from pathlib import Path
import subprocess

import pytest

from breakers.inputs.repository import RepositoryCloneError, clone_repository, validate_repository_url
from breakers.orchestrator import run_scan


def test_valid_github_and_gitlab_urls():
    assert validate_repository_url("https://github.com/acme/demo") == "https://github.com/acme/demo"
    assert validate_repository_url("https://gitlab.com/acme/demo.git") == "https://gitlab.com/acme/demo.git"


@pytest.mark.parametrize("url", [
    "http://github.com/acme/demo",
    "git@github.com:acme/demo.git",
    "https://example.com/acme/demo",
    "https://github.com/acme",
    "not-a-url",
])
def test_invalid_repository_url(url):
    with pytest.raises(ValueError):
        validate_repository_url(url)


def test_clone_failure_is_clear(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 128, "", "fatal: repository not found")

    monkeypatch.setattr("breakers.inputs.repository.subprocess.run", fake_run)
    with pytest.raises(RepositoryCloneError, match="repository not found"):
        clone_repository("https://github.com/acme/missing", tmp_path / "repo")


def test_local_repository_still_runs(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr("breakers.orchestrator.TrivyScanner.available", lambda self: False)
    monkeypatch.setattr("breakers.orchestrator.GitleaksScanner.available", lambda self: False)
    report = run_scan(str(repo))
    assert report["source"]["type"] == "repository"
    assert report["target"] == str(repo)


def test_remote_repository_uses_temporary_clone_and_cleans_up(monkeypatch):
    seen = {}

    def fake_clone(url, destination, timeout=60):
        destination = Path(destination)
        destination.mkdir()
        (destination / "README.md").write_text("demo", encoding="utf-8")
        seen["workspace"] = destination
        return destination

    monkeypatch.setattr("breakers.orchestrator.clone_repository", fake_clone)
    monkeypatch.setattr("breakers.orchestrator.repository_commit_sha", lambda path: "c" * 40)
    monkeypatch.setattr("breakers.orchestrator.TrivyScanner.available", lambda self: False)
    monkeypatch.setattr("breakers.orchestrator.GitleaksScanner.available", lambda self: False)

    report = run_scan("https://github.com/acme/demo")
    assert report["source"]["type"] == "repository"
    assert report["source"]["target"] == "https://github.com/acme/demo"
    assert report["source"]["workspace"] == "temporary_clone"
    assert report["source"]["commit_sha"] == "c" * 40
    assert report["target"] == "https://github.com/acme/demo"
    assert not seen["workspace"].exists()
