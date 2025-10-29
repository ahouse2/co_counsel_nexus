from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Co-Counsel API."""

    app_name: str = "Co-Counsel API"
    app_version: str = "0.1.0"

    neo4j_uri: str = Field(default="neo4j://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")

    qdrant_url: Optional[str] = Field(default=None)
    qdrant_path: Optional[str] = Field(default=None)

    vector_dir: Path = Field(default=Path("storage/vector"))
    forensics_dir: Path = Field(default=Path("storage/forensics"))
    forensics_chain_path: Path = Field(default=Path("storage/forensics_chain/ledger.jsonl"))
    timeline_path: Path = Field(default=Path("storage/timeline.jsonl"))
    job_store_dir: Path = Field(default=Path("storage/jobs"))
    document_store_dir: Path = Field(default=Path("storage/documents"))
    ingestion_workspace_dir: Path = Field(default=Path("storage/workspaces"))
    agent_threads_dir: Path = Field(default=Path("storage/agent_threads"))
    credentials_registry_path: Path | None = Field(default=None)

    privilege_classifier_threshold: float = Field(default=0.68)

    security_mtls_ca_path: Path | None = Field(default=None)
    security_mtls_registry_path: Path | None = Field(default=None)
    security_mtls_header: str = Field(default="x-client-cert")
    security_mtls_optional_paths: tuple[str, ...] = Field(default=("/health",))
    security_mtls_clock_skew: int = Field(default=60)

    security_oauth_jwks_path: Path | None = Field(default=None)
    security_token_issuer: str | None = Field(default=None)
    security_token_leeway: int = Field(default=60)

    security_audience_ingest: str = Field(default="co-counsel.ingest")
    security_audience_query: str = Field(default="co-counsel.query")
    security_audience_timeline: str = Field(default="co-counsel.timeline")
    security_audience_graph: str = Field(default="co-counsel.graph")
    security_audience_forensics: str = Field(default="co-counsel.forensics")
    security_audience_agents: str = Field(default="co-counsel.agents")
    telemetry_enabled: bool = Field(default=False)
    telemetry_service_name: str = Field(default="cocounsel-backend")
    telemetry_environment: str = Field(default="local")
    telemetry_otlp_endpoint: str | None = Field(default=None)
    telemetry_otlp_insecure: bool = Field(default=True)
    telemetry_metrics_interval: float = Field(default=30.0)
    telemetry_console_fallback: bool = Field(default=True)

    qdrant_collection: str = Field(default="cocounsel_documents")
    qdrant_vector_size: int = Field(default=128)
    qdrant_distance: Literal["Cosine", "Dot", "Euclid"] = Field(default="Cosine")

    ingestion_chunk_size: int = Field(default=400)
    ingestion_chunk_overlap: int = Field(default=60)
    ingestion_queue_maxsize: int = Field(default=32)
    ingestion_worker_concurrency: int = Field(default=1)

    retrieval_max_search_window: int = Field(default=60)
    retrieval_graph_hop_window: int = Field(default=12)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def prepare_directories(self) -> None:
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        self.forensics_dir.mkdir(parents=True, exist_ok=True)
        self.forensics_chain_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeline_path.parent.mkdir(parents=True, exist_ok=True)
        self.job_store_dir.mkdir(parents=True, exist_ok=True)
        self.document_store_dir.mkdir(parents=True, exist_ok=True)
        self.ingestion_workspace_dir.mkdir(parents=True, exist_ok=True)
        self.agent_threads_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[arg-type]
    settings.prepare_directories()
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()

