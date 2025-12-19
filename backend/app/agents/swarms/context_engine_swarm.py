"""
Context Engine Swarm - Autonomous context retrieval and augmentation.

This swarm handles all RAG (Retrieval Augmented Generation) operations:
1. QueryUnderstandingAgent - Parses and enhances user queries
2. HybridRetrievalAgent - Combines vector + graph + keyword search
3. RerankingAgent - Reranks results by relevance
4. ContextSynthesisAgent - Synthesizes retrieved content into coherent context
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.app.services.llm_service import get_llm_service, LLMService
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService

logger = logging.getLogger(__name__)


@dataclass
class ContextAgentResult:
    agent_name: str
    success: bool
    output: Dict[str, Any]


class ContextAgent:
    """Base class for context engine agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def process(self, query: str, context: Dict[str, Any]) -> ContextAgentResult:
        raise NotImplementedError


class QueryUnderstandingAgent(ContextAgent):
    """Agent 1: Parses and enhances user queries for better retrieval."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "QueryUnderstandingAgent")
    
    async def process(self, query: str, context: Dict[str, Any]) -> ContextAgentResult:
        """Parse and enhance the query."""
        try:
            prompt = f"""Analyze this legal research query and enhance it for better retrieval.

QUERY: {query}

Tasks:
1. Identify the query type (factual, legal_principle, case_search, statute_lookup, strategic)
2. Extract key entities and concepts
3. Generate search variations
4. Identify relevant legal domains

Return JSON:
{{
    "query_type": "factual|legal_principle|case_search|statute_lookup|strategic",
    "entities": ["entity1", "entity2"],
    "legal_concepts": ["concept1", "concept2"],
    "search_variations": ["variation1", "variation2"],
    "domains": ["contract", "tort", "criminal", "civil_procedure", "etc"],
    "enhanced_query": "improved query for search"
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return ContextAgentResult(self.name, True, data)
            
            return ContextAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ContextAgentResult(self.name, False, {"error": str(e)})


class HybridRetrievalAgent(ContextAgent):
    """Agent 2: Combines vector + graph + keyword search."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "HybridRetrievalAgent")
    
    async def process(self, query: str, context: Dict[str, Any]) -> ContextAgentResult:
        """Perform hybrid retrieval."""
        try:
            case_id = context.get("case_id", "default")
            enhanced_query = context.get("enhanced_query", query)
            entities = context.get("entities", [])
            
            all_results = []
            
            # 1. Graph-based retrieval (using entities)
            if entities:
                for entity in entities[:3]:
                    graph_query = """
                    MATCH (e:Entity)-[r]-(related)
                    WHERE e.name CONTAINS $entity AND e.case_id = $case_id
                    RETURN e.name as source, type(r) as relationship, 
                           labels(related)[0] as related_type, related.name as related_name
                    LIMIT 10
                    """
                    graph_results = await self.kg_service.run_cypher_query(
                        graph_query, {"entity": entity, "case_id": case_id}
                    )
                    for r in (graph_results or []):
                        all_results.append({
                            "source": "graph",
                            "content": f"{r.get('source')} --[{r.get('relationship')}]--> {r.get('related_name')}",
                            "relevance": 0.8
                        })
            
            # 2. Document search from graph
            doc_query = """
            MATCH (d:Document {case_id: $case_id})
            WHERE d.summary CONTAINS $query OR d.text CONTAINS $query
            RETURN d.id as doc_id, d.summary as summary, d.doc_type as doc_type
            LIMIT 5
            """
            doc_results = await self.kg_service.run_cypher_query(
                doc_query, {"case_id": case_id, "query": query[:50]}
            )
            for r in (doc_results or []):
                all_results.append({
                    "source": "document",
                    "doc_id": r.get("doc_id"),
                    "content": r.get("summary", "")[:500],
                    "doc_type": r.get("doc_type"),
                    "relevance": 0.7
                })
            
            return ContextAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "results": all_results,
                    "result_count": len(all_results),
                    "sources_used": ["graph", "document"]
                }
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ContextAgentResult(self.name, False, {"error": str(e)})


class RerankingAgent(ContextAgent):
    """Agent 3: Reranks results by relevance to query."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "RerankingAgent")
    
    async def process(self, query: str, context: Dict[str, Any]) -> ContextAgentResult:
        """Rerank results by relevance."""
        try:
            results = context.get("results", [])
            
            if not results:
                return ContextAgentResult(self.name, True, {"reranked": []})
            
            # Format results for LLM
            results_text = "\n".join([
                f"{i+1}. [{r.get('source')}] {r.get('content', '')[:200]}"
                for i, r in enumerate(results[:10])
            ])
            
            prompt = f"""Rerank these search results by relevance to the query.

QUERY: {query}

RESULTS:
{results_text}

Return JSON with reranked indices (1-indexed) and scores:
{{
    "ranking": [
        {{"index": 1, "score": 0.95, "reason": "Most relevant because..."}},
        {{"index": 3, "score": 0.85, "reason": "..."}}
    ]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                ranking = data.get("ranking", [])
                
                # Apply ranking
                reranked = []
                for r in ranking:
                    idx = r.get("index", 1) - 1
                    if 0 <= idx < len(results):
                        result = results[idx].copy()
                        result["relevance_score"] = r.get("score", 0.5)
                        result["ranking_reason"] = r.get("reason", "")
                        reranked.append(result)
                
                return ContextAgentResult(self.name, True, {"reranked": reranked})
            
            return ContextAgentResult(self.name, True, {"reranked": results})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ContextAgentResult(self.name, False, {"error": str(e)})


class ContextSynthesisAgent(ContextAgent):
    """Agent 4: Synthesizes retrieved content into coherent context."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "ContextSynthesisAgent")
    
    async def process(self, query: str, context: Dict[str, Any]) -> ContextAgentResult:
        """Synthesize context from retrieved results."""
        try:
            reranked = context.get("reranked", [])
            
            if not reranked:
                return ContextAgentResult(self.name, True, {
                    "synthesized_context": "No relevant information found.",
                    "confidence": 0.0
                })
            
            # Combine top results
            context_parts = [r.get("content", "") for r in reranked[:5]]
            combined = "\n\n".join(context_parts)
            
            prompt = f"""Synthesize this retrieved information into a coherent context for answering the query.

QUERY: {query}

RETRIEVED INFORMATION:
{combined}

Create a well-organized summary that:
1. Directly addresses the query
2. Synthesizes information from multiple sources
3. Notes any contradictions or gaps
4. Provides citations where possible

Return JSON:
{{
    "synthesized_context": "...",
    "key_points": ["point1", "point2"],
    "gaps": ["gap1"],
    "confidence": 0.0-1.0
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return ContextAgentResult(self.name, True, data)
            
            return ContextAgentResult(self.name, True, {
                "synthesized_context": combined,
                "confidence": 0.5
            })
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ContextAgentResult(self.name, False, {"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT ENGINE SWARM
# ═══════════════════════════════════════════════════════════════════════════

class ContextEngineSwarm:
    """
    Swarm for autonomous context retrieval and augmentation (RAG).
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.query_understanding = QueryUnderstandingAgent(self.llm_service, self.kg_service)
        self.hybrid_retrieval = HybridRetrievalAgent(self.llm_service, self.kg_service)
        self.reranking = RerankingAgent(self.llm_service, self.kg_service)
        self.context_synthesis = ContextSynthesisAgent(self.llm_service, self.kg_service)
        
        logger.info("ContextEngineSwarm initialized with 4 agents")
    
    async def retrieve_context(self, query: str, case_id: str) -> Dict[str, Any]:
        """Run full context retrieval pipeline."""
        context = {"case_id": case_id}
        
        # Stage 1: Query understanding
        logger.info(f"[ContextEngineSwarm] Understanding query for case {case_id}")
        query_result = await self.query_understanding.process(query, context)
        context.update(query_result.output)
        
        # Stage 2: Hybrid retrieval
        logger.info(f"[ContextEngineSwarm] Hybrid retrieval")
        retrieval_result = await self.hybrid_retrieval.process(query, context)
        context["results"] = retrieval_result.output.get("results", [])
        
        # Stage 3: Reranking
        logger.info(f"[ContextEngineSwarm] Reranking results")
        rerank_result = await self.reranking.process(query, context)
        context["reranked"] = rerank_result.output.get("reranked", [])
        
        # Stage 4: Context synthesis
        logger.info(f"[ContextEngineSwarm] Synthesizing context")
        synthesis_result = await self.context_synthesis.process(query, context)
        
        return {
            "query": query,
            "case_id": case_id,
            "query_analysis": query_result.output,
            "results_count": len(context.get("results", [])),
            "synthesized_context": synthesis_result.output.get("synthesized_context", ""),
            "confidence": synthesis_result.output.get("confidence", 0.0),
            "key_points": synthesis_result.output.get("key_points", [])
        }


# Factory
_context_swarm: Optional[ContextEngineSwarm] = None

def get_context_engine_swarm() -> ContextEngineSwarm:
    global _context_swarm
    if _context_swarm is None:
        _context_swarm = ContextEngineSwarm()
    return _context_swarm
