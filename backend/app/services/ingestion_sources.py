from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, Iterator, List
from urllib.parse import quote, urlparse
from typing import Any, Callable, Coroutine, Dict, List, Tuple
from urllib.parse import urljoin

from fastapi import HTTPException, status

from ..config import Settings
from ..models.api import IngestionSource
from ..utils.credentials import CredentialRegistry

import httpx


def _normalise_url_path(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path or "/"


@dataclass
class MaterializedSource:
    root: Path
    source: IngestionSource
    origin: str | None = None


class DigestCache:
    def __init__(self, base_dir: Path, *, suffix: str = ".json") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.suffix = suffix

    def path_for(self, digest: str) -> Path:
        return self.base_dir / f"{digest}{self.suffix}"

    def exists(self, digest: str) -> bool:
        return self.path_for(digest).exists()

    def store(self, digest: str, payload: bytes) -> Path:
        path = self.path_for(digest)
        if path.exists():
            return path
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_bytes(payload)
        tmp_path.replace(path)
        return path

    def copy(self, digest: str, destination: Path) -> Path:
        source = self.path_for(digest)
        if not source.exists():
            raise FileNotFoundError(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_PATTERN.sub("-", value.lower()).strip("-")
    return slug or "document"


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
            credentials = self.registry.get(reference)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Credential {reference} not found") from exc
        return {key: str(value) for key, value in credentials.items()}

    def _workspace(self, job_id: str, index: int, label: str) -> Path:
        workspace = self.settings.ingestion_workspace_dir / job_id / f"{index:02d}_{label}"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace


class CourtListenerSourceConnector(BaseSourceConnector):
    _DEFAULT_ENDPOINT = "https://www.courtlistener.com/api/rest/v3/opinions/"
    _MAX_PAGE_SIZE = 100
    _MAX_RETRIES = 3
    _BACKOFF_BASE = 0.5
    _RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        settings: Settings,
        registry: CredentialRegistry,
        logger: logging.Logger,
        *,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
        cache: DigestCache | None = None,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(settings, registry, logger)
        cache_dir = self.settings.ingestion_workspace_dir / "_cache" / "courtlistener"
        self._cache = cache or DigestCache(cache_dir)
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=timeout))
        self._sleep: Callable[[float], Coroutine[Any, Any, None]] = asyncio.sleep

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CourtListener source requires credRef")
        credentials = self._load_credentials(source.credRef)
        query = (source.path or credentials.get("query") or "").strip()
        if not query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CourtListener source requires a query via path or credential",
            )
        endpoint = credentials.get("endpoint") or self._DEFAULT_ENDPOINT
        token = credentials.get("token") or credentials.get("api_key")
        page_size = self._clamp_int(credentials.get("page_size", 25), 1, self._MAX_PAGE_SIZE)
        max_pages = self._clamp_int(credentials.get("max_pages", 1), 1, 10)
        workspace = self._workspace(job_id, index)
        coroutine = self._materialize_async(endpoint, query, token, page_size, max_pages, workspace)
        self._run_async(coroutine)
        origin = f"courtlistener:{query}"
        return MaterializedSource(root=workspace, source=source, origin=origin)

    async def _materialize_async(
        self,
        endpoint: str,
        query: str,
        token: str | None,
        page_size: int,
        max_pages: int,
        workspace: Path,
    ) -> None:
        headers = self._headers(token)
        params = {"q": query, "page_size": page_size}
        next_url = endpoint
        page = 0
        found = 0
        async with self._client_factory() as client:
            while next_url and page < max_pages:
                response = await self._request(client, next_url, headers=headers, params=params if page == 0 else None)
                payload = response.json()
                results = payload.get("results") or []
                if isinstance(results, list):
                    for rank, item in enumerate(results):
                        await self._materialize_opinion(client, endpoint, query, item, workspace, headers, page, rank)
                        found += 1
                next_url = payload.get("next")
                page += 1
        if found == 0:
            self.logger.warning(
                "CourtListener query yielded no opinions",
                extra={"query": query, "endpoint": endpoint},
            )

    async def _materialize_opinion(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        query: str,
        item: Dict[str, object],
        workspace: Path,
        headers: Dict[str, str],
        page: int,
        rank: int,
    ) -> None:
        identifier = item.get("id") or item.get("cluster") or item.get("absolute_url")
        slug_source = (
            item.get("case_name")
            or item.get("caption")
            or item.get("docket_number")
            or f"opinion-{page}-{rank}"
        )
        slug = _slugify(str(slug_source))
        digest_hint = str(item.get("sha1") or item.get("sha256") or "")
        if digest_hint and self._cache.exists(digest_hint):
            destination = workspace / f"{slug}-{digest_hint[:12]}.json"
            self._cache.copy(digest_hint, destination)
            self.logger.info(
                "Reused cached CourtListener opinion",
                extra={"slug": slug, "digest": digest_hint, "destination": str(destination)},
            )
            return
        text = item.get("plain_text") or item.get("html_with_citations") or ""
        if not text:
            resource_uri = item.get("resource_uri")
            if resource_uri:
                detail_url = urljoin(endpoint, str(resource_uri))
                detail_response = await self._request(client, detail_url, headers=headers)
                detail_payload = detail_response.json()
                text = detail_payload.get("plain_text") or detail_payload.get("html_with_citations") or ""
        text_str = str(text or "")
        if not text_str:
            self.logger.debug(
                "Skipping CourtListener result lacking text",
                extra={"slug": slug, "identifier": identifier},
            )
            return
        digest_value = digest_hint or sha256(text_str.encode("utf-8")).hexdigest()
        destination = workspace / f"{slug}-{digest_value[:12]}.json"
        payload = {
            "id": identifier,
            "case_name": item.get("case_name"),
            "docket_number": item.get("docket_number"),
            "court": item.get("court"),
            "date_filed": item.get("date_filed"),
            "absolute_url": item.get("absolute_url"),
            "resource_uri": item.get("resource_uri"),
            "citations": item.get("citations"),
            "query": query,
            "text": text_str,
        }
        cache_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        cache_path = self._cache.store(digest_value, cache_bytes)
        shutil.copy2(cache_path, destination)
        self.logger.info(
            "Materialised CourtListener opinion",
            extra={"slug": slug, "digest": digest_value, "destination": str(destination)},
        )

    def _headers(self, token: str | None) -> Dict[str, str]:
        headers = {
            "User-Agent": "CoCounsel-Ingestion/1.0",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Token {token}"
        return headers

    async def _request(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        headers: Dict[str, str] | None = None,
        params: Dict[str, object] | None = None,
    ) -> httpx.Response:
        last_response: httpx.Response | None = None
        for attempt in range(self._MAX_RETRIES):
            response = await client.get(url, headers=headers, params=params)
            status_code = response.status_code
            if status_code < 400:
                return response
            if status_code in self._RETRYABLE_STATUS and attempt < self._MAX_RETRIES - 1:
                delay = self._BACKOFF_BASE * (2**attempt)
                self.logger.warning(
                    "Retrying CourtListener request",
                    extra={"url": url, "status_code": status_code, "attempt": attempt + 1},
                )
                await self._sleep(delay)
                continue
            last_response = response
            break
        assert last_response is not None
        detail = last_response.text or f"HTTP {last_response.status_code}"
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"CourtListener request to {url} failed: {detail}",
        )

    def _workspace(self, job_id: str, index: int) -> Path:
        workspace = self.settings.ingestion_workspace_dir / job_id / f"{index:02d}_courtlistener"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _load_credentials(self, reference: str) -> Dict[str, str]:
        try:
            credentials = self.registry.get(reference)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Credential {reference} not found") from exc
        return {key: str(value) for key, value in credentials.items()}

    @staticmethod
    def _clamp_int(raw: object, minimum: int, maximum: int) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return minimum
        return max(minimum, min(maximum, value))

    @staticmethod
    def _run_async(coro: Coroutine[Any, Any, None]) -> None:
        try:
            asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()


class WebSearchSourceConnector(BaseSourceConnector):
    _DEFAULT_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
    _MAX_PAGE_SIZE = 20

    def __init__(
        self,
        settings: Settings,
        registry: CredentialRegistry,
        logger: logging.Logger,
        *,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
        cache: DigestCache | None = None,
        timeout: float = 20.0,
    ) -> None:
        super().__init__(settings, registry, logger)
        cache_dir = self.settings.ingestion_workspace_dir / "_cache" / "websearch"
        self._cache = cache or DigestCache(cache_dir)
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=timeout))

    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        if not source.credRef:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Web search source requires credRef")
        credentials = self._load_credentials(source.credRef)
        query = (source.path or credentials.get("query") or "").strip()
        if not query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Web search source requires a query via path or credential",
            )
        api_key = credentials.get("api_key") or credentials.get("token")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Web search credential must provide api_key",
            )
        endpoint = credentials.get("endpoint") or self._DEFAULT_ENDPOINT
        page_size = self._clamp_int(credentials.get("page_size", 10), 1, self._MAX_PAGE_SIZE)
        max_pages = self._clamp_int(credentials.get("max_pages", 1), 1, 5)
        workspace = self._workspace(job_id, index)
        coroutine = self._materialize_async(endpoint, query, api_key, page_size, max_pages, workspace)
        CourtListenerSourceConnector._run_async(coroutine)
        origin = f"websearch:{query}"
        return MaterializedSource(root=workspace, source=source, origin=origin)

    async def _materialize_async(
        self,
        endpoint: str,
        query: str,
        api_key: str,
        page_size: int,
        max_pages: int,
        workspace: Path,
    ) -> None:
        headers = {
            "User-Agent": "CoCounsel-Ingestion/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        page = 0
        total = 0
        async with self._client_factory() as client:
            while page < max_pages:
                params = {"q": query, "count": page_size, "offset": page * page_size}
                response = await client.get(endpoint, headers=headers, params=params)
                if response.status_code >= 400:
                    detail = response.text or f"HTTP {response.status_code}"
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Web search request failed: {detail}",
                    )
                payload = response.json()
                results = self._extract_results(payload)
                if not results:
                    break
                for rank, item in enumerate(results):
                    await self._materialize_result(query, item, workspace, page, rank, page_size)
                    total += 1
                page += 1
        if total == 0:
            self.logger.warning(
                "Web search produced no results",
                extra={"query": query, "endpoint": endpoint},
            )

    async def _materialize_result(
        self,
        query: str,
        item: Dict[str, object],
        workspace: Path,
        page: int,
        rank: int,
        page_size: int,
    ) -> None:
        title = str(item.get("title") or item.get("name") or f"result-{page}-{rank}")
        url = str(item.get("url") or item.get("link") or "")
        snippet = str(item.get("snippet") or item.get("description") or "")
        content = str(item.get("content") or snippet or "")
        slug = _slugify(title)
        digest_seed = url or f"{title}:{snippet}"
        digest = sha256(digest_seed.encode("utf-8")).hexdigest()
        destination = workspace / f"{slug}-{digest[:12]}.json"
        if self._cache.exists(digest):
            self._cache.copy(digest, destination)
            self.logger.info(
                "Reused cached web search result",
                extra={"slug": slug, "digest": digest, "destination": str(destination)},
            )
            return
        payload = {
            "title": title,
            "url": url,
            "snippet": snippet,
            "content": content,
            "query": query,
            "rank": rank + 1 + page * page_size,
        }
        cache_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        cache_path = self._cache.store(digest, cache_bytes)
        shutil.copy2(cache_path, destination)
        self.logger.info(
            "Materialised web search result",
            extra={"slug": slug, "digest": digest, "destination": str(destination)},
        )

    def _extract_results(self, payload: Dict[str, object]) -> List[Dict[str, object]]:
        if "results" in payload and isinstance(payload["results"], list):
            return [dict(item) for item in payload["results"]]
        web_section = payload.get("web")
        if isinstance(web_section, dict) and isinstance(web_section.get("results"), list):
            return [dict(item) for item in web_section["results"]]
        return []

    def _workspace(self, job_id: str, index: int) -> Path:
        workspace = self.settings.ingestion_workspace_dir / job_id / f"{index:02d}_websearch"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def _load_credentials(self, reference: str) -> Dict[str, str]:
        try:
            credentials = self.registry.get(reference)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Credential {reference} not found") from exc
        return {key: str(value) for key, value in credentials.items()}

    @staticmethod
    def _clamp_int(raw: object, minimum: int, maximum: int) -> int:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return minimum
        return max(minimum, min(maximum, value))


class SharePointSourceConnector(BaseSourceConnector):
    def materialize(self, job_id: str, index: int, source: IngestionSource) -> MaterializedSource:
        try:
            from office365.runtime.auth.client_credential import ClientCredential  # type: ignore
            from office365.sharepoint.client_context import ClientContext  # type: ignore
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
    if lowered in {"courtlistener", "court_listener"}:
        return CourtListenerSourceConnector(settings, registry, logger)
    if lowered in {"websearch", "web_search", "web"}:
        return WebSearchSourceConnector(settings, registry, logger)
    if lowered == "sharepoint":
        return SharePointSourceConnector(settings, registry, logger)
    if lowered == "onedrive":
        return OneDriveSourceConnector(settings, registry, logger)
    if lowered == "web":
        return WebSourceConnector(settings, registry, logger)
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Source type '{source_type}' is not supported")
