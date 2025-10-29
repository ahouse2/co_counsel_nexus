"""High-level exports for the ingestion orchestration package."""

from .fallback import (
    FallbackDocument,
    FallbackSentenceSplitter,
    FallbackTextNode,
    MetadataModeEnum,
)
from .loader_registry import LoaderRegistry, LoadedDocument
from .metrics import record_document_yield, record_node_yield, record_pipeline_metrics
from .ocr import OcrEngine, OcrResult
from .pipeline import PipelineResult, run_ingestion_pipeline
from .settings import (
    EmbeddingConfig,
    EmbeddingProvider,
    IngestionCostMode,
    LlamaIndexRuntimeConfig,
    OcrConfig,
    OcrProvider,
    PipelineTuning,
    build_runtime_config,
)

__all__ = [
    "LoaderRegistry",
    "LoadedDocument",
    "FallbackDocument",
    "FallbackSentenceSplitter",
    "FallbackTextNode",
    "MetadataModeEnum",
    "record_document_yield",
    "record_node_yield",
    "record_pipeline_metrics",
    "OcrEngine",
    "OcrResult",
    "PipelineResult",
    "run_ingestion_pipeline",
    "EmbeddingConfig",
    "EmbeddingProvider",
    "IngestionCostMode",
    "LlamaIndexRuntimeConfig",
    "OcrConfig",
    "OcrProvider",
    "PipelineTuning",
    "build_runtime_config",
]
