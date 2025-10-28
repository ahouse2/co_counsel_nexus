from __future__ import annotations

import base64
import binascii
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding

LOGGER = logging.getLogger("backend.security.mtls")


@dataclass(frozen=True)
class ClientIdentity:
    """Authenticated client metadata extracted from the mTLS registry."""

    subject: str
    fingerprint: str
    client_id: str
    tenant_id: str
    roles: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegistryEntry:
    subject: str
    fingerprint: str
    client_id: str
    tenant_id: str
    roles: Set[str]
    metadata: Dict[str, Any]


@dataclass
class MTLSConfig:
    ca_path: Path
    registry_path: Path
    header_name: str = "x-client-cert"
    optional_paths: Iterable[str] = field(default_factory=lambda: {"/health"})
    clock_skew_seconds: int = 60


class MTLSMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing mutual TLS by validating presented client certificates."""

    def __init__(self, app, config: MTLSConfig) -> None:  # type: ignore[override]
        super().__init__(app)
        self.config = config
        self.ca_certificate = self._load_ca_certificate(config.ca_path)
        self.registry = self._load_registry(config.registry_path)
        self.optional_paths = {str(path) for path in config.optional_paths}

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path in self.optional_paths:
            return await call_next(request)

        try:
            header_value = request.headers.get(self.config.header_name)
            if not header_value:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Client certificate required")

            certificate = self._parse_certificate(header_value)
            self._validate_chain(certificate)
            self._validate_validity_window(certificate)

            fingerprint = self._format_fingerprint(certificate.fingerprint(hashes.SHA256()))
            entry = self.registry.get(fingerprint)
            if not entry:
                LOGGER.warning("Unregistered client fingerprint", extra={"fingerprint": fingerprint})
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client certificate not authorised")

            subject = certificate.subject.rfc4514_string()
            if subject != entry.subject:
                LOGGER.warning(
                    "Client subject mismatch", extra={"expected": entry.subject, "presented": subject}
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client certificate subject mismatch")

            identity = ClientIdentity(
                subject=subject,
                fingerprint=fingerprint,
                client_id=entry.client_id,
                tenant_id=entry.tenant_id,
                roles=set(entry.roles),
                metadata=dict(entry.metadata),
            )
            request.state.client_identity = identity
            LOGGER.debug(
                "Authenticated client via mTLS",
                extra={"client_id": identity.client_id, "tenant_id": identity.tenant_id, "roles": sorted(identity.roles)},
            )
            return await call_next(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @staticmethod
    def _load_ca_certificate(path: Path) -> x509.Certificate:
        if not path.exists():
            raise RuntimeError(f"CA certificate path {path} does not exist")
        data = path.read_bytes()
        try:
            return x509.load_pem_x509_certificate(data)
        except ValueError as exc:  # pragma: no cover - guard rail
            raise RuntimeError(f"Unable to parse CA certificate at {path}") from exc

    @staticmethod
    def _load_registry(path: Path) -> Dict[str, RegistryEntry]:
        if not path.exists():
            raise RuntimeError(f"mTLS registry path {path} does not exist")
        payload = json.loads(path.read_text())
        clients = payload.get("clients", [])
        registry: Dict[str, RegistryEntry] = {}
        for client in clients:
            fingerprint = MTLSMiddleware._normalise_fingerprint(str(client.get("fingerprint", "")))
            if not fingerprint:
                continue
            entry = RegistryEntry(
                subject=str(client.get("subject", "")),
                fingerprint=fingerprint,
                client_id=str(client.get("client_id", fingerprint)),
                tenant_id=str(client.get("tenant_id", "")),
                roles={str(role) for role in client.get("roles", [])},
                metadata={key: value for key, value in client.get("metadata", {}).items()},
            )
            registry[fingerprint] = entry
        if not registry:
            raise RuntimeError("mTLS registry contains no authorised clients")
        return registry

    def _parse_certificate(self, header_value: str) -> x509.Certificate:
        try:
            decoded = base64.b64decode(header_value.encode("ascii"), validate=True)
        except (ValueError, binascii.Error):
            decoded = header_value.encode("ascii")
        try:
            return x509.load_pem_x509_certificate(decoded)
        except ValueError as exc:
            LOGGER.error("Failed to parse presented client certificate")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client certificate") from exc

    def _validate_chain(self, certificate: x509.Certificate) -> None:
        ca_public_key = self.ca_certificate.public_key()
        try:
            if isinstance(ca_public_key, rsa.RSAPublicKey):
                ca_public_key.verify(
                    certificate.signature,
                    certificate.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    certificate.signature_hash_algorithm,
                )
            elif isinstance(ca_public_key, ec.EllipticCurvePublicKey):
                ca_public_key.verify(
                    certificate.signature,
                    certificate.tbs_certificate_bytes,
                    ec.ECDSA(certificate.signature_hash_algorithm),
                )
            else:  # pragma: no cover - defensive guard for unsupported key types
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unsupported CA key type",
                )
        except InvalidSignature as exc:
            LOGGER.warning("Client certificate signature invalid")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client certificate signature") from exc
        if certificate.issuer != self.ca_certificate.subject:
            LOGGER.warning(
                "Client certificate issuer mismatch",
                extra={"expected": self.ca_certificate.subject.rfc4514_string(), "actual": certificate.issuer.rfc4514_string()},
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Client certificate issuer mismatch")

    def _validate_validity_window(self, certificate: x509.Certificate) -> None:
        now = datetime.now(timezone.utc)
        not_before = certificate.not_valid_before_utc
        not_after = certificate.not_valid_after_utc
        skew = self.config.clock_skew_seconds
        if now < not_before - timedelta(seconds=skew) or now > not_after + timedelta(seconds=skew):  # type: ignore[name-defined]
            LOGGER.warning(
                "Client certificate outside validity window",
                extra={
                    "not_before": not_before.isoformat(),
                    "not_after": not_after.isoformat(),
                    "now": now.isoformat(),
                },
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Client certificate expired or not yet valid")

    @staticmethod
    def _format_fingerprint(raw: bytes) -> str:
        return ":".join(f"{byte:02X}" for byte in raw)

    @staticmethod
    def _normalise_fingerprint(value: str) -> str:
        digits = value.replace(":", "").replace(" ", "").upper()
        if not digits:
            return ""
        return ":".join(digits[i : i + 2] for i in range(0, len(digits), 2))

