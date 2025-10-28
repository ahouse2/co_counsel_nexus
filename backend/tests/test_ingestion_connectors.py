import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from backend.app import config
from backend.app.models.api import IngestionSource
from backend.app.services.ingestion_sources import (
    OneDriveSourceConnector,
    S3SourceConnector,
    SharePointSourceConnector,
)
from backend.app.utils.credentials import CredentialRegistry


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, content: bytes = b"", text: str | None = None):
        self.status_code = status_code
        self._json = json_data or {}
        self._content = content
        self.text = text or ""

    def json(self) -> dict:
        return self._json

    @property
    def content(self) -> bytes:
        return self._content


def _prime_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, registry_payload: dict) -> tuple:
    workspace_dir = tmp_path / "workspaces"
    registry_path = tmp_path / "credentials.json"
    registry_path.write_text(json.dumps(registry_payload))
    monkeypatch.setenv("INGESTION_WORKSPACE_DIR", str(workspace_dir))
    monkeypatch.setenv("CREDENTIALS_REGISTRY_PATH", str(registry_path))
    config.reset_settings_cache()
    settings = config.get_settings()
    registry = CredentialRegistry(settings.credentials_registry_path)
    return settings, registry


def test_s3_connector_materializes_objects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings, registry = _prime_settings(
        tmp_path,
        monkeypatch,
        {
            "s3-default": {
                "bucket": "case-bucket",
                "access_key": "abc",
                "secret_key": "xyz",
                "prefix": "folder/",
            }
        },
    )

    class FakePaginator:
        def paginate(self, Bucket: str, Prefix: str):
            assert Bucket == "case-bucket"
            assert Prefix == "folder/"
            yield {
                "Contents": [
                    {"Key": "folder/report.txt"},
                    {"Key": "folder/nested/notes.txt"},
                ]
            }

    class FakeClient:
        def get_paginator(self, name: str) -> FakePaginator:
            assert name == "list_objects_v2"
            return FakePaginator()

        def download_file(self, bucket: str, key: str, destination: str) -> None:
            Path(destination).write_text(f"downloaded:{bucket}:{key}")

    class FakeSession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def client(self, name: str) -> FakeClient:
            assert name == "s3"
            return FakeClient()

    import boto3

    monkeypatch.setattr(boto3.session, "Session", FakeSession)

    connector = S3SourceConnector(settings, registry, logging.getLogger("test"))
    source = IngestionSource(type="s3", path="folder/", credRef="s3-default")
    materialized = connector.materialize("job-1", 0, source)

    files = sorted(str(path.relative_to(materialized.root)) for path in materialized.root.rglob("*") if path.is_file())
    assert files == ["nested/notes.txt", "report.txt"]
    assert materialized.origin == "s3://case-bucket/folder/"


class FakeFile:
    def __init__(self, name: str, server_url: str, content: bytes) -> None:
        self.name = name
        self.serverRelativeUrl = server_url
        self._content = content

    def download(self, handle):
        handle.write(self._content)
        return self

    def execute_query(self):  # noqa: D401 - sharepoint compatibility
        return None


class FakeFolder:
    def __init__(self, name: str, server_url: str, files: list[FakeFile] | None = None, subfolders: list["FakeFolder"] | None = None) -> None:
        self.name = name
        self.serverRelativeUrl = server_url
        self.files = files or []
        self.folders = subfolders or []


class FakeClientContext:
    folders: dict[str, FakeFolder] = {}

    def __init__(self, site_url: str) -> None:
        self.site_url = site_url
        self.web = self

    @classmethod
    def prime(cls, mapping: dict[str, FakeFolder]) -> None:
        cls.folders = mapping

    def with_credentials(self, _credentials) -> "FakeClientContext":
        return self

    def get_folder_by_server_relative_url(self, url: str) -> FakeFolder:
        return self.folders[url]

    def load(self, _obj) -> None:  # noqa: D401 - sharepoint compatibility
        return None

    def execute_query(self) -> None:  # noqa: D401 - sharepoint compatibility
        return None


class FakeClientCredential:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret


def test_sharepoint_connector_materializes_folders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings, registry = _prime_settings(
        tmp_path,
        monkeypatch,
        {
            "sp-default": {
                "site_url": "https://example.sharepoint.com/sites/legal",
                "client_id": "client",
                "client_secret": "secret",
            }
        },
    )

    root_folder = FakeFolder(
        name="CaseFiles",
        server_url="/sites/legal/CaseFiles",
        files=[FakeFile("summary.txt", "/sites/legal/CaseFiles/summary.txt", b"root summary")],
        subfolders=[
            FakeFolder(
                name="Depositions",
                server_url="/sites/legal/CaseFiles/Depositions",
                files=[FakeFile("depo1.txt", "/sites/legal/CaseFiles/Depositions/depo1.txt", b"deposition")],
            )
        ],
    )
    FakeClientContext.prime(
        {
            "/sites/legal/CaseFiles": root_folder,
            "/sites/legal/CaseFiles/Depositions": root_folder.folders[0],
        }
    )

    monkeypatch.setitem(
        sys.modules,
        "office365.runtime.auth.client_credential",
        SimpleNamespace(ClientCredential=FakeClientCredential),
    )
    monkeypatch.setitem(
        sys.modules,
        "office365.sharepoint.client_context",
        SimpleNamespace(ClientContext=FakeClientContext),
    )

    connector = SharePointSourceConnector(settings, registry, logging.getLogger("test"))
    source = IngestionSource(type="SharePoint", path="/sites/legal/CaseFiles", credRef="sp-default")
    materialized = connector.materialize("job-2", 1, source)

    summary = (materialized.root / "summary.txt").read_bytes()
    depo = (materialized.root / "Depositions" / "depo1.txt").read_bytes()
    assert summary == b"root summary"
    assert depo == b"deposition"


class FakeHttpxClient:
    instances: list["FakeHttpxClient"] = []

    def __init__(self, *_, **__):
        self.__class__.instances.append(self)
        self.is_token_client = len(self.__class__.instances) == 1

    def __enter__(self) -> "FakeHttpxClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False

    def post(self, url: str, data=None):
        assert self.is_token_client
        assert "oauth2" in url
        return FakeResponse(200, {"access_token": "token-value"})

    def get(self, url: str, headers=None, follow_redirects: bool = True):
        assert not self.is_token_client
        if url.endswith("/root:/cases"):
            return FakeResponse(200, {"id": "root123", "name": "cases"})
        if url.endswith("/items/root123/children"):
            return FakeResponse(
                200,
                {
                    "value": [
                        {"id": "file1", "name": "summary.txt", "file": {}},
                        {"id": "folderA", "name": "nested", "folder": {}},
                    ]
                },
            )
        if url.endswith("/items/folderA/children"):
            return FakeResponse(200, {"value": [{"id": "file2", "name": "notes.txt", "file": {}}]})
        if url.endswith("/items/file1/content"):
            return FakeResponse(200, {}, b"summary")
        if url.endswith("/items/file2/content"):
            return FakeResponse(200, {}, b"nested")
        raise AssertionError(f"Unexpected URL {url}")


def test_onedrive_connector_materializes_hierarchy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings, registry = _prime_settings(
        tmp_path,
        monkeypatch,
        {
            "od-default": {
                "tenant_id": "tenant",
                "client_id": "client",
                "client_secret": "secret",
                "drive_id": "drive",
            }
        },
    )

    FakeHttpxClient.instances = []
    monkeypatch.setattr("backend.app.services.ingestion_sources.httpx.Client", FakeHttpxClient)

    connector = OneDriveSourceConnector(settings, registry, logging.getLogger("test"))
    connector._sleep = lambda _delay: None
    source = IngestionSource(type="OneDrive", path="cases", credRef="od-default")
    materialized = connector.materialize("job-3", 2, source)

    files = sorted(str(path.relative_to(materialized.root)) for path in materialized.root.rglob("*") if path.is_file())
    assert files == ["nested/notes.txt", "summary.txt"]
    assert (materialized.root / "summary.txt").read_bytes() == b"summary"
    assert (materialized.root / "nested" / "notes.txt").read_bytes() == b"nested"
    assert materialized.origin == "onedrive:drive/cases"


def test_onedrive_missing_required_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings, registry = _prime_settings(
        tmp_path,
        monkeypatch,
        {
            "od-missing": {
                "tenant_id": "tenant",
                "client_id": "client",
                "client_secret": "secret",
            }
        },
    )
    connector = OneDriveSourceConnector(settings, registry, logging.getLogger("test"))
    source = IngestionSource(type="OneDrive", credRef="od-missing")
    with pytest.raises(HTTPException) as excinfo:
        connector.materialize("job-4", 0, source)
    assert excinfo.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TokenFailureClient:
    def __init__(self, *_, **__):
        pass

    def __enter__(self) -> "TokenFailureClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False

    def post(self, url: str, data=None):
        return FakeResponse(500, text="upstream error")

    def get(self, url: str, headers=None, follow_redirects: bool = True):  # pragma: no cover - not invoked in failure path
        raise AssertionError("Graph client should not be used when token acquisition fails")


def test_onedrive_token_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings, registry = _prime_settings(
        tmp_path,
        monkeypatch,
        {
            "od-token": {
                "tenant_id": "tenant",
                "client_id": "client",
                "client_secret": "secret",
                "drive_id": "drive",
            }
        },
    )
    monkeypatch.setattr("backend.app.services.ingestion_sources.httpx.Client", TokenFailureClient)
    connector = OneDriveSourceConnector(settings, registry, logging.getLogger("test"))
    source = IngestionSource(type="OneDrive", credRef="od-token")
    with pytest.raises(HTTPException) as excinfo:
        connector.materialize("job-5", 0, source)
    assert excinfo.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "token request" in excinfo.value.detail
