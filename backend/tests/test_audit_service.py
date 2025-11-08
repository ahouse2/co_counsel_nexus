
import json
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.security.authz import Principal
from backend.app.services.audit import AuditService, get_audit_service, reset_audit_service_cache


@pytest.fixture
def temp_log_file(tmp_path: Path) -> Path:
    return tmp_path / "audit.log"


@pytest.fixture
def audit_service(temp_log_file: Path) -> AuditService:
    return AuditService(log_path=temp_log_file)


@pytest.fixture
def test_principal() -> Principal:
    return Principal(subject="test-user", claims={"roles": ["user"]})


def test_log_event(audit_service: AuditService, temp_log_file: Path, test_principal: Principal):
    # Arrange
    event_type = "TEST_EVENT"
    resource_id = str(uuid4())
    details = {"foo": "bar"}

    # Act
    audit_service.log_event(event_type, test_principal, resource_id, details)

    # Assert
    with open(temp_log_file, "r") as f:
        log_entry = json.loads(f.readline())

    assert log_entry["event_type"] == event_type
    assert log_entry["principal_id"] == test_principal.subject
    assert log_entry["resource_id"] == resource_id
    assert log_entry["details"] == details
    assert "event_id" in log_entry
    assert "timestamp" in log_entry


def test_get_audit_service_singleton(temp_log_file: Path):
    # Arrange
    reset_audit_service_cache()
    from backend.app.config import get_settings
    settings = get_settings()
    settings.audit_log_path = temp_log_file

    # Act
    service1 = get_audit_service()
    service2 = get_audit_service()

    # Assert
    assert service1 is service2

    # Cleanup
    reset_audit_service_cache()
