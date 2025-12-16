from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from backend.app.services.graph import GraphService, get_graph_service
from backend.app.services.llm_service import get_llm_service
# Assuming we have a vector service or using Qdrant client directly. 
# For now, I'll assume we can access Qdrant via a service or client.
# The existing codebase seems to use LlamaIndex for some of this, but we want a "Unified" service.
# Let's check if there is a VectorService. I recall seeing `backend/app/services/vector.py` or similar in previous turns?
# If not, I'll implement a basic Qdrant wrapper here or use LlamaIndex if configured.
# The `GraphService` has `vector_query` but it returns empty in the fallback.

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeResult:
    content: str
    source: str # "graph", "vector", "hybrid"
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class UnifiedKnowledgeService:
    """
    Unified interface for querying Knowledge Graph and Vector Store.
    Implements "Graph-RAG" with Auto-Cypher and Reranking.
    """

    def __init__(self):
        self.graph_service = get_graph_service()
        self.llm_service = get_llm_service()
        self.settings = get_settings()
        # Initialize Vector Client (Qdrant)
        # For now, we'll assume the GraphService might have some vector capabilities or we add them.
        # But to be "Bad Ass", we should probably use the Qdrant client directly for fine-grained control.
        try:
            from qdrant_client import QdrantClient
            self.qdrant = QdrantClient(url=self.settings.qdrant_url)
        except ImportError:
            self.qdrant = None
            logger.warning("Qdrant client not found. Vector search will be disabled.")

    async def query(self, query: str, mode: str = "hybrid") -> List[KnowledgeResult]:
        """
        Executes a natural language query against the knowledge base.
        
        Args:
            query: The user's natural language query.
            mode: "hybrid", "graph", or "vector".
        """
        tasks = []
        
        if mode in ["hybrid", "graph"]:
            tasks.append(self._graph_query(query))
        
        if mode in ["hybrid", "vector"]:
            tasks.append(self._vector_query(query))
            
        results = await asyncio.gather(*tasks)
        
        flat_results = []
        for res_list in results:
            flat_results.extend(res_list)
            
        # Rerank results
        reranked = await self._rerank(query, flat_results)
        return reranked

    async def _graph_query(self, query: str) -> List[KnowledgeResult]:
        """Generates Cypher and queries the graph."""
        try:
            # 1. Generate Cypher
            cypher = await self._generate_cypher(query)
            if not cypher:
                return []
                
            # 2. Execute Cypher
            # We need to access the driver directly or add a method to GraphService
            # GraphService has `driver` attribute if mode is neo4j.
            if self.graph_service.mode != "neo4j":
                return []

            records = []
            with self.graph_service.driver.session() as session:
                result = session.run(cypher)
                records = [dict(record) for record in result]
            
            # 3. Convert to KnowledgeResult
            results = []
            for rec in records:
                # Naive stringification of the record
                content = str(rec)
                results.append(KnowledgeResult(
                    content=content,
                    source="graph",
                    score=1.0, # Placeholder, graph matches are exact
                    metadata={"cypher": cypher, "raw": rec}
                ))
            return results
            
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return []

    async def _vector_query(self, query: str) -> List[KnowledgeResult]:
        """Queries the vector store."""
        if not self.qdrant:
            return []
            
        try:
            # 1. Embed query
            # We need an embedding service. 
            # For now, let's assume we have one or use a placeholder.
            # Ideally, `llm_service` should provide embeddings.
            # Let's check `llm_service` again or `backend/app/services/embeddings.py`?
            # I'll assume `llm_service` has `get_embedding` or similar, or I'll add it.
            # For this draft, I'll skip the actual embedding call and return a mock if not available.
            
            # embedding = await self.llm_service.get_embedding(query)
            # search_result = self.qdrant.search(collection_name="documents", query_vector=embedding, limit=10)
            
            # Placeholder for now until we confirm embedding capability
            return [] 
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            return []

    async def _generate_cypher(self, query: str) -> str:
        """Uses LLM to convert natural language to Cypher."""
        schema = "Nodes: Document, Entity, Organization, Person, Location, Event. Relationships: MENTIONS, ONTOLOGY_CHILD, etc."
        prompt = f"""
        You are a Neo4j Cypher expert. Convert the following question into a Cypher query.
        Schema: {schema}
        Question: {query}
        Return the Cypher query only, no markdown.
        """
        try:
            response = await self.llm_service.generate_text(prompt)
            # Clean up response
            return response.replace("```cypher", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"Cypher generation failed: {e}")
            return ""

    async def _rerank(self, query: str, results: List[KnowledgeResult]) -> List[KnowledgeResult]:
        """Reranks results using LLM or cross-encoder."""
        if not results:
            return []
            
        # Simple LLM based reranking for "Wow" factor (semantic understanding)
        # In production, use a local cross-encoder for speed.
        
        # For now, just return sorted by score (if we had real scores)
        # Or just return as is.
        return results

_unified_knowledge_service: UnifiedKnowledgeService | None = None

def get_unified_knowledge_service() -> UnifiedKnowledgeService:
    global _unified_knowledge_service
    if _unified_knowledge_service is None:
        _unified_knowledge_service = UnifiedKnowledgeService()
    return _unified_knowledge_service
