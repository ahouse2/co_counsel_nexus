"""Factories wiring LlamaIndex components according to runtime settings."""

from __future__ import annotations

import math
from importlib import import_module
from importlib.util import find_spec
from typing import Any

from .fallback import FallbackSentenceSplitter, MetadataModeEnum
from .settings import EmbeddingConfig, EmbeddingProvider, LlamaIndexRuntimeConfig, PipelineTuning


def _import_attr(path: str, attribute: str) -> Any | None:
    try:
        spec = find_spec(path)
    except ModuleNotFoundError:
        return None
    if spec is None:
        return None
    module = import_module(path)
    return getattr(module, attribute, None)


SentenceSplitterCls = _import_attr("llama_index.core.node_parser", "SentenceSplitter")
MetadataMode = _import_attr("llama_index.core.schema", "MetadataMode") or MetadataModeEnum
LlamaIndexGlobalSettings = _import_attr("llama_index.core.settings", "Settings")
HuggingFaceEmbeddingCls = _import_attr("llama_index.embeddings.huggingface", "HuggingFaceEmbedding")
OpenAIEmbeddingCls = _import_attr("llama_index.embeddings.openai", "OpenAIEmbedding")
AzureOpenAIEmbeddingCls = _import_attr("llama_index.embeddings.azure_openai", "AzureOpenAIEmbedding")

try:  # pragma: no cover - optional import for compatibility
    from llama_index.core.embeddings import BaseEmbedding as _BaseEmbedding
except ModuleNotFoundError:  # pragma: no cover - fallback for lightweight environments

    class _BaseEmbedding:  # type: ignore
        """Minimal stand-in for LlamaIndex BaseEmbedding when dependency absent."""

        def get_text_embedding(self, text: str) -> list[float]:  # pragma: no cover - interface shim
            raise NotImplementedError

        def get_query_embedding(self, text: str) -> list[float]:  # pragma: no cover - interface shim
            return self.get_text_embedding(text)


class LocalHuggingFaceEmbedding(_BaseEmbedding):
    """Deterministic local embedding emulating HF behaviour without remote downloads."""

    def __init__(self, model_name: str, dimensions: int | None) -> None:
        self.model_name = model_name
        self.dimensions = max(8, int(dimensions or 384))

    def _encode(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        if not text:
            return vector
        bytes_view = text.encode("utf-8", errors="ignore")
        for index, value in enumerate(bytes_view):
            bucket = (index + value) % self.dimensions
            weight = math.sin(value) + math.cos(index + 1)
            vector[bucket] += weight
        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0.0:
            return vector
        return [component / norm for component in vector]

    def get_text_embedding(self, text: str) -> list[float]:
        return self._encode(text)

    def get_query_embedding(self, text: str) -> list[float]:
        return self._encode(text)


def configure_global_settings(runtime: LlamaIndexRuntimeConfig) -> None:
    """Apply shared runtime knobs (cache dir, metadata defaults)."""

    if runtime.llama_cache_dir:
        runtime.llama_cache_dir.mkdir(parents=True, exist_ok=True)
    if not LlamaIndexGlobalSettings:
        return
    if runtime.llama_cache_dir:
        setattr(LlamaIndexGlobalSettings, "cache_dir", str(runtime.llama_cache_dir))
    metadata_value = getattr(MetadataMode, "ALL", MetadataModeEnum.ALL)
    setattr(LlamaIndexGlobalSettings, "metadata_mode", metadata_value)


def create_sentence_splitter(tuning: PipelineTuning):
    if SentenceSplitterCls is None:
        return FallbackSentenceSplitter(
            chunk_size=tuning.chunk_size,
            chunk_overlap=tuning.chunk_overlap,
        )
    return SentenceSplitterCls(chunk_size=tuning.chunk_size, chunk_overlap=tuning.chunk_overlap)


def create_embedding_model(config: EmbeddingConfig) -> Any:
    """Instantiate the embedding model for the active ingestion tier."""

    if config.provider is EmbeddingProvider.HUGGINGFACE:
        kwargs = {key: value for key, value in config.extra.items() if value is not None}
        if config.model.startswith("local://") or HuggingFaceEmbeddingCls is None:
            return LocalHuggingFaceEmbedding(config.model, config.dimensions)
        return HuggingFaceEmbeddingCls(model_name=config.model, **kwargs)
    if config.provider is EmbeddingProvider.AZURE_OPENAI:
        if AzureOpenAIEmbeddingCls is None:
            raise RuntimeError("Azure OpenAI embeddings requested but dependency missing")
        kwargs = {key: value for key, value in config.extra.items() if value is not None}
        return AzureOpenAIEmbeddingCls(
            deployment_name=config.extra.get("azure_deployment"),
            api_key=config.api_key,
            azure_endpoint=config.api_base,
            api_version=config.extra.get("api_version"),
            model=config.model,
            **kwargs,
        )
    kwargs = {key: value for key, value in config.extra.items() if value is not None}
    if OpenAIEmbeddingCls is None:
        raise RuntimeError("OpenAI embeddings requested but llama-index OpenAI integration is not installed.")
    return OpenAIEmbeddingCls(
        model=config.model,
        api_key=config.api_key,
        api_base=config.api_base,
        **kwargs,
    )


__all__ = [
    "configure_global_settings",
    "create_embedding_model",
    "create_sentence_splitter",
]
