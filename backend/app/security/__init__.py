"""Security utilities for the Co-Counsel API."""

from .authz import AuthorizationService, Principal, ResourceDescriptor
from .dependencies import (
    authorize_agents_read,
    authorize_agents_run,
    authorize_forensics_document,
    authorize_forensics_financial,
    authorize_forensics_image,
    authorize_graph_read,
    authorize_ingest_enqueue,
    authorize_ingest_status,
    authorize_query,
    authorize_timeline,
    get_authorization_service,
)
from .mtls import ClientIdentity, MTLSConfig, MTLSMiddleware
from .oauth import OAuthValidator, TokenClaims
from .privilege_policy import (
    PrivilegePolicyDecision,
    PrivilegePolicyEngine,
    get_privilege_policy_engine,
    reset_privilege_policy_engine,
)

__all__ = [
    "AuthorizationService",
    "authorize_agents_read",
    "authorize_agents_run",
    "authorize_forensics_document",
    "authorize_forensics_financial",
    "authorize_forensics_image",
    "authorize_graph_read",
    "authorize_ingest_enqueue",
    "authorize_ingest_status",
    "authorize_query",
    "authorize_timeline",
    "ClientIdentity",
    "MTLSConfig",
    "MTLSMiddleware",
    "OAuthValidator",
    "Principal",
    "ResourceDescriptor",
    "TokenClaims",
    "get_authorization_service",
    "PrivilegePolicyDecision",
    "PrivilegePolicyEngine",
    "get_privilege_policy_engine",
    "reset_privilege_policy_engine",
]
