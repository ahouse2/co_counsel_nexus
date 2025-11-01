"""Graph exploration utilities for agent workflows."""

from __future__ import annotations

from typing import Dict, Iterable

from backend.app.services.graph import GraphService, GraphTextToCypherResult, get_graph_service


def run_cypher(query: str, parameters: Dict[str, object] | None = None) -> Dict[str, object]:
    """Execute a Cypher statement via the active graph service."""
    service = _service()
    return service.run_cypher(query, parameters)


def build_text_to_cypher_prompt(question: str, schema: str | None = None) -> str:
    """Render a text-to-Cypher prompt tailored to the current schema."""
    service = _service()
    return service.build_text_to_cypher_prompt(question, schema)


def describe_graph_schema() -> str:
    """Return a human-readable description of the property graph schema."""
    service = _service()
    return service.describe_schema()


def community_overview(node_ids: Iterable[str] | None = None) -> Dict[str, object]:
    """Return the latest community summary, optionally filtered by node ids."""
    service = _service()
    summary = service.compute_community_summary(set(node_ids or []))
    return summary.to_dict()


def text_to_cypher(question: str, schema: str | None = None) -> Dict[str, object]:
    """Generate Cypher for a natural language question when supported by the backend."""
    service = _service()
    result: GraphTextToCypherResult = service.text_to_cypher(question, schema=schema)
    return result.to_dict()


def _service() -> GraphService:
    return get_graph_service()
