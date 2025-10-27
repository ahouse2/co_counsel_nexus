from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from fastapi import HTTPException, status

from ..config import Settings
from ..models.api import IngestionSource
from ..utils.credentials import CredentialRegistry


@dataclass
class MaterializedSource:
    root: Path
    source: IngestionSource
    origin: str | None = None


class BaseSourceConnector:
    def __init__(self, settings: Settings, registry: CredentialRegistry, logger: logging.Logger) -> None:
        self.settings = settings
        self.registry = registry
        self.logger = logger

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        raise NotImplementedError


class LocalSourceConnector(BaseSourceConnector):
    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        if not source.path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Local source requires a path")
        target = Path(source.path).expanduser().resolve()
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source path {target} not found")
        if not target.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Local source must reference a directory")
        self.logger.info("Materialised local source", extra={"path": str(target)})
        return MaterializedSource(root=target, source=source, origin=str(target))


class S3SourceConnector(BaseSourceConnector):
    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="S3 ingestion requires boto3; install optional dependency",
            ) from exc

        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="S3 source requires credRef")
        credentials = self._load_credentials(source.credRef)
        bucket = credentials.get("bucket")
        if not bucket:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="S3 credential missing bucket")
        prefix = source.path or credentials.get("prefix", "")
        session = boto3.session.Session(
            aws_access_key_id=credentials.get("access_key"),
            aws_secret_access_key=credentials.get("secret_key"),
            aws_session_token=credentials.get("session_token"),
            region_name=credentials.get("region"),
        )
        client = session.client("s3")
        workspace = self._workspace(job_id, index, "s3")
        paginator = client.get_paginator("list_objects_v2")
        found = False
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj.get("Key")
                if not key or key.endswith("/"):
                    continue
                found = True
                relative = Path(key[len(prefix) :]) if prefix and key.startswith(prefix) else Path(key)
                destination = workspace / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                client.download_file(bucket, key, str(destination))
                self.logger.info(
                    "Downloaded S3 object",
                    extra={"bucket": bucket, "key": key, "destination": str(destination)},
                )
        if not found:
            self.logger.warning(
                "S3 source produced no objects",
                extra={"bucket": bucket, "prefix": prefix, "credRef": source.credRef},
            )
        return MaterializedSource(root=workspace, source=source, origin=f"s3://{bucket}/{prefix}" if prefix else f"s3://{bucket}")

    def _load_credentials(self, reference: str) -> Dict[str, str]:
        try:
            credentials = self.registry.get(reference)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Credential {reference} not found") from exc
        return {key: str(value) for key, value in credentials.items()}

    def _workspace(self, job_id: str, index: int, label: str) -> Path:
        workspace = self.settings.ingestion_workspace_dir / job_id / f"{index:02d}_{label}"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace


class SharePointSourceConnector(BaseSourceConnector):
    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        try:
            from office365.runtime.auth.client_credential import ClientCredential  # type: ignore
            from office365.sharepoint.client_context import ClientContext  # type: ignore
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SharePoint ingestion requires Office365-REST-Python-Client; install optional dependency",
            ) from exc

        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SharePoint source requires credRef")
        credentials = self._load_credentials(source.credRef)
        site_url = credentials.get("site_url")
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        if not (site_url and client_id and client_secret):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="SharePoint credential must include site_url, client_id, and client_secret",
            )
        folder = source.path or credentials.get("folder")
        if not folder:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SharePoint source requires folder path")
        workspace = self.settings.ingestion_workspace_dir / job_id / f"{index:02d}_sharepoint"
        workspace.mkdir(parents=True, exist_ok=True)

        ctx = ClientContext(site_url).with_credentials(ClientCredential(client_id, client_secret))
        try:
            self._download_folder(ctx, folder, workspace)
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.exception("Failed to download SharePoint folder", extra={"folder": folder})
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to download SharePoint folder {folder}: {exc}",
            ) from exc
        return MaterializedSource(root=workspace, source=source, origin=f"sharepoint:{folder}")

    def _load_credentials(self, reference: str) -> Dict[str, str]:
        try:
            credentials = self.registry.get(reference)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Credential {reference} not found") from exc
        return {key: str(value) for key, value in credentials.items()}

    def _download_folder(self, ctx, folder_url: str, destination: Path) -> None:
        folder = ctx.web.get_folder_by_server_relative_url(folder_url)
        ctx.load(folder)
        ctx.execute_query()

        files = folder.files
        ctx.load(files)
        ctx.execute_query()
        for item in files:
            local_path = destination / item.name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as handle:
                item.download(handle).execute_query()
            self.logger.info("Downloaded SharePoint file", extra={"path": item.serverRelativeUrl})

        subfolders = folder.folders
        ctx.load(subfolders)
        ctx.execute_query()
        for subfolder in subfolders:
            sub_dest = destination / subfolder.name
            sub_dest.mkdir(parents=True, exist_ok=True)
            self._download_folder(ctx, subfolder.serverRelativeUrl, sub_dest)


def build_connector(source_type: str, settings: Settings, registry: CredentialRegistry, logger: logging.Logger) -> BaseSourceConnector:
    lowered = source_type.lower()
    if lowered == "local":
        return LocalSourceConnector(settings, registry, logger)
    if lowered == "s3":
        return S3SourceConnector(settings, registry, logger)
    if lowered == "sharepoint":
        return SharePointSourceConnector(settings, registry, logger)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Source type '{source_type}' is not supported")
