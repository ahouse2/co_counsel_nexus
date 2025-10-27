#!/usr/bin/env python3
"""Qdrant bootstrap ensuring vector collections for documents and chunks."""

import os
from typing import Dict

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.http.exceptions import UnexpectedResponse


def _ensure_collection(
    client: QdrantClient,
    name: str,
    vectors_config: Dict[str, rest.VectorParams],
    payload_indexes: Dict[str, rest.PayloadSchemaType],
    **kwargs,
) -> None:
    existing = {collection.name for collection in client.get_collections().collections}
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=vectors_config,
            optimizers_config=kwargs.get(
                "optimizers_config",
                rest.OptimizersConfigDiff(default_segment_number=2),
            ),
            hnsw_config=kwargs.get(
                "hnsw_config",
                rest.HnswConfigDiff(m=16, ef_construct=128),
            ),
            quantization_config=kwargs.get("quantization_config"),
        )
    # ensure payload indexes exist (idempotent)
    for field_name, field_schema in payload_indexes.items():
        try:
            client.create_payload_index(
                collection_name=name,
                field_name=field_name,
                field_schema=field_schema,
                wait=True,
            )
        except UnexpectedResponse as exc:  # already exists
            if getattr(exc, "status_code", None) != 409:
                raise


def main() -> None:
    client = QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=30,
    )

    chunk_vectors = {
        "default": rest.VectorParams(size=128, distance=rest.Distance.COSINE)
    }
    chunk_indexes = {
        "document_id": rest.PayloadSchemaType.KEYWORD,
        "source_type": rest.PayloadSchemaType.KEYWORD,
        "tags": rest.PayloadSchemaType.KEYWORD,
        "ordinal": rest.PayloadSchemaType.INTEGER,
    }
    _ensure_collection(
        client,
        name="chunk_embeddings",
        vectors_config=chunk_vectors,
        payload_indexes=chunk_indexes,
        optimizers_config=rest.OptimizersConfigDiff(default_segment_number=2),
        hnsw_config=rest.HnswConfigDiff(m=16, ef_construct=128),
    )

    document_vectors = {
        "default": rest.VectorParams(size=1, distance=rest.Distance.DOT)
    }
    document_indexes = {
        "document_id": rest.PayloadSchemaType.KEYWORD,
        "title": rest.PayloadSchemaType.TEXT,
        "source_uri": rest.PayloadSchemaType.KEYWORD,
    }
    _ensure_collection(
        client,
        name="documents",
        vectors_config=document_vectors,
        payload_indexes=document_indexes,
        optimizers_config=rest.OptimizersConfigDiff(default_segment_number=1),
        hnsw_config=rest.HnswConfigDiff(m=8, ef_construct=32),
    )


if __name__ == "__main__":
    main()
