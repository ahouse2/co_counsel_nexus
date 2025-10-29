"""End-to-end LlamaIndex ingestion orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

from importlib import import_module
from importlib.util import find_spec

from backend.app.models.api import IngestionSource
from backend.app.utils.triples import EntitySpan, Triple, extract_entities, extract_triples

from .loader_registry import LoadedDocument, LoaderRegistry
from .llama_index_factory import (
    configure_global_settings,
    create_embedding_model,
    create_sentence_splitter,
)
from .metrics import record_document_yield, record_node_yield, record_pipeline_metrics
from .settings import LlamaIndexRuntimeConfig
from .fallback import MetadataModeEnum


def _has_spec(path: str) -> bool:
    try:
        return find_spec(path) is not None
    except ModuleNotFoundError:
        return False


def _resolve_metadata_mode() -> object:
    if not _has_spec("llama_index.core.schema"):
        return MetadataModeEnum
    try:
        module = import_module("llama_index.core.schema")
        return getattr(module, "MetadataMode")
    except (ModuleNotFoundError, AttributeError):
        return MetadataModeEnum


MetadataMode = _resolve_metadata_mode()
METADATA_MODE_ALL = getattr(MetadataMode, "ALL", MetadataModeEnum.ALL)


@dataclass
class PipelineNodeRecord:
    node_id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, object]
    chunk_index: int


@dataclass
class DocumentPipelineResult:
    loaded: LoadedDocument
    nodes: List[PipelineNodeRecord]
    entities: List[EntitySpan]
    triples: List[Triple]


@dataclass
class PipelineResult:
    job_id: str
    source: IngestionSource
    documents: List[DocumentPipelineResult] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return sum(len(doc.nodes) for doc in self.documents)


def run_ingestion_pipeline(
    job_id: str,
    materialized_root: Path,
    source: IngestionSource,
    origin: str,
    *,
    registry: LoaderRegistry,
    runtime_config: LlamaIndexRuntimeConfig,
) -> PipelineResult:
    """Materialise documents, chunk into nodes, and enrich with embeddings."""

    configure_global_settings(runtime_config)
    splitter = create_sentence_splitter(runtime_config.tuning)
    embedding_model = create_embedding_model(runtime_config.embedding)

    with record_pipeline_metrics(source.type.lower(), job_id):
        loaded_documents = registry.load_documents(materialized_root, source, origin=origin)
        record_document_yield(len(loaded_documents), source_type=source.type.lower(), job_id=job_id)
        documents = [
            _process_loaded_document(loaded, splitter, embedding_model)
            for loaded in loaded_documents
        ]
        total_nodes = sum(len(doc.nodes) for doc in documents)
        record_node_yield(total_nodes, source_type=source.type.lower(), job_id=job_id)
        return PipelineResult(job_id=job_id, source=source, documents=documents)


def _process_loaded_document(
    loaded: LoadedDocument,
    splitter,
    embedding_model,
) -> DocumentPipelineResult:
    nodes = _split_nodes(splitter, loaded.document)
    pipeline_nodes: List[PipelineNodeRecord] = []
    for index, node in enumerate(nodes):
        text = node.get_content(metadata_mode=METADATA_MODE_ALL)
        vector = embedding_model.get_text_embedding(text)
        metadata = dict(getattr(node, "metadata", {}) or {})
        metadata.setdefault("source_path", str(loaded.path))
        metadata.setdefault("source_type", loaded.source.type.lower())
        pipeline_nodes.append(
            PipelineNodeRecord(
                node_id=node.node_id,
                text=text,
                embedding=vector,
                metadata=metadata,
                chunk_index=index,
            )
        )
    entities = extract_entities(loaded.text)
    triples = extract_triples(loaded.text)
    return DocumentPipelineResult(loaded=loaded, nodes=pipeline_nodes, entities=entities, triples=triples)


def _split_nodes(splitter, document) -> Sequence[Any]:
    nodes = splitter.get_nodes_from_documents([document])
    return nodes


__all__ = ["PipelineResult", "run_ingestion_pipeline"]
