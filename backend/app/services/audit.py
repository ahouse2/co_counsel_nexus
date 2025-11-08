from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..security.authz import Principal

@dataclass
class AuditEvent:
    event_id: str
    timestamp: str
    event_type: str
    principal_id: str
    resource_id: str
    details: dict

class AuditService:
    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.touch(exist_ok=True)

    def log_event(self, event_type: str, principal: Principal, resource_id: str, details: dict) -> None:
        """Logs a new audit event."""
        event = AuditEvent(
            event_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            principal_id=principal.subject if principal else "system",
            resource_id=resource_id,
            details=details,
        )
        with open(self._log_path, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")

_audit_service: AuditService | None = None

def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        from ..config import get_settings
        settings = get_settings()
        _audit_service = AuditService(log_path=settings.audit_log_path)
    return _audit_service

def reset_audit_service_cache() -> None:
    global _audit_service
    _audit_service = None
