"""Protected, shareable report artifacts using standard authenticated encryption."""

from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class ProtectedReportError(ValueError):
    pass


@dataclass(frozen=True)
class PublishedReport:
    token: str
    path: Path


class ProtectedReportStore:
    """Stores encrypted JSON artifacts without requiring user accounts.

    Version 2 uses PBKDF2-HMAC-SHA256 for passphrase derivation and AES-256-GCM
    for authenticated encryption. The envelope is versioned so future formats
    can be introduced without silently changing the cryptographic contract.
    """

    VERSION = 2
    KDF_ROUNDS = 600_000
    SALT_BYTES = 16
    NONCE_BYTES = 12

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, report: dict[str, Any], passphrase: str) -> PublishedReport:
        if not passphrase or len(passphrase) < 8:
            raise ProtectedReportError("passphrase must contain at least 8 characters")

        token = secrets.token_urlsafe(18)
        salt = secrets.token_bytes(self.SALT_BYTES)
        nonce = secrets.token_bytes(self.NONCE_BYTES)
        key = self._derive_key(passphrase, salt, self.KDF_ROUNDS)
        plaintext = json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        aad = self._aad(token)
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)

        envelope = {
            "version": self.VERSION,
            "cipher": "aes-256-gcm",
            "kdf": "pbkdf2-hmac-sha256",
            "rounds": self.KDF_ROUNDS,
            "salt": self._b64(salt),
            "nonce": self._b64(nonce),
            "ciphertext": self._b64(ciphertext),
        }
        path = self.root / f"{token}.json"
        path.write_text(json.dumps(envelope, separators=(",", ":")), encoding="utf-8")
        return PublishedReport(token=token, path=path)

    def open(self, token: str, passphrase: str) -> dict[str, Any]:
        path = self._path_for(token)
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            if envelope.get("version") != self.VERSION:
                raise ProtectedReportError("unsupported report artifact version")
            if envelope.get("cipher") != "aes-256-gcm" or envelope.get("kdf") != "pbkdf2-hmac-sha256":
                raise ProtectedReportError("unsupported report artifact encryption")
            rounds = int(envelope["rounds"])
            if rounds != self.KDF_ROUNDS:
                raise ProtectedReportError("unsupported report artifact KDF parameters")
            salt = self._unb64(envelope["salt"])
            nonce = self._unb64(envelope["nonce"])
            ciphertext = self._unb64(envelope["ciphertext"])
            if len(salt) != self.SALT_BYTES or len(nonce) != self.NONCE_BYTES:
                raise ProtectedReportError("report artifact has invalid cryptographic parameters")
        except ProtectedReportError:
            raise
        except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ProtectedReportError("report artifact is unavailable or invalid") from exc

        key = self._derive_key(passphrase, salt, rounds)
        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, self._aad(token))
            decoded = json.loads(plaintext.decode("utf-8"))
        except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtectedReportError("invalid passphrase or corrupted artifact") from exc
        if not isinstance(decoded, dict):
            raise ProtectedReportError("report artifact has invalid content")
        return decoded

    @classmethod
    def _derive_key(cls, passphrase: str, salt: bytes, rounds: int) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=rounds,
        )
        return kdf.derive(passphrase.encode("utf-8"))

    @staticmethod
    def _aad(token: str) -> bytes:
        return f"breakers-protected-report:v2:{token}".encode("utf-8")

    def _path_for(self, token: str) -> Path:
        if not token or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in token):
            raise ProtectedReportError("invalid report token")
        return self.root / f"{token}.json"

    @staticmethod
    def _b64(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii")

    @staticmethod
    def _unb64(value: str) -> bytes:
        return base64.urlsafe_b64decode(value.encode("ascii"))
