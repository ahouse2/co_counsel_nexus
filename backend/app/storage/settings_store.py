from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from ..utils.storage import (
    ManifestError,
    ManifestEncryptionError,
    atomic_write_json,
    decrypt_manifest,
    encrypt_manifest,
    load_manifest_key,
    read_json,
)


class SettingsStoreError(RuntimeError):
    """Base error for settings persistence failures."""


class SettingsStore:
    """Encrypted persistence for operator-configurable runtime settings."""

    _ASSOCIATED_DATA = "application-settings-v1"

    def __init__(self, path: Path, key_path: Path | None) -> None:
        self._path = Path(path).expanduser().resolve()
        self._key_path = Path(key_path).expanduser().resolve() if key_path else None

    def load(self) -> Dict[str, Any]:
        """Return decrypted settings payload, falling back to empty payload on error."""

        try:
            envelope = read_json(self._path)
        except FileNotFoundError:
            return {}
        try:
            key = load_manifest_key(self._key_path)
        except ManifestEncryptionError:
            return {}
        try:
            return decrypt_manifest(envelope, key, associated_data=self._ASSOCIATED_DATA)
        except ManifestError:
            return {}

    def save(self, payload: Dict[str, Any]) -> None:
        """Persist the supplied payload."""

        if not self._key_path:
            raise SettingsStoreError("Manifest encryption key path is not configured")
        key = load_manifest_key(self._key_path)
        envelope = encrypt_manifest(
            payload,
            key,
            associated_data=self._ASSOCIATED_DATA,
        )
        envelope["saved_at"] = datetime.now(timezone.utc).isoformat()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._path, envelope)

