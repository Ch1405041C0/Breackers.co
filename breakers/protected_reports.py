"""Protected, shareable report artifacts.

This module deliberately keeps sharing separate from report generation.  A
caller can publish any JSON-serializable report and hand the returned token and
passphrase to the client through different channels.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProtectedReportError(ValueError):
    pass


@dataclass(frozen=True)
class PublishedReport:
    token: str
    path: Path


class ProtectedReportStore:
    """Stores authenticated encrypted JSON without requiring user accounts.

    Encryption uses a SHA-256 based stream derived from a per-artifact salt and
    passphrase, while HMAC-SHA256 authenticates the complete encrypted payload.
    The format is versioned so the crypto implementation can be replaced later
    without changing callers or public links.
    """

    VERSION = 1
    KDF_ROUNDS = 200_000

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, report: dict[str, Any], passphrase: str) -> PublishedReport:
        if not passphrase or len(passphrase) < 8:
            raise ProtectedReportError("passphrase must contain at least 8 characters")

        token = secrets.token_urlsafe(18)
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac(
            "sha256", passphrase.encode("utf-8"), salt, self.KDF_ROUNDS, dklen=32
        )
        plaintext = json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ciphertext = self._xor_stream(plaintext, key, nonce)
        tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()

        envelope = {
            "version": self.VERSION,
            "kdf": "pbkdf2-sha256",
            "rounds": self.KDF_ROUNDS,
            "salt": self._b64(salt),
            "nonce": self._b64(nonce),
            "ciphertext": self._b64(ciphertext),
            "tag": self._b64(tag),
        }
        path = self.root / f"{token}.json"
        path.write_text(json.dumps(envelope, separators=(",", ":")), encoding="utf-8")
        return PublishedReport(token=token, path=path)

    def open(self, token: str, passphrase: str) -> dict[str, Any]:
        path = self._path_for(token)
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            salt = self._unb64(envelope["salt"])
            nonce = self._unb64(envelope["nonce"])
            ciphertext = self._unb64(envelope["ciphertext"])
            expected_tag = self._unb64(envelope["tag"])
            rounds = int(envelope["rounds"])
        except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ProtectedReportError("report artifact is unavailable or invalid") from exc

        key = hashlib.pbkdf2_hmac(
            "sha256", passphrase.encode("utf-8"), salt, rounds, dklen=32
        )
        actual_tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(actual_tag, expected_tag):
            raise ProtectedReportError("invalid passphrase or corrupted artifact")

        try:
            plaintext = self._xor_stream(ciphertext, key, nonce)
            return json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtectedReportError("report artifact could not be decoded") from exc

    def _path_for(self, token: str) -> Path:
        if not token or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in token):
            raise ProtectedReportError("invalid report token")
        return self.root / f"{token}.json"

    @staticmethod
    def _xor_stream(data: bytes, key: bytes, nonce: bytes) -> bytes:
        output = bytearray(len(data))
        offset = 0
        counter = 0
        while offset < len(data):
            block = hmac.new(
                key, b"breakers-report" + nonce + counter.to_bytes(8, "big"), hashlib.sha256
            ).digest()
            size = min(len(block), len(data) - offset)
            for index in range(size):
                output[offset + index] = data[offset + index] ^ block[index]
            offset += size
            counter += 1
        return bytes(output)

    @staticmethod
    def _b64(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii")

    @staticmethod
    def _unb64(value: str) -> bytes:
        return base64.urlsafe_b64decode(value.encode("ascii"))
