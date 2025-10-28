from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict

from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_IDENTIFIER_PATTERN = re.compile(r"[^A-Za-z0-9._-]")


def sanitise_identifier(value: str) -> str:
    """Normalise identifiers used for file names to prevent traversal."""

    cleaned = _IDENTIFIER_PATTERN.sub("_", value)
    cleaned = cleaned.strip("._")
    if not cleaned:
        cleaned = sha256(value.encode("utf-8")).hexdigest()
    return cleaned


def safe_path(root: Path, name: str, suffix: str = ".json") -> Path:
    root = root.resolve()
    safe_name = sanitise_identifier(name)
    candidate = (root / f"{safe_name}{suffix}").resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError(f"Resolved path {candidate} escapes storage root {root}")
    return candidate


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


class ManifestError(RuntimeError):
    """Base error class for encrypted manifest operations."""


class ManifestEncryptionError(ManifestError):
    """Raised when the encryption key is missing or invalid."""


class ManifestIntegrityError(ManifestError):
    """Raised when encrypted payload integrity checks fail."""


class ManifestExpired(ManifestError):
    """Raised when a manifest has passed its retention window."""


def load_manifest_key(path: Path) -> bytes:
    if not path:
        raise ManifestEncryptionError("Manifest encryption key path is not configured")
    path = Path(path)
    if not path.exists():
        raise ManifestEncryptionError(f"Manifest encryption key path {path} does not exist")
    raw_bytes = path.read_bytes()
    if len(raw_bytes) == 32:
        return raw_bytes
    raw = raw_bytes.strip()
    try:
        decoded = base64.urlsafe_b64decode(raw + b"=" * ((4 - len(raw) % 4) % 4))
        if len(decoded) == 32:
            return decoded
    except (ValueError, TypeError):
        pass
    try:
        decoded = bytes.fromhex(raw.decode("ascii"))
        if len(decoded) == 32:
            return decoded
    except (ValueError, UnicodeDecodeError):
        pass
    raise ManifestEncryptionError("Manifest encryption key must be 32 bytes after decoding")


def _derive_aad(identifier: str) -> bytes:
    return sha256(identifier.encode("utf-8")).digest()


def _canonical_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def encrypt_manifest(
    payload: Dict[str, Any],
    key: bytes,
    *,
    associated_data: str,
    expires_at: datetime | None = None,
) -> Dict[str, Any]:
    nonce = os.urandom(12)
    aad = _derive_aad(associated_data)
    plaintext = _canonical_bytes(payload)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    envelope = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "associated_data": associated_data,
        "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
        "checksum": sha256(plaintext).hexdigest(),
        "length": len(plaintext),
    }
    if expires_at is not None:
        envelope["expires_at"] = expires_at.astimezone(timezone.utc).isoformat()
    return envelope


def decrypt_manifest(
    envelope: Dict[str, Any],
    key: bytes,
    *,
    associated_data: str | None = None,
) -> Dict[str, Any]:
    expires_at = envelope.get("expires_at")
    if expires_at:
        try:
            expiry_ts = datetime.fromisoformat(str(expires_at))
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise ManifestIntegrityError("Invalid manifest expiry timestamp") from exc
        if datetime.now(timezone.utc) >= expiry_ts:
            raise ManifestExpired("Manifest retention window elapsed")
    expected_identifier = str(envelope.get("associated_data", ""))
    identifier = associated_data or expected_identifier
    if not identifier:
        raise ManifestIntegrityError("Associated data missing for manifest decryption")
    if expected_identifier and associated_data and expected_identifier != associated_data:
        raise ManifestIntegrityError("Associated data mismatch detected")
    try:
        nonce = base64.urlsafe_b64decode(str(envelope["nonce"]).encode("ascii"))
        ciphertext = base64.urlsafe_b64decode(str(envelope["ciphertext"]).encode("ascii"))
    except KeyError as exc:  # pragma: no cover - guard rail
        raise ManifestIntegrityError("Malformed encrypted manifest") from exc
    aad = _derive_aad(identifier)
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
    except Exception as exc:  # pragma: no cover - crypto failures should be rare
        raise ManifestIntegrityError("Unable to decrypt manifest payload") from exc
    checksum = sha256(plaintext).hexdigest()
    expected_checksum = str(envelope.get("checksum", ""))
    if checksum != expected_checksum:
        raise ManifestIntegrityError("Manifest checksum mismatch")
    expected_length = int(envelope.get("length", len(plaintext)))
    if expected_length != len(plaintext):
        raise ManifestIntegrityError("Manifest length mismatch")
    return json.loads(plaintext.decode("utf-8"))


def ensure_retention_days(days: int) -> int:
    return max(1, int(days))


def retention_expiry(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=ensure_retention_days(days))
