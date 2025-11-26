from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence

import importlib
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from ..config import get_settings


class InMemoryVectorIndex:
    """Deterministic cosine-similarity vector index for offline/testing modes."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self._store: Dict[str, tuple[List[float], Dict[str, object]]] = {}

    def upsert(self, points: Iterable[qmodels.PointStruct]) -> None:
        for point in points:
            vector = list(point.vector)
            if len(vector) != self.dimensions:
                raise ValueError("Vector dimensionality mismatch for in-memory index")
            payload = dict(point.payload or {})
            self._store[str(point.id)] = (vector, payload)

    def search(self, vector: Sequence[float], top_k: int) -> List[qmodels.ScoredPoint]:
        query = list(vector)
        if len(query) != self.dimensions:
            raise ValueError("Query dimensionality mismatch for in-memory index")
        results: List[qmodels.ScoredPoint] = []
        for point_id, (stored_vector, payload) in self._store.items():
            score = self._cosine_similarity(query, stored_vector)
            results.append(
                qmodels.ScoredPoint(
                    id=point_id,
                    score=score,
                    payload=payload,
                    version=0,
                    vector=stored_vector,
                )
            )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot / (left_norm * right_norm)


class VectorService:
    def __init__(self) -> None:
        self.settings = get_settings()
        backend = self.settings.vector_backend
        self._memory_index: InMemoryVectorIndex | None = None
        self.client: QdrantClient | None = None
        self._chroma_collection = None
        self._chroma_client = None
        if backend == "memory":
            self.mode = "memory"
            self._memory_index = InMemoryVectorIndex(self.settings.qdrant_vector_size)
        elif backend == "chroma":
            self.mode = "chroma"
            try:
                chromadb = importlib.import_module("chromadb")
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Vector backend 'chroma' selected but chromadb is not installed. Install chromadb or switch the "
                    "vector backend configuration."
                ) from exc
            self._chroma_client = chromadb.PersistentClient(path=str(self.settings.ingestion_chroma_dir))
            self._chroma_collection = self._chroma_client.get_or_create_collection(self.settings.chroma_collection)
        else:
            self.mode = "qdrant"
            self.client = self._create_client()
            self.ensure_collection()

    def _create_client(self) -> QdrantClient:
        print(f"Initializing QdrantClient. URL: {self.settings.qdrant_url}, Path: {self.settings.qdrant_path}")
        if self.settings.qdrant_url:
            print(f"Connecting to Qdrant at {self.settings.qdrant_url}")
            return QdrantClient(url=self.settings.qdrant_url)
        if self.settings.qdrant_path and self.settings.qdrant_path != ":memory":
            print(f"Connecting to local Qdrant at {self.settings.qdrant_path}")
            return QdrantClient(path=self.settings.qdrant_path)
        print(f"Connecting to local Qdrant at default dir {self.settings.vector_dir}")
        return QdrantClient(path=str(self.settings.vector_dir))

    def ensure_collection(self) -> None:
        if self.mode == "memory" or self.client is None:
            return
        collection = self.settings.qdrant_collection
        size = self.settings.qdrant_vector_size
        try:
            info = self.client.get_collection(collection)
            if info.config.params.vectors.size == size:
                return
            self.client.delete_collection(collection)
        except Exception:
            pass
        try:
            self.client.delete_collection(collection_name=collection)
        except Exception:
            pass
        self.client.create_collection(
            collection_name=collection,
            vectors_config=qmodels.VectorParams(
                size=size,
                distance=qmodels.Distance(self.settings.qdrant_distance),
            ),
        )

    def upsert(self, points: Iterable[qmodels.PointStruct]) -> None:
        if self.mode == "memory":
            assert self._memory_index is not None
            self._memory_index.upsert(points)
            return
        if self.mode == "chroma":
            ids: List[str] = []
            embeddings: List[List[float]] = []
            metadatas: List[Dict[str, object]] = []
            documents: List[str] = []
            for point in points:
                ids.append(str(point.id))
                vector = list(point.vector)
                embeddings.append(vector)
                payload = dict(point.payload or {})
                metadatas.append(payload)
                documents.append(str(payload.get("text", "")))
            self._chroma_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
            return
        assert self.client is not None
        self.client.upsert(collection_name=self.settings.qdrant_collection, points=list(points))

    def search(self, vector: Sequence[float], top_k: int = 8) -> List[qmodels.ScoredPoint]:
        if self.mode == "memory":
            assert self._memory_index is not None
            return self._memory_index.search(vector, top_k)
        if self.mode == "chroma":
            results = self._chroma_collection.query(
                query_embeddings=[list(vector)],
                n_results=top_k,
                include=["metadatas", "distances", "embeddings", "documents"],
            )
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            embeddings = results.get("embeddings", [[]])[0]
            scored: List[qmodels.ScoredPoint] = []
            for idx, point_id in enumerate(ids):
                metadata = metadatas[idx] if idx < len(metadatas) else {}
                distance = distances[idx] if idx < len(distances) else 0.0
                score = 1.0 - distance if distance is not None else 0.0
                vector_out = embeddings[idx] if idx < len(embeddings) else []
                scored.append(
                    qmodels.ScoredPoint(
                        id=point_id,
                        score=float(score),
                        payload=metadata,
                        version=0,
                        vector=vector_out,
                    )
                )
            return scored
        assert self.client is not None
        return self.client.search(
            collection_name=self.settings.qdrant_collection,
            query_vector=list(vector),
            limit=top_k,
            with_payload=True,
        )


_vector_service: VectorService | None = None


def get_vector_service() -> VectorService:
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service


def reset_vector_service() -> None:
    global _vector_service
    _vector_service = None

