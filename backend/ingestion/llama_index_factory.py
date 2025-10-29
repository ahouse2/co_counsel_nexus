"""Factories wiring LlamaIndex components according to runtime settings."""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from typing import Any

from backend.app.utils.text import hashed_embedding

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


class DeterministicHashEmbedding:
    """Deterministic embedding used for offline testing and hashing modes."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def get_text_embedding(self, text: str) -> list[float]:
        return hashed_embedding(text, self.dimensions)


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
        if config.model.startswith("hash://"):
            dims = config.dimensions or 384
            return DeterministicHashEmbedding(dims)
        kwargs = {key: value for key, value in config.extra.items() if value is not None}
        if HuggingFaceEmbeddingCls is None:
            raise RuntimeError(
                "HuggingFace embeddings requested but llama-index HuggingFace integration is not installed."
            )
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
