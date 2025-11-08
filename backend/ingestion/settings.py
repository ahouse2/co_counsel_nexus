"""Runtime configuration helpers for the LlamaIndex ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:  # pragma: no cover - import used for typing only
    from backend.app.config import Settings  # pylint: disable=cyclic-import
else:  # pragma: no cover - fallback type when not type checking
    Settings = Any  # type: ignore


class IngestionCostMode(str, Enum):
    """Cost discipline tiers sourced from the TRD."""

    COMMUNITY = "community"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class EmbeddingProvider(str, Enum):
    """Embedding backends supported by the ingestion runtime."""

    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class OcrProvider(str, Enum):
    """OCR engines offered by the ingestion runtime."""

    TESSERACT = "tesseract"
    VISION = "vision"


class LlmProvider(str, Enum):
    """LLM backends supported by the ingestion runtime for text generation tasks."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


@dataclass(frozen=True)
class EmbeddingConfig:
    """Concrete embedding selection for a pipeline execution."""

    provider: EmbeddingProvider
    model: str
    dimensions: Optional[int]
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OcrConfig:
    """OCR backend selection and parameters."""

    provider: OcrProvider
    languages: str
    tessdata_path: Optional[Path] = None
    vision_endpoint: Optional[str] = None
    vision_model: Optional[str] = None
    api_key: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LlmConfig:
    """LLM backend selection and parameters for text generation."""

    provider: LlmProvider
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineTuning:
    """Chunking, batching and retry knobs for the pipeline."""

    chunk_size: int
    chunk_overlap: int
    max_triplets_per_chunk: int
    graph_batch_size: int


@dataclass(frozen=True)
class LlamaIndexRuntimeConfig:
    """Aggregate ingestion configuration for downstream orchestration."""

    cost_mode: IngestionCostMode
    embedding: EmbeddingConfig
    ocr: OcrConfig
    llm: LlmConfig # Added LLM configuration
    tuning: PipelineTuning
    workspace_dir: Path
    llama_cache_dir: Path
    chroma_persist_dir: Path
    vector_backend: str


class EmbeddingSecretEnvelope(BaseModel):
    """Secrets envelope for embeddings fetched from the credential registry."""

    api_key: Optional[str] = None
    endpoint: Optional[str] = None


def resolve_cost_mode(raw: str | IngestionCostMode) -> IngestionCostMode:
    if isinstance(raw, IngestionCostMode):
        return raw
    try:
        return IngestionCostMode(raw.lower())
    except ValueError as exc:  # pragma: no cover - defensive; validated upstream
        raise ValueError(f"Unsupported ingestion cost mode: {raw}") from exc


def build_embedding_config(settings: "Settings") -> EmbeddingConfig:
    """Resolve the embedding configuration for the active cost mode."""

    mode = resolve_cost_mode(settings.ingestion_cost_mode)
    if mode is IngestionCostMode.COMMUNITY:
        return EmbeddingConfig(
            provider=EmbeddingProvider.HUGGINGFACE,
            model=settings.ingestion_hf_model,
            dimensions=settings.ingestion_hf_dimensions or settings.qdrant_vector_size,
            extra={
                "device": settings.ingestion_hf_device,
                "cache_folder": str(settings.ingestion_hf_cache_dir) if settings.ingestion_hf_cache_dir else None,
            },
        )
    if mode is IngestionCostMode.PRO:
        return EmbeddingConfig(
            provider=EmbeddingProvider.OPENAI,
            model=settings.ingestion_openai_model,
            dimensions=settings.ingestion_openai_dimensions or settings.qdrant_vector_size,
            api_key=settings.ingestion_openai_api_key,
            api_base=settings.ingestion_openai_base,
        )
    return EmbeddingConfig(
        provider=EmbeddingProvider.AZURE_OPENAI
        if settings.ingestion_azure_openai_endpoint
        else EmbeddingProvider.OPENAI,
        model=settings.ingestion_enterprise_embedding_model,
        dimensions=settings.ingestion_enterprise_embedding_dimensions or settings.qdrant_vector_size,
        api_key=settings.ingestion_enterprise_embedding_api_key
        or settings.ingestion_openai_api_key,
        api_base=settings.ingestion_azure_openai_endpoint or settings.ingestion_openai_base,
        extra={
            "azure_deployment": settings.ingestion_azure_openai_deployment,
            "api_version": settings.ingestion_azure_openai_api_version,
        },
    )


def build_ocr_config(settings: "Settings") -> OcrConfig:
    mode = resolve_cost_mode(settings.ingestion_cost_mode)
    if mode is IngestionCostMode.COMMUNITY:
        return OcrConfig(
            provider=OcrProvider.TESSERACT,
            languages=settings.ingestion_tesseract_languages,
            tessdata_path=settings.ingestion_tesseract_path,
        )
    if mode is IngestionCostMode.PRO:
        return OcrConfig(
            provider=OcrProvider.TESSERACT,
            languages=settings.ingestion_tesseract_languages,
            tessdata_path=settings.ingestion_tesseract_path,
            extra={"vision_fallback": {
                "endpoint": settings.ingestion_vision_endpoint,
                "model": settings.ingestion_vision_model,
                "api_key": settings.ingestion_vision_api_key,
            }},
        )
    return OcrConfig(
        provider=OcrProvider.VISION,
        languages=settings.ingestion_tesseract_languages,
        tessdata_path=settings.ingestion_tesseract_path,
        vision_endpoint=settings.ingestion_vision_endpoint,
        vision_model=settings.ingestion_vision_model,
        api_key=settings.ingestion_vision_api_key,
    )


def build_llm_config(settings: "Settings") -> LlmConfig:
    mode = resolve_cost_mode(settings.ingestion_cost_mode)
    if mode is IngestionCostMode.COMMUNITY:
        return LlmConfig(
            provider=LlmProvider.OLLAMA, # Assuming Ollama for community tier
            model=settings.ingestion_ollama_model,
            api_base=settings.ingestion_ollama_base,
        )
    if mode is IngestionCostMode.PRO:
        return LlmConfig(
            provider=LlmProvider.OPENAI,
            model=settings.ingestion_openai_model,
            api_key=settings.ingestion_openai_api_key,
            api_base=settings.ingestion_openai_base,
        )
    return LlmConfig(
        provider=LlmProvider.AZURE_OPENAI
        if settings.ingestion_azure_openai_endpoint
        else LlmProvider.OPENAI,
        model=settings.ingestion_enterprise_llm_model,
        api_key=settings.ingestion_enterprise_llm_api_key
        or settings.ingestion_openai_api_key,
        api_base=settings.ingestion_azure_openai_endpoint or settings.ingestion_openai_base,
        extra={
            "azure_deployment": settings.ingestion_azure_openai_deployment,
            "api_version": settings.ingestion_azure_openai_api_version,
        },
    )


def build_pipeline_tuning(settings: "Settings") -> PipelineTuning:
    return PipelineTuning(
        chunk_size=settings.ingestion_chunk_size,
        chunk_overlap=settings.ingestion_chunk_overlap,
        max_triplets_per_chunk=settings.ingestion_max_triplets_per_chunk,
        graph_batch_size=settings.ingestion_graph_batch_size,
    )


def build_runtime_config(settings: "Settings") -> LlamaIndexRuntimeConfig:
    return LlamaIndexRuntimeConfig(
        cost_mode=resolve_cost_mode(settings.ingestion_cost_mode),
        embedding=build_embedding_config(settings),
        ocr=build_ocr_config(settings),
        llm=build_llm_config(settings), # Added LLM configuration
        tuning=build_pipeline_tuning(settings),
        workspace_dir=settings.ingestion_workspace_dir,
        llama_cache_dir=settings.ingestion_llama_cache_dir,
        chroma_persist_dir=settings.ingestion_chroma_dir,
        vector_backend=settings.vector_backend,
    )


__all__ = [
    "EmbeddingConfig",
    "EmbeddingProvider",
    "EmbeddingSecretEnvelope",
    "IngestionCostMode",
    "LlamaIndexRuntimeConfig",
    "OcrConfig",
    "OcrProvider",
    "LlmConfig", # Added
    "LlmProvider", # Added
    "PipelineTuning",
    "build_embedding_config",
    "build_ocr_config",
    "build_llm_config", # Added
    "build_pipeline_tuning",
    "build_runtime_config",
    "resolve_cost_mode",
]
