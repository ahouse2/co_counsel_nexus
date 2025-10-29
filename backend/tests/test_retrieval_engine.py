from __future__ import annotations

from typing import List

import pytest
from qdrant_client.http import models as qmodels

from backend.app.services import retrieval_engine as engine_module


class _StubVectorAdapter:
    def __init__(self, points: List[qmodels.ScoredPoint]):
        self._points = points

    def retrieve(self, _query: str, *, top_k: int) -> List[qmodels.ScoredPoint]:
        return self._points[:top_k]


class _StubGraphAdapter:
    def __init__(self, points: List[qmodels.ScoredPoint], relations: List[tuple[str, str | None]]):
        self._points = points
        self._relations = relations

    def retrieve(
        self,
        _query: str,
        *,
        top_k: int,
    ) -> tuple[List[qmodels.ScoredPoint], List[tuple[str, str | None]]]:
        return self._points[:top_k], self._relations[:top_k]


class _StubKeywordAdapter:
    def __init__(self, points: List[qmodels.ScoredPoint]):
        self._points = points

    def retrieve(self, _query: str, *, top_k: int) -> List[qmodels.ScoredPoint]:
        return self._points[:top_k]


@pytest.fixture()
def hybrid_engine() -> engine_module.HybridQueryEngine:
    vector_points = [
        qmodels.ScoredPoint(
            id="vector::1",
            score=0.9,
            payload={"doc_id": "doc-vec", "text": "vector snippet", "chunk_index": 0},
            version=1,
        )
    ]
    graph_points = [
        qmodels.ScoredPoint(
            id="graph::edge",
            score=0.6,
            payload={"doc_id": "doc-graph", "text": "Graph relation", "chunk_index": 1},
            version=1,
        )
    ]
    keyword_points = [
        qmodels.ScoredPoint(
            id="keyword::1",
            score=0.5,
            payload={"doc_id": "doc-key", "text": "Keyword match", "chunk_index": 2},
            version=1,
        )
    ]
    relations = [("Graph relation", "doc-graph")]
    return engine_module.HybridQueryEngine(
        vector=_StubVectorAdapter(vector_points),
        graph=_StubGraphAdapter(graph_points, relations),
        keyword=_StubKeywordAdapter(keyword_points),
    )


def test_rrf_fusion_preserves_retriever_provenance(hybrid_engine: engine_module.HybridQueryEngine) -> None:
    bundle = hybrid_engine.retrieve(
        "query",
        top_k=3,
        vector_window=3,
        graph_window=3,
        keyword_window=3,
        use_cross_encoder=False,
    )

    assert bundle.reranker == "rrf"
    assert bundle.relation_statements == [("Graph relation", "doc-graph")]
    assert {point.id for point in bundle.fused_points} >= {"vector::1", "graph::edge", "keyword::1"}

    for point in bundle.fused_points:
        payload = point.payload or {}
        assert "retrievers" in payload
        assert payload["fusion_score"] == pytest.approx(point.score)
        key = engine_module._point_key(point)
        assert key in bundle.fusion_scores
        assert bundle.fusion_scores[key] == pytest.approx(payload["fusion_score"])


def test_cross_encoder_fallback_when_unavailable(
    hybrid_engine: engine_module.HybridQueryEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hybrid_engine._cross_encoder_model = "dummy-model"

    calls: dict[str, int] = {"count": 0}

    def _fake_cross_encoder():
        calls["count"] += 1
        return None

    monkeypatch.setattr(hybrid_engine, "_ensure_cross_encoder", _fake_cross_encoder)

    bundle = hybrid_engine.retrieve(
        "query",
        top_k=2,
        vector_window=2,
        graph_window=2,
        keyword_window=2,
        use_cross_encoder=True,
    )

    assert calls["count"] == 1
    assert bundle.reranker == "rrf"
    assert all("cross_encoder_score" not in (point.payload or {}) for point in bundle.fused_points)
