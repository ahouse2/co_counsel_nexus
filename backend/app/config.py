from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Literal, Optional

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

    vector_backend: Literal["qdrant", "chroma", "memory"] = Field(default="qdrant")
    vector_dir: Path = Field(default=Path("storage/vector"))
    ingestion_chroma_dir: Path = Field(default=Path("storage/chroma"))
    chroma_collection: str = Field(default="cocounsel_documents")
    ingestion_llama_cache_dir: Path = Field(default=Path("storage/llama_cache"))
    forensics_dir: Path = Field(default=Path("storage/forensics"))
    forensics_chain_path: Path = Field(default=Path("storage/forensics_chain/ledger.jsonl"))
    timeline_path: Path = Field(default=Path("storage/timeline.jsonl"))
    job_store_dir: Path = Field(default=Path("storage/jobs"))
    document_store_dir: Path = Field(default=Path("storage/documents"))
    ingestion_workspace_dir: Path = Field(default=Path("storage/workspaces"))
    agent_threads_dir: Path = Field(default=Path("storage/agent_threads"))
    agent_retry_attempts: int = Field(default=3, ge=1)
    agent_retry_backoff_ms: int = Field(default=0, ge=0)
    agent_circuit_threshold: int = Field(default=4, ge=1)
    agent_circuit_window_seconds: float = Field(default=30.0, ge=1.0)
    agent_circuit_cooldown_seconds: float = Field(default=45.0, ge=1.0)
    credentials_registry_path: Path | None = Field(default=None)
    manifest_encryption_key_path: Path = Field(default=Path("storage/manifest.key"))
    manifest_retention_days: int = Field(default=30)
    audit_log_path: Path = Field(default=Path("storage/audit.log"))
    billing_usage_path: Path = Field(default=Path("storage/billing/usage.json"))

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
    security_audience_billing: str = Field(default="co-counsel.billing")
    security_audience_dev_agent: str = Field(default="co-counsel.dev-agent")

    dev_agent_validation_commands: tuple[tuple[str, ...], ...] = Field(
        default=(
            (
                "python",
                "-m",
                "tools.qa.quality_gate",
                "--threshold",
                "85",
                "--",
                "backend/tests",
                "-q",
            ),
            ("ruff", "check", "backend"),
        )
    )
    dev_agent_required_scopes: tuple[str, ...] = Field(default=("dev-agent:admin",))
    dev_agent_admin_roles: tuple[str, ...] = Field(default=("PlatformEngineer", "AutomationService"))
    telemetry_enabled: bool = Field(default=False)
    telemetry_service_name: str = Field(default="cocounsel-backend")
    telemetry_environment: str = Field(default="local")
    telemetry_otlp_endpoint: str | None = Field(default=None)
    telemetry_otlp_insecure: bool = Field(default=True)
    telemetry_metrics_interval: float = Field(default=30.0)
    telemetry_console_fallback: bool = Field(default=True)

    billing_default_plan: str = Field(default="community")
    billing_plan_overrides: Dict[str, str] = Field(default_factory=dict)
    billing_support_overrides: Dict[str, str] = Field(default_factory=dict)
    billing_health_soft_threshold: float = Field(default=0.8)
    billing_health_hard_threshold: float = Field(default=0.95)

    voice_enabled: bool = Field(default=True)
    voice_sessions_dir: Path = Field(default=Path("storage/voice/sessions"))
    voice_cache_dir: Path = Field(default=Path("storage/voice/cache"))
    voice_whisper_model: str = Field(default="medium.en")
    voice_whisper_compute_type: Literal["int8_float16", "float16", "float32"] = Field(
        default="int8_float16"
    )
    voice_device_preference: Literal["auto", "cuda", "cpu"] = Field(default="auto")
    voice_tts_model: str = Field(default="tts_models/en/vctk/vits")
    voice_sentiment_model: str = Field(
        default="distilbert-base-uncased-finetuned-sst-2-english"
    )
    voice_sample_rate: int = Field(default=22050, ge=8000, le=48000)
    voice_personas: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {
            "aurora": {
                "label": "Aurora",
                "description": "Warm, empathetic cadence suitable for sensitive updates.",
                "speaker_id": "p273",
            },
            "atlas": {
                "label": "Atlas",
                "description": "Calm, authoritative delivery for compliance briefings.",
                "speaker_id": "p270",
            },
            "lyra": {
                "label": "Lyra",
                "description": "Crisp, energetic tone tuned for investigative stand-ups.",
                "speaker_id": "p268",
            },
        }
    )

    qdrant_collection: str = Field(default="cocounsel_documents")
    qdrant_vector_size: int = Field(default=384)
    qdrant_distance: Literal["Cosine", "Dot", "Euclid"] = Field(default="Cosine")

    ingestion_cost_mode: Literal["community", "pro", "enterprise"] = Field(default="community")
    ingestion_chunk_size: int = Field(default=400)
    ingestion_chunk_overlap: int = Field(default=60)
    ingestion_max_triplets_per_chunk: int = Field(default=12)
    ingestion_graph_batch_size: int = Field(default=64)
    ingestion_hf_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    ingestion_hf_dimensions: Optional[int] = Field(default=None)
    ingestion_hf_device: Optional[str] = Field(default=None)
    ingestion_hf_cache_dir: Optional[Path] = Field(default=None)
    ingestion_openai_model: str = Field(default="text-embedding-3-small")
    ingestion_openai_dimensions: Optional[int] = Field(default=None)
    ingestion_openai_api_key: Optional[str] = Field(default=None)
    ingestion_openai_base: Optional[str] = Field(default=None)
    ingestion_enterprise_embedding_model: str = Field(default="text-embedding-3-large")
    ingestion_enterprise_embedding_dimensions: Optional[int] = Field(default=None)
    ingestion_enterprise_embedding_api_key: Optional[str] = Field(default=None)
    ingestion_azure_openai_endpoint: Optional[str] = Field(default=None)
    ingestion_azure_openai_deployment: Optional[str] = Field(default=None)
    ingestion_azure_openai_api_version: Optional[str] = Field(default="2024-05-01-preview")
    ingestion_tesseract_languages: str = Field(default="eng")
    ingestion_tesseract_path: Optional[Path] = Field(default=None)
    ingestion_vision_endpoint: Optional[str] = Field(default=None)
    ingestion_vision_model: Optional[str] = Field(default=None)
    ingestion_vision_api_key: Optional[str] = Field(default=None)
    ingestion_queue_maxsize: int = Field(default=32)
    ingestion_worker_concurrency: int = Field(default=1)

    retrieval_max_search_window: int = Field(default=60)
    retrieval_graph_hop_window: int = Field(default=12)
    retrieval_cross_encoder_model: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def prepare_directories(self) -> None:
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        self.ingestion_chroma_dir.mkdir(parents=True, exist_ok=True)
        self.ingestion_llama_cache_dir.mkdir(parents=True, exist_ok=True)
        if self.ingestion_hf_cache_dir:
            self.ingestion_hf_cache_dir.mkdir(parents=True, exist_ok=True)
        self.forensics_dir.mkdir(parents=True, exist_ok=True)
        self.forensics_chain_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeline_path.parent.mkdir(parents=True, exist_ok=True)
        self.job_store_dir.mkdir(parents=True, exist_ok=True)
        self.document_store_dir.mkdir(parents=True, exist_ok=True)
        self.ingestion_workspace_dir.mkdir(parents=True, exist_ok=True)
        self.agent_threads_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.billing_usage_path.parent.mkdir(parents=True, exist_ok=True)
        self.voice_sessions_dir.mkdir(parents=True, exist_ok=True)
        self.voice_cache_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[arg-type]
    settings.prepare_directories()
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()

