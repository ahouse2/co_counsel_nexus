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
    timeline_path: Path = Field(default=Path("storage/timeline.jsonl"))
    job_store_dir: Path = Field(default=Path("storage/jobs"))
    document_store_dir: Path = Field(default=Path("storage/documents"))
    ingestion_workspace_dir: Path = Field(default=Path("storage/workspaces"))
    agent_threads_dir: Path = Field(default=Path("storage/agent_threads"))
    credentials_registry_path: Path | None = Field(default=None)

    qdrant_collection: str = Field(default="cocounsel_documents")
    qdrant_vector_size: int = Field(default=128)
    qdrant_distance: Literal["Cosine", "Dot", "Euclid"] = Field(default="Cosine")

    ingestion_chunk_size: int = Field(default=400)
    ingestion_chunk_overlap: int = Field(default=60)

    retrieval_max_search_window: int = Field(default=60)
    retrieval_graph_hop_window: int = Field(default=12)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def prepare_directories(self) -> None:
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        self.forensics_dir.mkdir(parents=True, exist_ok=True)
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

