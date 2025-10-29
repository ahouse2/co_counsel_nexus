from __future__ import annotations

import base64
import json
import importlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Iterable, Sequence

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import config
from backend.app.security.dependencies import reset_security_caches
from backend.app.utils.audit import reset_audit_trail


@dataclass
class SecurityMaterials:
    certificate_pem: str
    ca_cert_path: Path
    registry_path: Path
    jwks_path: Path
    private_key: rsa.RSAPrivateKey
    ca_private_key: rsa.RSAPrivateKey
    ca_certificate: x509.Certificate
    header_name: str
    tenant_id: str
    client_id: str
    issuer: str

    def certificate_header(self) -> str:
        return base64.b64encode(self.certificate_pem.encode("utf-8")).decode("ascii")

    def issue_token(
        self,
        *,
        scopes: Sequence[str],
        roles: Sequence[str],
        audience: Sequence[str],
        subject: str = "user-123",
        extra: dict | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "tenant_id": self.tenant_id,
            "iss": self.issuer,
            "aud": list(audience),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "scope": " ".join(sorted(set(scopes))),
            "roles": list(roles),
        }
        if extra:
            payload.update(extra)
        headers = {"kid": "test-key"}
        token = jwt.encode(payload, self.private_key, algorithm="RS256", headers=headers)
        return token

    def auth_headers(
        self,
        *,
        scopes: Sequence[str],
        roles: Sequence[str],
        audience: Sequence[str],
        subject: str = "user-123",
        extra: dict | None = None,
    ) -> dict[str, str]:
        token = self.issue_token(scopes=scopes, roles=roles, audience=audience, subject=subject, extra=extra)
        return {
            "Authorization": f"Bearer {token}",
            self.header_name: self.certificate_header(),
        }


def _generate_ca_pair() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CoCounsel Test CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, "CoCounsel Root CA"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _generate_client_cert(
    ca_key: rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
    *,
    tenant_id: str,
    client_id: str,
) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CoCounsel Client"),
            x509.NameAttribute(NameOID.COMMON_NAME, client_id),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=5))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=180))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(client_id)]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    return key, cert


def _write_jwks(path: Path, public_key: rsa.RSAPublicKey) -> None:
    numbers = public_key.public_numbers()
    n = base64.urlsafe_b64encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")).rstrip(b"=").decode("ascii")
    e = base64.urlsafe_b64encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")).rstrip(b"=").decode("ascii")
    jwks = {"keys": [{"kty": "RSA", "kid": "test-key", "alg": "RS256", "use": "sig", "n": n, "e": e}]}
    path.write_text(json.dumps(jwks))


def _write_registry(path: Path, *, client_cert: x509.Certificate, tenant_id: str, client_id: str, roles: Iterable[str]) -> None:
    fingerprint = client_cert.fingerprint(hashes.SHA256())
    fingerprint_str = ":".join(f"{byte:02X}" for byte in fingerprint)
    registry = {
        "clients": [
            {
                "subject": client_cert.subject.rfc4514_string(),
                "fingerprint": fingerprint_str,
                "client_id": client_id,
                "tenant_id": tenant_id,
                "roles": list(roles),
            }
        ]
    }
    path.write_text(json.dumps(registry))


@pytest.fixture()
def security_materials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SecurityMaterials:
    ca_key, ca_cert = _generate_ca_pair()
    tenant_id = "tenant-alpha"
    client_id = "case-coordinator"
    client_key, client_cert = _generate_client_cert(ca_key, ca_cert, tenant_id=tenant_id, client_id=client_id)

    ca_path = tmp_path / "ca.pem"
    ca_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))

    cert_path = tmp_path / "client.pem"
    cert_path.write_bytes(client_cert.public_bytes(serialization.Encoding.PEM))

    registry_path = tmp_path / "registry.json"
    _write_registry(
        registry_path,
        client_cert=client_cert,
        tenant_id=tenant_id,
        client_id=client_id,
        roles=[
            "CaseCoordinator",
            "ResearchAnalyst",
            "ComplianceAuditor",
            "PlatformEngineer",
            "ForensicsOperator",
            "CustomerSuccessManager",
            "ExecutiveSponsor",
        ],
    )

    jwks_path = tmp_path / "jwks.json"
    _write_jwks(jwks_path, client_key.public_key())

    header_name = "X-Client-Cert"
    issuer = "https://auth.cocounsel.test"

    monkeypatch.setenv("SECURITY_MTLS_CA_PATH", str(ca_path))
    monkeypatch.setenv("SECURITY_MTLS_REGISTRY_PATH", str(registry_path))
    monkeypatch.setenv("SECURITY_MTLS_HEADER", header_name)
    monkeypatch.setenv("SECURITY_OAUTH_JWKS_PATH", str(jwks_path))
    monkeypatch.setenv("SECURITY_TOKEN_ISSUER", issuer)

    config.reset_settings_cache()
    reset_security_caches()

    certificate_pem = client_cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return SecurityMaterials(
        certificate_pem=certificate_pem,
        ca_cert_path=ca_path,
        registry_path=registry_path,
        jwks_path=jwks_path,
        private_key=client_key,
        ca_private_key=ca_key,
        ca_certificate=ca_cert,
        header_name=header_name,
        tenant_id=tenant_id,
        client_id=client_id,
        issuer=issuer,
    )


@pytest.fixture()
def auth_headers_factory(security_materials: SecurityMaterials):
    default_scopes = [
        "ingest:enqueue",
        "ingest:status",
        "query:read",
        "query:trace",
        "timeline:read",
        "graph:read",
        "forensics:read",
        "forensics:document",
        "forensics:image",
        "forensics:financial",
        "agents:run",
        "agents:read",
        "billing:read",
        "knowledge:read",
        "knowledge:write",
    ]
    default_roles = [
        "CaseCoordinator",
        "ResearchAnalyst",
        "ComplianceAuditor",
        "PlatformEngineer",
        "ForensicsOperator",
    ]
    default_audience = [
        "co-counsel.ingest",
        "co-counsel.query",
        "co-counsel.timeline",
        "co-counsel.graph",
        "co-counsel.forensics",
        "co-counsel.agents",
        "co-counsel.billing",
        "co-counsel.knowledge",
    ]

    def factory(
        *,
        scopes: Sequence[str] | None = None,
        roles: Sequence[str] | None = None,
        audience: Sequence[str] | None = None,
        subject: str = "user-123",
        extra: dict | None = None,
    ) -> dict[str, str]:
        return security_materials.auth_headers(
            scopes=scopes or default_scopes,
            roles=roles or default_roles,
            audience=audience or default_audience,
            subject=subject,
            extra=extra,
        )

    return factory


@pytest.fixture()
def sample_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()

    text = root / "case_notes.txt"
    text.write_text(
        "Acme Corporation acquired Beta LLC on 2024-10-01 after the initial filing on 2024-09-15."
    )

    image = root / "evidence.png"
    img = Image.new("RGB", (240, 80), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 20), "Acme 2024-10-02", fill="black")
    img.save(image)

    csv_file = root / "ledger.csv"
    csv_file.write_text("entity,amount\nAcme,100.0\nBeta,100.0\nBeta,400.0\n")

    return root


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, security_materials: SecurityMaterials) -> TestClient:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setenv("NEO4J_URI", "memory://")
    monkeypatch.setenv("QDRANT_PATH", ":memory:")
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.setenv("VECTOR_DIR", str(storage_root / "vector"))
    monkeypatch.setenv("FORENSICS_DIR", str(storage_root / "forensics"))
    monkeypatch.setenv("TIMELINE_PATH", str(storage_root / "timeline.jsonl"))
    monkeypatch.setenv("JOB_STORE_DIR", str(storage_root / "jobs"))
    monkeypatch.setenv("DOCUMENT_STORE_DIR", str(storage_root / "documents"))
    monkeypatch.setenv("INGESTION_WORKSPACE_DIR", str(storage_root / "workspaces"))
    monkeypatch.setenv("INGESTION_CHROMA_DIR", str(storage_root / "chroma"))
    monkeypatch.setenv("INGESTION_LLAMA_CACHE_DIR", str(storage_root / "llama_cache"))
    monkeypatch.setenv("AGENT_THREADS_DIR", str(storage_root / "agent_threads"))
    monkeypatch.setenv("BILLING_USAGE_PATH", str(storage_root / "billing" / "usage.json"))
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("KNOWLEDGE_CATALOG_PATH", str(repo_root / "docs/knowledge/catalog.json"))
    monkeypatch.setenv("KNOWLEDGE_CONTENT_DIR", str(repo_root / "docs/knowledge/best_practices"))
    monkeypatch.setenv("KNOWLEDGE_PROGRESS_PATH", str(storage_root / "knowledge" / "progress.json"))
    monkeypatch.setenv("VOICE_SESSIONS_DIR", str(storage_root / "voice" / "sessions"))
    monkeypatch.setenv("VOICE_CACHE_DIR", str(storage_root / "voice" / "cache"))
    monkeypatch.setenv("VECTOR_BACKEND", "memory")
    monkeypatch.setenv("INGESTION_COST_MODE", "community")
    monkeypatch.setenv("INGESTION_HF_MODEL", "local://tests")
    key_path = storage_root / "manifest.key"
    key_path.write_bytes(os.urandom(32))
    audit_log_path = storage_root / "audit.log"
    monkeypatch.setenv("MANIFEST_ENCRYPTION_KEY_PATH", str(key_path))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(audit_log_path))

    from backend.app import config as app_config
    from backend.app.services import graph as graph_service
    from backend.app.services import vector as vector_service
    from backend.app.telemetry.billing import reset_billing_registry

    app_config.reset_settings_cache()
    reset_security_caches()
    reset_audit_trail()
    vector_service.reset_vector_service()
    graph_service.reset_graph_service()
    reset_billing_registry()

    settings = app_config.get_settings()
    main_module = importlib.import_module("backend.app.main")
    importlib.reload(main_module)
    client_instance = TestClient(main_module.app)
    return client_instance
