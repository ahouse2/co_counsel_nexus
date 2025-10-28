from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from fastapi import HTTPException, status

from ..config import Settings
from ..models.api import IngestionSource
from ..utils.credentials import CredentialRegistry

import httpx


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


class OneDriveSourceConnector(BaseSourceConnector):
    _TOKEN_SCOPE = "https://graph.microsoft.com/.default"
    _GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
    _MAX_RETRIES = 3

    def __init__(
        self,
        settings: Settings,
        registry: CredentialRegistry,
        logger: logging.Logger,
        *,
        client_timeout: float = 30.0,
    ) -> None:
        super().__init__(settings, registry, logger)
        self._client_timeout = client_timeout
        self._sleep = time.sleep

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OneDrive source requires credRef")

        credentials = self._load_credentials(source.credRef)
        tenant_id = credentials.get("tenant_id")
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        drive_id = credentials.get("drive_id")
        folder = source.path or credentials.get("folder", "")

        missing_fields = [
            key
            for key, value in {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "client_secret": client_secret,
                "drive_id": drive_id,
            }.items()
            if not value
        ]
        if missing_fields:
            detail = ", ".join(sorted(missing_fields))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"OneDrive credential missing required fields: {detail}",
            )

        token = self._acquire_token(tenant_id, client_id, client_secret)  # type: ignore[arg-type]
        headers = {"Authorization": f"Bearer {token}"}
        workspace = self._workspace(job_id, index)
        folder_path = folder.strip("/")

        with httpx.Client(timeout=self._client_timeout) as client:
            base_item = self._resolve_base_item(client, drive_id, folder_path, headers)
            files_downloaded = self._download_tree(client, drive_id, base_item, workspace, headers)

        if not files_downloaded:
            self.logger.warning(
                "OneDrive source produced no files",
                extra={"drive_id": drive_id, "folder": folder_path or "<root>", "credRef": source.credRef},
            )

        origin_suffix = folder_path if folder_path else "root"
        return MaterializedSource(root=workspace, source=source, origin=f"onedrive:{drive_id}/{origin_suffix}")

    def _workspace(self, job_id: str, index: int) -> Path:
        workspace = self.settings.ingestion_workspace_dir / job_id / f"{index:02d}_onedrive"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _load_credentials(self, reference: str) -> Dict[str, str]:
        try:
            credentials = self.registry.get(reference)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Credential {reference} not found") from exc
        return {key: str(value) for key, value in credentials.items()}

    def _acquire_token(self, tenant_id: str, client_id: str, client_secret: str) -> str:
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": self._TOKEN_SCOPE,
        }
        with httpx.Client(timeout=self._client_timeout) as client:
            response = client.post(url, data=data)
        if response.status_code != status.HTTP_200_OK:
            detail = response.text or "unable to obtain token"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OneDrive token request failed ({response.status_code}): {detail}",
            )
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OneDrive token response missing access_token",
            )
        return str(token)

    def _resolve_base_item(
        self,
        client: httpx.Client,
        drive_id: str,
        folder_path: str,
        headers: Dict[str, str],
    ) -> Dict[str, str]:
        if folder_path:
            url = f"{self._GRAPH_ROOT}/drives/{drive_id}/root:/{folder_path}"
        else:
            url = f"{self._GRAPH_ROOT}/drives/{drive_id}/root"
        response = self._request(client.get, url, headers=headers)
        payload = response.json()
        item_id = payload.get("id")
        if not item_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OneDrive folder resolution failed: missing id",
            )
        name = payload.get("name") or (folder_path.split("/")[-1] if folder_path else "root")
        return {"id": str(item_id), "name": str(name)}

    def _download_tree(
        self,
        client: httpx.Client,
        drive_id: str,
        base_item: Dict[str, str],
        workspace: Path,
        headers: Dict[str, str],
    ) -> bool:
        queue: list[Tuple[str, Path]] = [(base_item["id"], Path(""))]
        files_downloaded = False

        while queue:
            item_id, relative_path = queue.pop(0)
            children_url = f"{self._GRAPH_ROOT}/drives/{drive_id}/items/{item_id}/children"
            next_url: str | None = children_url
            while next_url:
                response = self._request(client.get, next_url, headers=headers)
                payload = response.json()
                for child in payload.get("value", []):
                    name = child.get("name")
                    child_id = child.get("id")
                    if not name or not child_id:
                        continue
                    if child.get("folder") is not None:
                        queue.append((str(child_id), relative_path / name))
                        continue
                    if child.get("file") is None:
                        continue
                    destination = workspace / relative_path / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    download_url = f"{self._GRAPH_ROOT}/drives/{drive_id}/items/{child_id}/content"
                    download_response = self._request(client.get, download_url, headers=headers)
                    destination.write_bytes(download_response.content)
                    files_downloaded = True
                    self.logger.info(
                        "Downloaded OneDrive file",
                        extra={
                            "drive_id": drive_id,
                            "item_id": child_id,
                            "path": str(destination),
                        },
                    )
                next_url = payload.get("@odata.nextLink")
        return files_downloaded

    def _request(
        self,
        method,
        url: str,
        *,
        headers: Dict[str, str] | None = None,
    ) -> httpx.Response:
        last_response: httpx.Response | None = None
        for attempt in range(self._MAX_RETRIES):
            response = method(url, headers=headers, follow_redirects=True)
            status_code = response.status_code
            if status_code < 400:
                return response
            if status_code in (429, 500, 502, 503, 504) and attempt < self._MAX_RETRIES - 1:
                delay = 0.25 * (2**attempt)
                self.logger.warning(
                    "Retrying OneDrive request",
                    extra={"url": url, "status_code": status_code, "attempt": attempt + 1},
                )
                self._sleep(delay)
                continue
            last_response = response
            break
        assert last_response is not None
        detail = last_response.text or f"HTTP {last_response.status_code}"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OneDrive request to {url} failed: {detail}",
        )


def build_connector(source_type: str, settings: Settings, registry: CredentialRegistry, logger: logging.Logger) -> BaseSourceConnector:
    lowered = source_type.lower()
    if lowered == "local":
        return LocalSourceConnector(settings, registry, logger)
    if lowered == "s3":
        return S3SourceConnector(settings, registry, logger)
    if lowered == "sharepoint":
        return SharePointSourceConnector(settings, registry, logger)
    if lowered == "onedrive":
        return OneDriveSourceConnector(settings, registry, logger)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Source type '{source_type}' is not supported")
