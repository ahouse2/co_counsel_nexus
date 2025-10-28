from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from ..config import get_settings
from ..utils.storage import (
    ManifestExpired,
    ManifestIntegrityError,
    atomic_write_json,
    decrypt_manifest,
    encrypt_manifest,
    ensure_retention_days,
    load_manifest_key,
    read_json,
    retention_expiry,
    safe_path,
)


class JobStore:
    """Persistence layer for ingestion job manifests with encryption and retention."""

    def __init__(
        self,
        root: Path,
        *,
        key: bytes | None = None,
        retention_days: int | None = None,
    ) -> None:
        settings = get_settings()
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.key = key or load_manifest_key(settings.manifest_encryption_key_path)
        days = retention_days if retention_days is not None else settings.manifest_retention_days
        self.retention_days = ensure_retention_days(days)
        self._prune_expired()

    def _path(self, job_id: str) -> Path:
        return safe_path(self.root, job_id)

    def _expiry(self) -> datetime:
        return retention_expiry(self.retention_days)

    def _prune_expired(self) -> None:
        now = datetime.now(timezone.utc)
        for file in self.root.glob("*.json"):
            try:
                envelope = read_json(file)
            except (ValueError, OSError):
                continue
            expires_at = envelope.get("expires_at")
            if not expires_at:
                continue
            try:
                expiry_ts = datetime.fromisoformat(str(expires_at))
            except ValueError:
                continue
            if expiry_ts <= now:
                file.unlink(missing_ok=True)

    def write_job(self, job_id: str, payload: Dict[str, object]) -> None:
        path = self._path(job_id)
        envelope = encrypt_manifest(payload, self.key, associated_data=job_id, expires_at=self._expiry())
        atomic_write_json(path, envelope)

    def read_job(self, job_id: str) -> Dict[str, object]:
        path = self._path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Job {job_id} missing from store")
        envelope = read_json(path)
        try:
            return decrypt_manifest(envelope, self.key, associated_data=job_id)
        except ManifestExpired as exc:
            path.unlink(missing_ok=True)
            raise FileNotFoundError(f"Job {job_id} expired") from exc
        except ManifestIntegrityError as exc:
            raise RuntimeError(f"Job {job_id} failed integrity checks") from exc

    def list_jobs(self) -> List[Dict[str, object]]:
        manifests: List[Dict[str, object]] = []
        for file in sorted(self.root.glob("*.json")):
            try:
                envelope = read_json(file)
                manifest = decrypt_manifest(envelope, self.key)
            except (ValueError, FileNotFoundError, OSError, ManifestIntegrityError, ManifestExpired):
                if file.exists():
                    try:
                        file.unlink()
                    except OSError:
                        pass
                continue
            manifests.append(manifest)
        return manifests

    def clear(self) -> None:
        for file in self.root.glob("*.json"):
            file.unlink(missing_ok=True)

