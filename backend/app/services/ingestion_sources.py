from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List
from urllib.parse import quote, urlparse

from fastapi import HTTPException, status

from ..config import Settings
from ..models.api import IngestionSource
from ..utils.credentials import CredentialRegistry


def _normalise_url_path(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path or "/"


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

    def preflight(self, source: IngestionSource) -> None:
        """Perform lightweight validation prior to enqueueing."""
        return None

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


class LocalSourceConnector(BaseSourceConnector):
    def preflight(self, source: IngestionSource) -> None:
        self._resolve_root(source)

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        target = self._resolve_root(source)
        self.logger.info("Materialised local source", extra={"path": str(target)})
        return MaterializedSource(root=target, source=source, origin=str(target))

    def _resolve_root(self, source: IngestionSource) -> Path:
        if not source.path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Local source requires a path")
        target = Path(source.path).expanduser().resolve()
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source path {target} not found")
        if not target.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Local source must reference a directory")
        return target


class S3SourceConnector(BaseSourceConnector):
    def preflight(self, source: IngestionSource) -> None:
        self._ensure_boto3()
        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="S3 source requires credRef")
        self._load_credentials(source.credRef)

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        boto3 = self._ensure_boto3()

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

    def _ensure_boto3(self):
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="S3 ingestion requires boto3; install optional dependency",
            ) from exc
        return boto3


class SharePointSourceConnector(BaseSourceConnector):
    def preflight(self, source: IngestionSource) -> None:
        self._ensure_sdk()
        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SharePoint source requires credRef")
        credentials = self._load_credentials(source.credRef)
        folder = source.path or credentials.get("folder")
        if not folder:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SharePoint source requires folder path")

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        ClientCredential, ClientContext = self._ensure_sdk()

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

    def _ensure_sdk(self):
        try:
            from office365.runtime.auth.client_credential import ClientCredential  # type: ignore
            from office365.sharepoint.client_context import ClientContext  # type: ignore
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SharePoint ingestion requires Office365-REST-Python-Client; install optional dependency",
            ) from exc
        return ClientCredential, ClientContext

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
    GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]

    def preflight(self, source: IngestionSource) -> None:
        self._ensure_dependencies()
        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OneDrive source requires credRef")
        credentials = self._load_credentials(source.credRef)
        required = {"tenant_id", "client_id", "client_secret", "drive_id"}
        missing = sorted(required - set(credentials))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"OneDrive credential missing fields: {', '.join(missing)}",
            )

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        httpx, msal = self._ensure_dependencies()

        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OneDrive source requires credRef")
        credentials = self._load_credentials(source.credRef)
        tenant_id = credentials.get("tenant_id")
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        drive_id = credentials.get("drive_id")
        if not (tenant_id and client_id and client_secret and drive_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="OneDrive credential must include tenant_id, client_id, client_secret, and drive_id",
            )

        folder = source.path or credentials.get("folder", "")
        workspace = self._workspace(job_id, index, "onedrive")

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(scopes=self.GRAPH_SCOPE)
        access_token = token_result.get("access_token")
        if not access_token:
            description = token_result.get("error_description") or token_result.get("error") or "unknown"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to acquire OneDrive token: {description}",
            )

        base_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}"
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

        with httpx.Client(timeout=60.0) as client:
            try:
                iterator = self._list_items(client, base_url, folder, headers, workspace)
                for item in iterator:
                    relative_path = workspace / item["relative"]
                    if item["is_folder"]:
                        relative_path.mkdir(parents=True, exist_ok=True)
                        continue
                    relative_path.parent.mkdir(parents=True, exist_ok=True)
                    download_url = item.get("download_url")
                    if not download_url:
                        self.logger.warning(
                            "Skipping OneDrive file without download URL",
                            extra={"item": item.get("name"), "path": folder},
                        )
                        continue
                    try:
                        response = client.get(download_url, headers=None)
                    except Exception as exc:  # pylint: disable=broad-except
                        self.logger.exception(
                            "Failed to download OneDrive file",
                            extra={"drive_id": drive_id, "name": item.get("name")},
                        )
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Unable to download OneDrive file {item.get('name')}",
                        ) from exc
                    if response.status_code >= 400:
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"OneDrive returned HTTP {response.status_code} for {item.get('name')}",
                        )
                    relative_path.write_bytes(response.content)
                    self.logger.info(
                        "Downloaded OneDrive file",
                        extra={"drive_id": drive_id, "name": item.get("name"), "path": str(relative_path)},
                    )
            except HTTPException:
                raise
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.exception("Failed to enumerate OneDrive items", extra={"folder": folder})
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Unable to enumerate OneDrive folder {folder or '/'}: {exc}",
                ) from exc

        origin = f"onedrive:{folder}" if folder else "onedrive:/"
        return MaterializedSource(root=workspace, source=source, origin=origin)

    def _ensure_dependencies(self):
        try:
            import httpx
            import msal  # type: ignore
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OneDrive ingestion requires msal and httpx; install optional dependency",
            ) from exc
        return httpx, msal

    def _list_items(
        self,
        client,
        base_url: str,
        folder: str,
        headers: Dict[str, str],
        workspace: Path,
    ) -> Iterator[Dict[str, object]]:
        stack: List[tuple[str, Path]] = []
        initial_path = folder.strip("/")
        initial_relative = Path(initial_path) if initial_path else Path()
        if initial_path:
            (workspace / initial_relative).mkdir(parents=True, exist_ok=True)
        stack.append((initial_path, initial_relative))
        while stack:
            current_path, relative = stack.pop()
            for entry in self._list_children(client, base_url, current_path, headers):
                name = entry.get("name") or "unnamed"
                child_relative = relative / name
                if entry.get("folder") is not None:
                    stack.append(((current_path + "/" + name).strip("/"), child_relative))
                    yield {
                        "is_folder": True,
                        "name": name,
                        "relative": child_relative,
                    }
                else:
                    yield {
                        "is_folder": False,
                        "name": name,
                        "relative": child_relative,
                        "download_url": entry.get("@microsoft.graph.downloadUrl"),
                    }

    def _list_children(
        self,
        client,
        base_url: str,
        folder: str,
        headers: Dict[str, str],
    ) -> Iterable[Dict[str, object]]:
        if folder:
            encoded = quote(folder, safe="/")
            url = f"{base_url}/root:/{encoded}:/children"
        else:
            url = f"{base_url}/root/children"
        while url:
            try:
                response = client.get(url, headers=headers)
            except Exception as exc:  # pylint: disable=broad-except
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Unable to request OneDrive path '{folder or '/'}': {exc}",
                ) from exc
            if response.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OneDrive folder '{folder}' not found")
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"OneDrive returned HTTP {response.status_code} for path '{folder or '/'}'",
                )
            payload = response.json()
            for entry in payload.get("value", []):
                yield entry
            url = payload.get("@odata.nextLink")


class WebSourceConnector(BaseSourceConnector):
    def preflight(self, source: IngestionSource) -> None:
        self._validate_url(source)
        self._ensure_httpx()

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        httpx = self._ensure_httpx()
        url = self._validate_url(source)

        workspace = self._workspace(job_id, index, "web")
        filename = self._build_filename(url)
        target = workspace / filename

        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.get(url)
            except httpx.RequestError as exc:  # type: ignore[attr-defined]
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch {url}: {exc}",
                ) from exc
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch {url}: HTTP {response.status_code}",
                )
            target.write_bytes(response.content)

        self.logger.info("Fetched web source", extra={"url": url, "path": str(target)})
        origin = f"web:{_normalise_url_path(url)}"
        return MaterializedSource(root=workspace, source=source, origin=origin)

    def _ensure_httpx(self):
        try:
            import httpx
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Web ingestion requires httpx optional dependency",
            ) from exc
        return httpx

    def _validate_url(self, source: IngestionSource) -> str:
        if not source.path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Web source requires a URL in path")
        url = source.path.strip()
        if not url.lower().startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Web source path must be a HTTP(S) URL",
            )
        return url

    def _build_filename(self, url: str) -> str:
        parsed = urlparse(url)
        name = Path(parsed.path).name or "index.html"
        if "." not in name:
            name = f"{name}.html"
        return name


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
    if lowered == "web":
        return WebSourceConnector(settings, registry, logger)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Source type '{source_type}' is not supported")
