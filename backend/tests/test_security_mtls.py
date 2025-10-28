from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from backend.tests.conftest import SecurityMaterials


def _issue_client_certificate(
    *,
    ca_key: rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
    common_name: str,
    not_valid_before: datetime,
    not_valid_after: datetime,
) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Unauthorized Client"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .sign(ca_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def test_missing_certificate_rejected(
    client: TestClient,
    auth_headers_factory,
) -> None:
    headers = auth_headers_factory()
    headers.pop("X-Client-Cert", None)
    response = client.get("/query", params={"q": "security check"}, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Client certificate required"


def test_unknown_fingerprint_denied(
    client: TestClient,
    auth_headers_factory,
    security_materials: SecurityMaterials,
) -> None:
    now = datetime.now(timezone.utc)
    rogue_pem = _issue_client_certificate(
        ca_key=security_materials.ca_private_key,
        ca_cert=security_materials.ca_certificate,
        common_name="rogue-client",
        not_valid_before=now - timedelta(minutes=1),
        not_valid_after=now + timedelta(days=1),
    )
    headers = auth_headers_factory()
    headers[security_materials.header_name] = base64.b64encode(rogue_pem.encode("utf-8")).decode("ascii")
    response = client.get("/timeline", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Client certificate not authorised"


def test_expired_certificate_rejected(
    client: TestClient,
    auth_headers_factory,
    security_materials: SecurityMaterials,
) -> None:
    now = datetime.now(timezone.utc)
    expired_pem = _issue_client_certificate(
        ca_key=security_materials.ca_private_key,
        ca_cert=security_materials.ca_certificate,
        common_name="expired-client",
        not_valid_before=now - timedelta(days=10),
        not_valid_after=now - timedelta(days=5),
    )
    headers = auth_headers_factory()
    headers[security_materials.header_name] = base64.b64encode(expired_pem.encode("utf-8")).decode("ascii")
    response = client.get("/graph/neighbor", params={"id": "entity::acme"}, headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()
