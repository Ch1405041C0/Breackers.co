import json

import pytest

from breakers.protected_reports import ProtectedReportError, ProtectedReportStore


def test_publish_and_open_round_trip(tmp_path):
    store = ProtectedReportStore(tmp_path)
    report = {"target": "demo", "score": 87, "findings": [{"severity": "high"}]}

    published = store.publish(report, "cliente-2026")

    assert published.path.exists()
    assert store.open(published.token, "cliente-2026") == report
    raw = published.path.read_text(encoding="utf-8")
    assert "findings" not in raw
    assert "demo" not in raw


def test_wrong_passphrase_is_rejected(tmp_path):
    store = ProtectedReportStore(tmp_path)
    published = store.publish({"score": 42}, "correcta-2026")

    with pytest.raises(ProtectedReportError):
        store.open(published.token, "incorrecta")


def test_tampered_artifact_is_rejected(tmp_path):
    store = ProtectedReportStore(tmp_path)
    published = store.publish({"score": 42}, "correcta-2026")
    envelope = json.loads(published.path.read_text(encoding="utf-8"))
    envelope["ciphertext"] = envelope["ciphertext"][:-2] + "AA"
    published.path.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(ProtectedReportError):
        store.open(published.token, "correcta-2026")


def test_short_passphrase_is_rejected(tmp_path):
    store = ProtectedReportStore(tmp_path)

    with pytest.raises(ProtectedReportError):
        store.publish({"score": 42}, "corta")
