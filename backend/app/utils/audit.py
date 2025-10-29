from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any, Dict

from ..config import get_settings

_GENESIS_HASH = "0" * 64


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalise(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {str(key): _normalise(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    if isinstance(value, set):
        return [_normalise(item) for item in sorted(value)]
    return value


def _canonical_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True)
class AuditEvent:
    """Structured representation for a single audit event."""

    category: str
    action: str
    actor: Dict[str, Any]
    subject: Dict[str, Any]
    outcome: str
    severity: str = "info"
    correlation_id: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)

    def to_payload(self) -> Dict[str, Any]:
        actor_payload = _normalise(self.actor)
        subject_payload = _normalise(self.subject)
        metadata_payload = _normalise(self.metadata)
        created_at = _normalise(self.created_at)
        lineage_source = f"{actor_payload.get('id') or actor_payload.get('client_id') or actor_payload.get('subject') or 'anonymous'}::{self.category}::{self.action}"
        lineage = sha256(lineage_source.encode("utf-8")).hexdigest()[:32]
        payload: Dict[str, Any] = {
            "version": 1,
            "timestamp": created_at,
            "category": self.category,
            "action": self.action,
            "actor": actor_payload,
            "subject": subject_payload,
            "outcome": self.outcome,
            "severity": self.severity,
            "correlation_id": self.correlation_id,
            "metadata": metadata_payload,
            "lineage": lineage,
        }
        return payload


class AuditTrail:
    """Append-only JSONL ledger with hash chaining for privileged events."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self.path.exists():
            return _GENESIS_HASH
        last_hash = _GENESIS_HASH
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                candidate = record.get("hash")
                if isinstance(candidate, str) and len(candidate) == 64:
                    last_hash = candidate
        return last_hash or _GENESIS_HASH

    def append(self, event: AuditEvent) -> str:
        payload = event.to_payload()
        canonical = _canonical_payload(payload)
        with self._lock:
            prev_hash = self._last_hash or _GENESIS_HASH
            event_hash = sha256(f"{prev_hash}:{canonical}".encode("utf-8")).hexdigest()
            record = dict(payload)
            record["prev_hash"] = prev_hash
            record["hash"] = event_hash
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
            self._last_hash = event_hash
        return event_hash

    def verify(self) -> bool:
        prev_hash = _GENESIS_HASH
        if not self.path.exists():
            return True
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                expected_prev = record.get("prev_hash") or _GENESIS_HASH
                if expected_prev != prev_hash:
                    return False
                record_hash = record.get("hash")
                payload = {key: value for key, value in record.items() if key not in {"hash", "prev_hash"}}
                canonical = _canonical_payload(payload)
                computed = sha256(f"{prev_hash}:{canonical}".encode("utf-8")).hexdigest()
                if record_hash != computed:
                    return False
                prev_hash = record_hash
        return True


_AUDIT_LOCK = Lock()
_AUDIT_INSTANCE: AuditTrail | None = None


def get_audit_trail() -> AuditTrail:
    global _AUDIT_INSTANCE
    with _AUDIT_LOCK:
        if _AUDIT_INSTANCE is None:
            settings = get_settings()
            _AUDIT_INSTANCE = AuditTrail(settings.audit_log_path)
        return _AUDIT_INSTANCE


def reset_audit_trail() -> None:
    global _AUDIT_INSTANCE
    with _AUDIT_LOCK:
        _AUDIT_INSTANCE = None
