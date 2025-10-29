from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pytest

from backend.app.utils.storage import (
    ManifestEncryptionError,
    ManifestExpired,
    ManifestIntegrityError,
    atomic_write_json,
    decrypt_manifest,
    encrypt_manifest,
    load_manifest_key,
    read_json,
    safe_path,
    sanitise_identifier,
)

def test_sanitise_identifier_normalises_values() -> None:
    assert sanitise_identifier("../weird\nname") == "weird_name"
    hashed = sanitise_identifier("!!!")
    assert len(hashed) == 64  # sha256 fallback


def test_safe_path_guards_traversal(tmp_path: Path) -> None:
    safe = safe_path(tmp_path, "case::id")
    assert safe.parent == tmp_path.resolve()
    escape = safe_path(tmp_path, "../../escape")
    assert escape.parent == tmp_path.resolve()
    assert escape.name.endswith(".json")


def test_atomic_write_and_read_json(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"
    atomic_write_json(target, {"value": 1})
    assert target.exists()
    assert read_json(target) == {"value": 1}

    with target.open("w", encoding="utf-8") as handle:
        handle.write("not-json")
    with pytest.raises(json.JSONDecodeError):
        read_json(target)


def test_encrypt_manifest_round_trip(tmp_path: Path) -> None:
    key = os.urandom(32)
    payload = {"id": "doc-1", "value": 42}
    expires = datetime.now(timezone.utc) + timedelta(days=2)
    envelope = encrypt_manifest(payload, key, associated_data="doc-1", expires_at=expires)
    path = tmp_path / "doc.json"
    atomic_write_json(path, envelope)
    loaded = read_json(path)
    assert decrypt_manifest(loaded, key, associated_data="doc-1") == payload


def test_decrypt_manifest_detects_tampering(tmp_path: Path) -> None:
    key = os.urandom(32)
    payload = {"id": "doc-2", "value": 11}
    envelope = encrypt_manifest(payload, key, associated_data="doc-2", expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    envelope["ciphertext"] = envelope["ciphertext"][:-4] + "ABCD"
    with pytest.raises(ManifestIntegrityError):
        decrypt_manifest(envelope, key, associated_data="doc-2")


def test_decrypt_manifest_enforces_expiry() -> None:
    key = os.urandom(32)
    payload = {"id": "doc-3"}
    envelope = encrypt_manifest(payload, key, associated_data="doc-3", expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    with pytest.raises(ManifestExpired):
        decrypt_manifest(envelope, key, associated_data="doc-3")


def test_load_manifest_key_accepts_base64(tmp_path: Path) -> None:
    key_bytes = os.urandom(32)
    key_path = tmp_path / "key.b64"
    key_path.write_text(json.dumps({"key": key_bytes.hex()}))
    with pytest.raises(ManifestEncryptionError):
        load_manifest_key(key_path)
    # Overwrite with urlsafe base64
    key_path.write_text(base64.urlsafe_b64encode(key_bytes).decode("ascii"))
    loaded = load_manifest_key(key_path)
    assert loaded == key_bytes
