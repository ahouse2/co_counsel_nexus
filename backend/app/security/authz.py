from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from fastapi import HTTPException, status
try:
    from oso import Oso
except ImportError:
    # Mock Oso for environments where it's not available (e.g. Python 3.13)
    class Oso:
        def register_class(self, *args, **kwargs): pass
        def load_files(self, *args, **kwargs): pass
        def is_allowed(self, *args, **kwargs): return True

LOGGER = logging.getLogger("backend.security.authz")


@dataclass
class Principal:
    client_id: str
    subject: str
    tenant_id: str
    roles: Set[str] = field(default_factory=set)
    token_roles: Set[str] = field(default_factory=set)
    certificate_roles: Set[str] = field(default_factory=set)
    scopes: Set[str] = field(default_factory=set)
    case_admin: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


@dataclass
class ResourceDescriptor:
    name: str
    action: str
    tenant_id: str | None
    required_scopes: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def has_roles(self) -> bool:
        return bool(self.allowed_roles)


class AuthorizationService:
    """Evaluates authorization decisions via Oso policies."""

    def __init__(self, policy_path: Path) -> None:
        self.oso = Oso()
        self.oso.register_class(Principal)
        self.oso.register_class(ResourceDescriptor)
        self.oso.load_files([str(policy_path)])

    def authorize(self, principal: Principal, action: str, resource: ResourceDescriptor) -> None:
        try:
            allowed = self.oso.is_allowed(principal, action, resource)
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Authorization evaluation failed", extra={"action": action, "resource": resource.name})
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authorization engine failure") from exc
        if not allowed:
            LOGGER.warning(
                "Authorization denied",
                extra={
                    "client_id": principal.client_id,
                    "subject": principal.subject,
                    "tenant_id": principal.tenant_id,
                    "action": action,
                    "resource": resource.name,
                    "roles": sorted(principal.roles),
                    "scopes": sorted(principal.scopes),
                },
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def build_resource(
    name: str,
    action: str,
    tenant_id: str | None,
    *,
    scopes: Iterable[str],
    roles: Iterable[str],
    attributes: Dict[str, Any] | None = None,
) -> ResourceDescriptor:
    return ResourceDescriptor(
        name=name,
        action=action,
        tenant_id=tenant_id,
        required_scopes=list(scopes),
        allowed_roles=list(roles),
        attributes=attributes or {},
    )

