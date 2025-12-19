"""
Enhanced Ingestion Swarm - 6 Specialized Agents with KG Integration

This swarm handles the complete document ingestion lifecycle with specialized agents:
1. RouterAgent - Document type classification and routing
2. PrivilegeDetectorAgent - Attorney-client privilege screening
3. HotDocumentAgent - Key evidence flagging
4. MetadataEnricherAgent - Legal metadata extraction
5. GraphLinkerAgent - Entity/relationship creation in KG
6. QAValidatorAgent - Quality assurance checks
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.app.services.llm_service import get_llm_service, LLMService
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService
from backend.app.services.classification_service import ClassificationService
from backend.app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# AGENT BASE CLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AgentResult:
    """Result from an agent's processing."""
    agent_name: str
    success: bool
    output: Dict[str, Any]
    next_action: Optional[str] = None


class IngestionAgent:
    """Base class for ingestion swarm agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def process(self, document: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        """Process a document. Override in subclasses."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════
# SPECIALIZED AGENTS
# ═══════════════════════════════════════════════════════════════════════════

class RouterAgent(IngestionAgent):
    """Agent 1: Classifies document type and routes to appropriate handlers."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "RouterAgent")
    
    async def process(self, document: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        """Classify document and determine processing route."""
        text = document.get("text", "")[:3000]
        
        prompt = f"""Classify this legal document and determine its processing priority.

DOCUMENT TEXT:
{text}

Return JSON:
{{
    "doc_type": "contract|pleading|correspondence|discovery|evidence|financial|medical|other",
    "priority": "high|medium|low",
    "route": "standard|privileged|forensic|expedited",
    "confidence": 0.0-1.0
}}"""

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    output=data,
                    next_action="privilege_check" if data.get("route") == "privileged" else "metadata"
                )
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
        
        return AgentResult(self.name, False, {"error": "Classification failed"})


class PrivilegeDetectorAgent(IngestionAgent):
    """Agent 2: Screens for attorney-client privilege markers."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "PrivilegeDetectorAgent")
    
    async def process(self, document: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        """Detect attorney-client privilege markers."""
        text = document.get("text", "")[:5000]
        
        prompt = f"""Analyze this document for attorney-client privilege indicators.

DOCUMENT:
{text}

Check for:
1. "Privileged and Confidential" headers
2. Attorney-client communications
3. Work product doctrine markers
4. Legal advice content

Return JSON:
{{
    "is_privileged": true/false,
    "privilege_type": "attorney_client|work_product|none",
    "confidence": 0.0-1.0,
    "markers_found": ["marker1", "marker2"],
    "recommendation": "flag_for_review|clear|withhold"
}}"""

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                
                # If privileged, publish event to orchestrator
                if data.get("is_privileged"):
                    from backend.app.services.autonomous_orchestrator import get_orchestrator, SystemEvent, EventType
                    orchestrator = get_orchestrator()
                    await orchestrator.publish(SystemEvent(
                        event_type=EventType.PRIVILEGE_DETECTED,
                        case_id=context.get("case_id", ""),
                        source_service=self.name,
                        payload={"doc_id": document.get("id"), "privilege_type": data.get("privilege_type")}
                    ))
                
                return AgentResult(self.name, True, data)
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
        
        return AgentResult(self.name, False, {"error": "Privilege detection failed"})


class HotDocumentAgent(IngestionAgent):
    """Agent 3: Identifies key evidence documents that need immediate attention."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "HotDocumentAgent")
    
    async def process(self, document: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        """Flag documents as hot/key evidence."""
        text = document.get("text", "")[:4000]
        doc_type = context.get("router_result", {}).get("doc_type", "unknown")
        
        prompt = f"""Analyze this {doc_type} document for "hot document" indicators.

A HOT DOCUMENT is one that:
- Contains smoking gun admissions
- Shows clear liability or damages
- Contradicts key claims
- Contains fraud indicators
- Has critical timeline implications

DOCUMENT:
{text}

Return JSON:
{{
    "is_hot": true/false,
    "heat_score": 0.0-1.0,
    "hot_factors": ["factor1", "factor2"],
    "key_quotes": ["quote1", "quote2"],
    "strategic_value": "high|medium|low",
    "recommended_action": "immediate_review|priority_analysis|standard_processing"
}}"""

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                
                # If hot document, publish event
                if data.get("is_hot") and data.get("heat_score", 0) > 0.7:
                    from backend.app.services.autonomous_orchestrator import get_orchestrator, SystemEvent, EventType
                    orchestrator = get_orchestrator()
                    await orchestrator.publish(SystemEvent(
                        event_type=EventType.HOT_DOCUMENT_FLAGGED,
                        case_id=context.get("case_id", ""),
                        source_service=self.name,
                        payload={"doc_id": document.get("id"), "heat_score": data.get("heat_score")}
                    ))
                
                return AgentResult(self.name, True, data)
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
        
        return AgentResult(self.name, False, {"error": "Hot document detection failed"})


class MetadataEnricherAgent(IngestionAgent):
    """Agent 4: Extracts and enriches legal metadata from documents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "MetadataEnricherAgent")
    
    async def process(self, document: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        """Extract legal metadata for graph and search."""
        text = document.get("text", "")[:5000]
        
        prompt = f"""Extract legal metadata from this document.

DOCUMENT:
{text}

Extract:
1. Named entities (people, organizations, locations)
2. Dates and date ranges
3. Legal citations (cases, statutes)
4. Monetary amounts
5. Contract terms (if applicable)
6. Key legal concepts

Return JSON:
{{
    "entities": [
        {{"name": "...", "type": "person|org|location|court", "role": "plaintiff|defendant|witness|attorney|other"}}
    ],
    "dates": [
        {{"date": "YYYY-MM-DD", "context": "event description"}}
    ],
    "citations": [
        {{"citation": "...", "type": "case|statute|regulation"}}
    ],
    "amounts": [
        {{"amount": 0.00, "currency": "USD", "context": "..."}}
    ],
    "legal_concepts": ["concept1", "concept2"],
    "summary": "brief document summary"
}}"""

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return AgentResult(self.name, True, data, next_action="graph_link")
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
        
        return AgentResult(self.name, False, {"error": "Metadata extraction failed"})


class GraphLinkerAgent(IngestionAgent):
    """Agent 5: Creates entities and relationships in the Knowledge Graph."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "GraphLinkerAgent")
    
    async def process(self, document: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        """Create graph nodes and relationships from extracted metadata."""
        doc_id = document.get("id", str(uuid4()))
        case_id = context.get("case_id", "default")
        metadata = context.get("metadata_result", {})
        
        nodes_created = 0
        relationships_created = 0
        
        try:
            # Create document node
            doc_node_query = """
            MERGE (d:Document {id: $doc_id})
            SET d.case_id = $case_id,
                d.summary = $summary,
                d.updated_at = datetime()
            RETURN d
            """
            await self.kg_service.run_cypher_query(doc_node_query, {
                "doc_id": doc_id,
                "case_id": case_id,
                "summary": metadata.get("summary", "")[:500]
            })
            nodes_created += 1
            
            # Create entity nodes and link to document
            for entity in metadata.get("entities", [])[:20]:
                entity_query = """
                MERGE (e:Entity {name: $name, type: $type})
                WITH e
                MATCH (d:Document {id: $doc_id})
                MERGE (d)-[:MENTIONS {role: $role}]->(e)
                RETURN e
                """
                await self.kg_service.run_cypher_query(entity_query, {
                    "name": entity.get("name", "Unknown"),
                    "type": entity.get("type", "unknown"),
                    "role": entity.get("role", "mentioned"),
                    "doc_id": doc_id
                })
                nodes_created += 1
                relationships_created += 1
            
            # Create citation nodes and links
            for citation in metadata.get("citations", [])[:10]:
                citation_query = """
                MERGE (c:Citation {text: $citation, type: $type})
                WITH c
                MATCH (d:Document {id: $doc_id})
                MERGE (d)-[:CITES]->(c)
                RETURN c
                """
                await self.kg_service.run_cypher_query(citation_query, {
                    "citation": citation.get("citation", ""),
                    "type": citation.get("type", "case"),
                    "doc_id": doc_id
                })
                relationships_created += 1
            
            # Publish graph updated event
            from backend.app.services.autonomous_orchestrator import get_orchestrator, SystemEvent, EventType
            orchestrator = get_orchestrator()
            await orchestrator.publish(SystemEvent(
                event_type=EventType.GRAPH_UPDATED,
                case_id=case_id,
                source_service=self.name,
                payload={"doc_id": doc_id, "nodes": nodes_created, "relationships": relationships_created}
            ))
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "nodes_created": nodes_created,
                    "relationships_created": relationships_created,
                    "doc_id": doc_id
                }
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return AgentResult(self.name, False, {"error": str(e)})


class QAValidatorAgent(IngestionAgent):
    """Agent 6: Quality assurance validation of the ingestion results."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "QAValidatorAgent")
    
    async def process(self, document: Dict[str, Any], context: Dict[str, Any]) -> AgentResult:
        """Validate ingestion quality and completeness."""
        checks_passed = []
        checks_failed = []
        
        # Check 1: Document has been classified
        if context.get("router_result", {}).get("doc_type"):
            checks_passed.append("classification_complete")
        else:
            checks_failed.append("classification_missing")
        
        # Check 2: Metadata was extracted
        if context.get("metadata_result", {}).get("entities"):
            checks_passed.append("entities_extracted")
        else:
            checks_failed.append("no_entities_found")
        
        # Check 3: Graph was updated
        if context.get("graph_result", {}).get("nodes_created", 0) > 0:
            checks_passed.append("graph_updated")
        else:
            checks_failed.append("graph_not_updated")
        
        # Check 4: Privilege check completed
        if "privilege_result" in context:
            checks_passed.append("privilege_checked")
        else:
            checks_failed.append("privilege_not_checked")
        
        quality_score = len(checks_passed) / (len(checks_passed) + len(checks_failed)) if checks_passed or checks_failed else 0
        
        return AgentResult(
            agent_name=self.name,
            success=quality_score >= 0.5,
            output={
                "quality_score": quality_score,
                "checks_passed": checks_passed,
                "checks_failed": checks_failed,
                "status": "approved" if quality_score >= 0.75 else "needs_review"
            }
        )


# ═══════════════════════════════════════════════════════════════════════════
# ENHANCED INGESTION SWARM
# ═══════════════════════════════════════════════════════════════════════════

class EnhancedIngestionSwarm:
    """
    Full 6-agent ingestion swarm with KG integration and event publishing.
    
    Workflow:
    1. RouterAgent → Classify and route
    2. PrivilegeDetectorAgent → Screen for privilege (parallel)
    3. HotDocumentAgent → Flag key evidence (parallel)
    4. MetadataEnricherAgent → Extract metadata
    5. GraphLinkerAgent → Update knowledge graph
    6. QAValidatorAgent → Validate results
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        # Initialize all 6 agents
        self.router = RouterAgent(self.llm_service, self.kg_service)
        self.privilege_detector = PrivilegeDetectorAgent(self.llm_service, self.kg_service)
        self.hot_doc_detector = HotDocumentAgent(self.llm_service, self.kg_service)
        self.metadata_enricher = MetadataEnricherAgent(self.llm_service, self.kg_service)
        self.graph_linker = GraphLinkerAgent(self.llm_service, self.kg_service)
        self.qa_validator = QAValidatorAgent(self.llm_service, self.kg_service)
        
        logger.info("EnhancedIngestionSwarm initialized with 6 agents")
    
    async def process_document(self, document: Dict[str, Any], case_id: str) -> Dict[str, Any]:
        """
        Process a document through the complete ingestion swarm.
        
        Args:
            document: {"id": ..., "text": ..., "metadata": {...}}
            case_id: Case identifier
            
        Returns:
            Complete processing results from all agents
        """
        context = {"case_id": case_id}
        results = {}
        
        # Stage 1: Route document
        logger.info(f"[Swarm] Stage 1: Routing document {document.get('id')}")
        router_result = await self.router.process(document, context)
        results["router"] = router_result.output
        context["router_result"] = router_result.output
        
        # Stage 2: Parallel checks (privilege + hot document)
        logger.info(f"[Swarm] Stage 2: Parallel privilege and hot doc checks")
        privilege_task = self.privilege_detector.process(document, context)
        hot_doc_task = self.hot_doc_detector.process(document, context)
        
        privilege_result, hot_doc_result = await asyncio.gather(privilege_task, hot_doc_task)
        results["privilege"] = privilege_result.output
        results["hot_document"] = hot_doc_result.output
        context["privilege_result"] = privilege_result.output
        context["hot_doc_result"] = hot_doc_result.output
        
        # Stage 3: Metadata enrichment
        logger.info(f"[Swarm] Stage 3: Metadata enrichment")
        metadata_result = await self.metadata_enricher.process(document, context)
        results["metadata"] = metadata_result.output
        context["metadata_result"] = metadata_result.output
        
        # Stage 4: Graph linking
        logger.info(f"[Swarm] Stage 4: Knowledge Graph linking")
        graph_result = await self.graph_linker.process(document, context)
        results["graph"] = graph_result.output
        context["graph_result"] = graph_result.output
        
        # Stage 5: QA validation
        logger.info(f"[Swarm] Stage 5: QA validation")
        qa_result = await self.qa_validator.process(document, context)
        results["qa"] = qa_result.output
        
        logger.info(f"[Swarm] Document {document.get('id')} processing complete. QA Score: {qa_result.output.get('quality_score', 0):.0%}")
        
        return {
            "doc_id": document.get("id"),
            "case_id": case_id,
            "success": qa_result.success,
            "results": results
        }


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

_swarm_instance: Optional[EnhancedIngestionSwarm] = None

def get_ingestion_swarm() -> EnhancedIngestionSwarm:
    """Get or create the ingestion swarm instance."""
    global _swarm_instance
    if _swarm_instance is None:
        _swarm_instance = EnhancedIngestionSwarm()
    return _swarm_instance
