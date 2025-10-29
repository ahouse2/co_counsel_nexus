"""Fallback primitives used when LlamaIndex is not available."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence
from uuid import uuid4


class MetadataModeEnum:
    """Minimal stand-in for LlamaIndex metadata mode enum."""

    ALL = "ALL"


@dataclass
class FallbackDocument:
    text: str
    metadata: Dict[str, object]

    def __init__(self, text: str, metadata: Dict[str, object] | None = None, metadata_mode: object | None = None) -> None:
        self.text = text
        self.metadata = metadata or {}

    def get_content(self, metadata_mode: object | None = None) -> str:
        return self.text


@dataclass
class FallbackTextNode:
    node_id: str
    text: str
    metadata: Dict[str, object]

    def get_content(self, metadata_mode: object | None = None) -> str:
        return self.text


class FallbackSentenceSplitter:
    """Deterministic sentence splitter mirroring LlamaIndex behaviour."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = max(1, chunk_size)
        self.chunk_overlap = max(0, chunk_overlap)

    def get_nodes_from_documents(self, documents: Sequence[FallbackDocument]) -> List[FallbackTextNode]:
        nodes: List[FallbackTextNode] = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for document in documents:
            metadata = dict(getattr(document, "metadata", {}))
            text = document.get_content(None)
            for start in range(0, len(text), step):
                chunk = text[start : start + self.chunk_size]
                if not chunk:
                    continue
                node_id = f"fallback::{uuid4()}"
                nodes.append(FallbackTextNode(node_id=node_id, text=chunk, metadata=metadata))
        return nodes


__all__ = [
    "FallbackDocument",
    "FallbackSentenceSplitter",
    "FallbackTextNode",
    "MetadataModeEnum",
]
