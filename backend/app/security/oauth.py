from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Set

import jwt
from fastapi import HTTPException, status

LOGGER = logging.getLogger("backend.security.oauth")


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    tenant_id: str
    scopes: Set[str]
    roles: Set[str]
    audience: Set[str]
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    case_admin: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)


class OAuthValidator:
    """Validates OAuth2 bearer tokens against a JWKS source."""

    def __init__(self, jwks_path: Path, issuer: str, *, leeway_seconds: int = 60) -> None:
        self.jwks_path = jwks_path
        self.issuer = issuer
        self.leeway_seconds = leeway_seconds
        self._keys = self._load_keys(jwks_path)

    def validate(self, token: str, audience: str) -> TokenClaims:
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing key identifier")
        jwk = self._keys.get(kid)
        if not jwk:
            LOGGER.warning("Token presented unknown key identifier", extra={"kid": kid})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key")
        key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        algorithms = [jwk.get("alg", "RS256")]
        try:
            payload = jwt.decode(
                token,
                key=key,
                algorithms=algorithms,
                audience=audience,
                issuer=self.issuer,
                leeway=self.leeway_seconds,
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidAudienceError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token audience mismatch")
        except jwt.InvalidIssuerError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token issuer mismatch")
        except jwt.InvalidTokenError as exc:
            LOGGER.warning("Invalid bearer token", extra={"error": str(exc)})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc

        scopes = self._parse_scopes(payload.get("scope"))
        roles = self._parse_roles(payload.get("roles"))
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token missing tenant scope")

        audience_claim = payload.get("aud")
        if isinstance(audience_claim, str):
            audience_set = {audience_claim}
        elif isinstance(audience_claim, Iterable):
            audience_set = {str(item) for item in audience_claim}
        else:
            audience_set = set()

        issued_at = self._parse_timestamp(payload.get("iat"))
        expires_at = self._parse_timestamp(payload.get("exp"))
        case_admin = bool(payload.get("case_admin", False))
        attributes = {
            key: value
            for key, value in payload.items()
            if key
            not in {"sub", "scope", "roles", "aud", "iss", "exp", "iat", "tenant_id", "case_admin", "nbf"}
        }
        return TokenClaims(
            subject=str(payload.get("sub", "")),
            tenant_id=str(tenant_id),
            scopes=scopes,
            roles=roles,
            audience=audience_set,
            issued_at=issued_at,
            expires_at=expires_at,
            case_admin=case_admin,
            attributes=attributes,
        )

    @staticmethod
    def _parse_scopes(value: Any) -> Set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            return {item for item in value.split() if item}
        if isinstance(value, Iterable):
            return {str(item) for item in value if item}
        return set()

    @staticmethod
    def _parse_roles(value: Any) -> Set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            return {item.strip() for item in value.split(",") if item.strip()}
        if isinstance(value, Iterable):
            return {str(item) for item in value if item}
        return set()

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        try:
            timestamp = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError):
            return None
        return timestamp

    @staticmethod
    def _load_keys(path: Path) -> Dict[str, Dict[str, Any]]:
        if not path.exists():
            raise RuntimeError(f"JWKS path {path} does not exist")
        payload = json.loads(path.read_text())
        keys = payload.get("keys", [])
        registry: Dict[str, Dict[str, Any]] = {}
        for key in keys:
            kid = key.get("kid")
            if not kid:
                continue
            registry[str(kid)] = key
        if not registry:
            raise RuntimeError("JWKS does not contain any signing keys")
        return registry

