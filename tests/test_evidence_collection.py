from pathlib import Path

from breakers.evidence import MAX_FRAGMENT_CHARS, MAX_FRAGMENTS, MAX_TOTAL_CHARS, collect_evidence_fragments


def test_text_evidence_is_collected_as_bounded_fragments(tmp_path: Path):
    target = tmp_path / "requirements.md"
    target.write_text("Acceptance criteria\n" + ("x" * 900) + "\nSecurity requirement", encoding="utf-8")

    fragments = collect_evidence_fragments(str(target), {"type": "functional_document"})

    assert fragments
    assert len(fragments) <= MAX_FRAGMENTS
    assert all(len(item["text"]) <= MAX_FRAGMENT_CHARS for item in fragments)
    assert sum(len(item["text"]) for item in fragments) <= MAX_TOTAL_CHARS
    assert fragments[0]["reference"].startswith("requirements.md#fragment-")


def test_repository_sampling_uses_context_files_and_ignores_env_and_source(tmp_path: Path):
    (tmp_path / "README.md").write_text("Payment API with authentication and response time objectives", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name": "payments"}', encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=SHOULD_NOT_BE_COLLECTED", encoding="utf-8")
    (tmp_path / "app.py").write_text("SECRET = 'SHOULD_NOT_BE_COLLECTED'", encoding="utf-8")

    fragments = collect_evidence_fragments(str(tmp_path), {"type": "repository"})
    combined = "\n".join(item["text"] for item in fragments)

    assert "Payment API" in combined
    assert "payments" in combined
    assert "SHOULD_NOT_BE_COLLECTED" not in combined
    assert all(".env" not in item["reference"] for item in fragments)
    assert all("app.py" not in item["reference"] for item in fragments)


def test_binary_mobile_artifact_does_not_get_interpreted_as_text(tmp_path: Path):
    target = tmp_path / "app.apk"
    target.write_bytes(b"PK\x03\x04binary")

    fragments = collect_evidence_fragments(str(target), {"input_type": "app", "subtype": "android_apk"})

    assert fragments == []
