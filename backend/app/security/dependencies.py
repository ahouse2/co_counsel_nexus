from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, Request, status

from ..config import get_settings
from .authz import AuthorizationService, Principal, build_resource
from .mtls import ClientIdentity, MTLSConfig
from .oauth import OAuthValidator


LOGGER = logging.getLogger("backend.security.dependencies")


def create_mtls_config() -> MTLSConfig:
    settings = get_settings()
    if not settings.security_mtls_ca_path or not settings.security_mtls_registry_path:
        raise RuntimeError("Security settings for mTLS are not configured")
    return MTLSConfig(
        ca_path=settings.security_mtls_ca_path,
        registry_path=settings.security_mtls_registry_path,
        header_name=settings.security_mtls_header,
        optional_paths=settings.security_mtls_optional_paths,
        clock_skew_seconds=settings.security_mtls_clock_skew,
    )


@lru_cache(maxsize=1)
def _get_oauth_validator() -> OAuthValidator:
    settings = get_settings()
    if not settings.security_oauth_jwks_path:
        raise RuntimeError("JWKS path not configured")
    if not settings.security_token_issuer:
        raise RuntimeError("Token issuer not configured")
    return OAuthValidator(
        settings.security_oauth_jwks_path,
        issuer=settings.security_token_issuer,
        leeway_seconds=settings.security_token_leeway,
    )


@lru_cache(maxsize=1)
def get_authorization_service() -> AuthorizationService:
    policy_path = Path(__file__).with_name("policy.polar")
    return AuthorizationService(policy_path)


def _extract_identity(request: Request) -> ClientIdentity:
    identity = getattr(request.state, "client_identity", None)
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Client certificate required")
    return identity


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed authorization header")
    return parts[1]


def _authorize(
    request: Request,
    *,
    resource_name: str,
    action: str,
    audience: str,
    required_scopes: Iterable[str],
    allowed_roles: Iterable[str],
):
    identity = _extract_identity(request)
    token = _extract_bearer_token(request)
    validator = _get_oauth_validator()
    claims = validator.validate(token, audience=audience)
    if identity.tenant_id != claims.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch between certificate and token")
    certificate_roles = set(identity.roles)
    token_roles = set(claims.roles)
    effective_roles = (certificate_roles & token_roles) if token_roles else certificate_roles

    principal = Principal(
        client_id=identity.client_id,
        subject=claims.subject or identity.subject,
        tenant_id=claims.tenant_id,
        roles=effective_roles,
        token_roles=token_roles,
        certificate_roles=certificate_roles,
        scopes=set(claims.scopes),
        case_admin=claims.case_admin,
        attributes={
            **identity.metadata,
            **claims.attributes,
            "token_roles": sorted(token_roles),
            "certificate_roles": sorted(certificate_roles),
        },
    )
    request.state.principal = principal

    required_scope_set = set(required_scopes)
    missing_scopes = sorted(required_scope_set - principal.scopes)
    if missing_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scope(s): {', '.join(missing_scopes)}",
        )

    allowed_role_set = set(allowed_roles)
    if allowed_role_set and not (principal.roles & allowed_role_set):
        if principal.case_admin:
            LOGGER.debug(
                "Bypassing role enforcement for case administrator",
                extra={
                    "client_id": principal.client_id,
                    "subject": principal.subject,
                    "resource": resource_name,
                    "roles": sorted(principal.roles),
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for requested resource",
            )

    resource = build_resource(
        resource_name,
        action,
        tenant_id=claims.tenant_id,
        scopes=required_scopes,
        roles=allowed_roles,
        attributes={"case_admin": claims.case_admin, **claims.attributes},
    )
    authz = get_authorization_service()
    authz.authorize(principal, action, resource)
    return principal


def _dependency(
    *,
    resource_name: str,
    action: str,
    audience: str,
    required_scopes: Iterable[str],
    allowed_roles: Iterable[str],
):
    async def wrapper(request: Request) -> Principal:
        return _authorize(
            request,
            resource_name=resource_name,
            action=action,
            audience=audience,
            required_scopes=required_scopes,
            allowed_roles=allowed_roles,
        )

    return wrapper


settings = get_settings()

authorize_ingest_enqueue = _dependency(
    resource_name="ingest.enqueue",
    action="ingest:enqueue",
    audience=settings.security_audience_ingest,
    required_scopes=["ingest:enqueue", "ingest:status"],
    allowed_roles=["CaseCoordinator", "PlatformEngineer", "AutomationService"],
)

authorize_ingest_status = _dependency(
    resource_name="ingest.status",
    action="ingest:status",
    audience=settings.security_audience_ingest,
    required_scopes=["ingest:status"],
    allowed_roles=[
        "CaseCoordinator",
        "PlatformEngineer",
        "ComplianceAuditor",
        "ForensicsOperator",
        "ResearchAnalyst",
        "AutomationService",
    ],
)

authorize_query = _dependency(
    resource_name="query.read",
    action="query:read",
    audience=settings.security_audience_query,
    required_scopes=["query:read"],
    allowed_roles=[
        "ResearchAnalyst",
        "CaseCoordinator",
        "ComplianceAuditor",
        "PlatformEngineer",
        "ForensicsOperator",
    ],
)

authorize_timeline = _dependency(
    resource_name="timeline.read",
    action="timeline:read",
    audience=settings.security_audience_timeline,
    required_scopes=["timeline:read"],
    allowed_roles=["ResearchAnalyst", "CaseCoordinator", "ComplianceAuditor"],
)

authorize_graph_read = _dependency(
    resource_name="graph.read",
    action="graph:read",
    audience=settings.security_audience_graph,
    required_scopes=["graph:read"],
    allowed_roles=[
        "ResearchAnalyst",
        "CaseCoordinator",
        "ComplianceAuditor",
        "PlatformEngineer",
        "ForensicsOperator",
    ],
)

authorize_forensics_document = _dependency(
    resource_name="forensics.document",
    action="forensics:document",
    audience=settings.security_audience_forensics,
    required_scopes=["forensics:read", "forensics:document"],
    allowed_roles=["ForensicsOperator", "ComplianceAuditor", "CaseCoordinator"],
)

authorize_forensics_image = _dependency(
    resource_name="forensics.image",
    action="forensics:image",
    audience=settings.security_audience_forensics,
    required_scopes=["forensics:read", "forensics:image"],
    allowed_roles=["ForensicsOperator", "ComplianceAuditor", "CaseCoordinator"],
)

authorize_forensics_financial = _dependency(
    resource_name="forensics.financial",
    action="forensics:financial",
    audience=settings.security_audience_forensics,
    required_scopes=["forensics:read", "forensics:financial"],
    allowed_roles=["ForensicsOperator", "ComplianceAuditor", "CaseCoordinator"],
)

authorize_agents_run = _dependency(
    resource_name="agents.run",
    action="agents:run",
    audience=settings.security_audience_agents,
    required_scopes=["agents:run"],
    allowed_roles=["ResearchAnalyst", "CaseCoordinator", "PlatformEngineer"],
)

authorize_agents_read = _dependency(
    resource_name="agents.read",
    action="agents:read",
    audience=settings.security_audience_agents,
    required_scopes=["agents:read"],
    allowed_roles=["ResearchAnalyst", "CaseCoordinator", "ComplianceAuditor", "PlatformEngineer"],
)


def reset_security_caches() -> None:
    _get_oauth_validator.cache_clear()
    get_authorization_service.cache_clear()
