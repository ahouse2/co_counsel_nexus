from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Dict, Iterator, List, Tuple


@dataclass(frozen=True)
class ChainEntry:
    index: int
    timestamp: str
    actor: str
    action: str
    payload: Dict[str, object]
    prev_hash: str
    digest: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "digest": self.digest,
        }


class ForensicsChainLedger:
    """Tamper-evident append-only ledger for forensic artefacts."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    # region public API
    def append(self, actor: str, action: str, payload: Dict[str, object]) -> ChainEntry:
        payload = self._jsonable(payload)
        with self._lock:
            entries = list(self.iter_entries())
            index = entries[-1].index + 1 if entries else 0
            prev_hash = entries[-1].digest if entries else "0" * 64
            timestamp = datetime.now(timezone.utc).isoformat()
            canonical = self._canonical_payload(index, timestamp, actor, action, payload, prev_hash)
            digest = self._compute_digest(canonical)
            entry = ChainEntry(
                index=index,
                timestamp=timestamp,
                actor=actor,
                action=action,
                payload=payload,
                prev_hash=prev_hash,
                digest=digest,
            )
            self._append_entry(entry)
            return entry

    def iter_entries(self) -> Iterator[ChainEntry]:
        if not self.path.exists():
            return iter(())
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    yield ChainEntry(
                        index=int(payload["index"]),
                        timestamp=str(payload["timestamp"]),
                        actor=str(payload["actor"]),
                        action=str(payload["action"]),
                        payload=dict(payload.get("payload", {})),
                        prev_hash=str(payload["prev_hash"]),
                        digest=str(payload["digest"]),
                    )
                except (KeyError, TypeError, ValueError):
                    continue

    def verify(self) -> Tuple[bool, List[str]]:
        issues: List[str] = []
        prev_hash = "0" * 64
        for entry in self.iter_entries():
            canonical = self._canonical_payload(
                entry.index,
                entry.timestamp,
                entry.actor,
                entry.action,
                entry.payload,
                entry.prev_hash,
            )
            expected_digest = self._compute_digest(canonical)
            if entry.prev_hash != prev_hash:
                issues.append(
                    f"entry {entry.index} has unexpected prev_hash {entry.prev_hash} (expected {prev_hash})"
                )
            if entry.digest != expected_digest:
                issues.append(
                    f"entry {entry.index} digest mismatch (expected {expected_digest}, found {entry.digest})"
                )
            prev_hash = entry.digest
        return len(issues) == 0, issues

    def latest(self) -> ChainEntry | None:
        entries = list(self.iter_entries())
        return entries[-1] if entries else None

    # endregion

    # region internal helpers
    def _append_entry(self, entry: ChainEntry) -> None:
        line = json.dumps(entry.to_dict(), separators=(",", ":"), sort_keys=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
            handle.flush()

    @staticmethod
    def _canonical_payload(
        index: int,
        timestamp: str,
        actor: str,
        action: str,
        payload: Dict[str, object],
        prev_hash: str,
    ) -> Dict[str, object]:
        return {
            "index": index,
            "timestamp": timestamp,
            "actor": actor,
            "action": action,
            "payload": payload,
            "prev_hash": prev_hash,
        }

    @staticmethod
    def _compute_digest(payload: Dict[str, object]) -> str:
        canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return sha256(canonical).hexdigest()

    @staticmethod
    def _jsonable(payload: Dict[str, object]) -> Dict[str, object]:
        def normalise(value: object) -> object:
            if isinstance(value, dict):
                return {str(key): normalise(val) for key, val in value.items()}
            if isinstance(value, (list, tuple, set)):
                return [normalise(item) for item in value]
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, datetime):
                return value.isoformat()
            return value

        return {str(key): normalise(val) for key, val in payload.items()}

    # endregion


__all__ = ["ChainEntry", "ForensicsChainLedger"]
