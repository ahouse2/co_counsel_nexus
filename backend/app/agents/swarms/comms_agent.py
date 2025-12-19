"""
CommsAgent - The gateway agent for each swarm.

Responsibilities:
1. KG Input: Query Knowledge Graph for context before swarm runs
2. KG Output: Write consensus result to KG after swarm completes  
3. Cross-swarm: Send/receive messages to/from other swarms
4. User-facing: Report to Co-Counsel coordinator

Every swarm should have exactly one CommsAgent instance.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService

logger = logging.getLogger(__name__)


@dataclass
class SwarmMessage:
    """A message between swarms or to/from the coordinator."""
    id: str = field(default_factory=lambda: str(uuid4()))
    from_swarm: str = ""
    to_swarm: str = ""  # Empty = broadcast, "coordinator" = to Co-Counsel
    message_type: str = "info"  # info, request, response, alert, consensus
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    case_id: str = "default"
    in_response_to: Optional[str] = None


@dataclass
class ConsensusResult:
    """The result of a swarm's consensus process."""
    swarm_name: str
    case_id: str
    consensus_type: str  # majority_vote, weighted_average, debate, supervisor
    final_output: Dict[str, Any]
    confidence: float  # 0.0 - 1.0
    participating_agents: List[str]
    dissenting_agents: List[str] = field(default_factory=list)
    iterations: int = 1
    timestamp: datetime = field(default_factory=datetime.now)


class CommsAgent:
    """
    The Communications Agent - gateway for each swarm.
    
    Handles all external communication:
    - KG queries (context gathering)
    - KG writes (consensus output)
    - Cross-swarm messaging
    - Reporting to Co-Counsel coordinator
    """
    
    def __init__(
        self, 
        swarm_name: str,
        kg_service: Optional[KnowledgeGraphService] = None,
        message_handler: Optional[Callable] = None
    ):
        self.swarm_name = swarm_name
        self.kg_service = kg_service or get_knowledge_graph_service()
        self.message_handler = message_handler  # Callback for incoming messages
        self.message_queue: List[SwarmMessage] = []
        self.sent_messages: List[SwarmMessage] = []
        self.activity_log: List[Dict[str, Any]] = []
        
        logger.info(f"[CommsAgent:{swarm_name}] Initialized")
    
    # ═══════════════════════════════════════════════════════════════════════
    # KG INPUT - Query context before swarm runs
    # ═══════════════════════════════════════════════════════════════════════
    
    async def query_kg_context(self, case_id: str, context_type: str = "general") -> Dict[str, Any]:
        """
        Query the Knowledge Graph for relevant context before the swarm starts.
        
        Args:
            case_id: The case ID to query for
            context_type: Type of context needed (general, timeline, entities, evidence, etc.)
        
        Returns:
            Dictionary of context data for the swarm
        """
        self._log_activity("kg_query", f"Querying KG for {context_type} context")
        
        context = {
            "case_id": case_id,
            "context_type": context_type,
            "entities": [],
            "relationships": [],
            "documents": [],
            "events": [],
            "facts": []
        }
        
        try:
            # Query entities
            entity_query = """
            MATCH (e:Entity {case_id: $case_id})
            RETURN e.name as name, e.type as type, e.id as id
            LIMIT 50
            """
            entities = await self.kg_service.run_cypher_query(entity_query, {"case_id": case_id})
            context["entities"] = entities or []
            
            # Query relationships
            rel_query = """
            MATCH (a:Entity {case_id: $case_id})-[r]->(b:Entity)
            RETURN a.name as source, type(r) as relationship, b.name as target
            LIMIT 50
            """
            rels = await self.kg_service.run_cypher_query(rel_query, {"case_id": case_id})
            context["relationships"] = rels or []
            
            # Query based on context type
            if context_type == "timeline":
                timeline_query = """
                MATCH (e:Event {case_id: $case_id})
                RETURN e.date as date, e.description as description
                ORDER BY e.date
                LIMIT 30
                """
                events = await self.kg_service.run_cypher_query(timeline_query, {"case_id": case_id})
                context["events"] = events or []
                
            elif context_type == "evidence":
                evidence_query = """
                MATCH (d:Document {case_id: $case_id})
                WHERE d.is_evidence = true OR d.hot_document = true
                RETURN d.id as id, d.summary as summary, d.doc_type as type
                LIMIT 20
                """
                docs = await self.kg_service.run_cypher_query(evidence_query, {"case_id": case_id})
                context["documents"] = docs or []
            
            self._log_activity("kg_query_complete", f"Retrieved {len(context['entities'])} entities, {len(context['relationships'])} relationships")
            
        except Exception as e:
            logger.error(f"[CommsAgent:{self.swarm_name}] KG query failed: {e}")
            self._log_activity("kg_query_error", str(e))
        
        return context
    
    # ═══════════════════════════════════════════════════════════════════════
    # KG OUTPUT - Write consensus to KG
    # ═══════════════════════════════════════════════════════════════════════
    
    async def write_consensus_to_kg(self, consensus: ConsensusResult) -> bool:
        """
        Write the swarm's consensus result to the Knowledge Graph.
        
        Args:
            consensus: The ConsensusResult from the swarm
            
        Returns:
            True if write succeeded
        """
        self._log_activity("kg_write", f"Writing consensus to KG (confidence: {consensus.confidence:.0%})")
        
        try:
            # Create a SwarmOutput node
            query = """
            CREATE (s:SwarmOutput {
                id: $id,
                swarm_name: $swarm_name,
                case_id: $case_id,
                consensus_type: $consensus_type,
                confidence: $confidence,
                output: $output,
                agents: $agents,
                dissenting: $dissenting,
                iterations: $iterations,
                timestamp: datetime($timestamp)
            })
            WITH s
            MATCH (c:Case {id: $case_id})
            MERGE (c)-[:HAS_SWARM_OUTPUT]->(s)
            RETURN s.id as output_id
            """
            
            result = await self.kg_service.run_cypher_query(query, {
                "id": str(uuid4()),
                "swarm_name": consensus.swarm_name,
                "case_id": consensus.case_id,
                "consensus_type": consensus.consensus_type,
                "confidence": consensus.confidence,
                "output": str(consensus.final_output)[:5000],  # Truncate for safety
                "agents": consensus.participating_agents,
                "dissenting": consensus.dissenting_agents,
                "iterations": consensus.iterations,
                "timestamp": consensus.timestamp.isoformat()
            })
            
            # Also create any entities/relationships mentioned in output
            await self._extract_and_store_entities(consensus)
            
            self._log_activity("kg_write_complete", "Consensus stored successfully")
            return True
            
        except Exception as e:
            logger.error(f"[CommsAgent:{self.swarm_name}] KG write failed: {e}")
            self._log_activity("kg_write_error", str(e))
            return False
    
    async def _extract_and_store_entities(self, consensus: ConsensusResult):
        """Extract entities from consensus output and store in KG."""
        output = consensus.final_output
        
        # Store specific outputs based on swarm type
        if "entities" in output:
            for entity in output.get("entities", [])[:20]:
                await self.kg_service.run_cypher_query(
                    """
                    MERGE (e:Entity {name: $name, case_id: $case_id})
                    SET e.type = $type, e.source_swarm = $swarm
                    """,
                    {
                        "name": entity.get("name", ""),
                        "case_id": consensus.case_id,
                        "type": entity.get("type", "unknown"),
                        "swarm": consensus.swarm_name
                    }
                )
    
    # ═══════════════════════════════════════════════════════════════════════
    # CROSS-SWARM MESSAGING
    # ═══════════════════════════════════════════════════════════════════════
    
    async def send_message(self, to_swarm: str, message_type: str, content: Dict[str, Any], case_id: str = "default") -> SwarmMessage:
        """
        Send a message to another swarm.
        
        Args:
            to_swarm: Target swarm name or "coordinator" or "broadcast"
            message_type: Type of message (request, info, alert, etc.)
            content: Message content
            
        Returns:
            The sent message
        """
        message = SwarmMessage(
            from_swarm=self.swarm_name,
            to_swarm=to_swarm,
            message_type=message_type,
            content=content,
            case_id=case_id
        )
        
        self.sent_messages.append(message)
        self._log_activity("message_sent", f"To: {to_swarm}, Type: {message_type}")
        
        # Route through orchestrator
        try:
            from backend.app.services.autonomous_orchestrator import get_orchestrator
            orchestrator = get_orchestrator()
            if orchestrator:
                await orchestrator.route_swarm_message(message)
        except Exception as e:
            logger.warning(f"[CommsAgent:{self.swarm_name}] Could not route message: {e}")
        
        return message
    
    async def receive_message(self, message: SwarmMessage):
        """
        Receive and process an incoming message.
        """
        self.message_queue.append(message)
        self._log_activity("message_received", f"From: {message.from_swarm}, Type: {message.message_type}")
        
        if self.message_handler:
            await self.message_handler(message)
    
    def get_pending_messages(self) -> List[SwarmMessage]:
        """Get all pending messages and clear the queue."""
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages
    
    # ═══════════════════════════════════════════════════════════════════════
    # COORDINATOR REPORTING
    # ═══════════════════════════════════════════════════════════════════════
    
    async def report_to_coordinator(self, status: str, details: Dict[str, Any] = None):
        """
        Report status to the Co-Counsel coordinator.
        """
        await self.send_message(
            to_swarm="coordinator",
            message_type="status_report",
            content={
                "swarm": self.swarm_name,
                "status": status,
                "details": details or {},
                "activity_log": self.activity_log[-10:]  # Last 10 activities
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # ACTIVITY LOGGING
    # ═══════════════════════════════════════════════════════════════════════
    
    def _log_activity(self, activity_type: str, details: str):
        """Log an activity for observability."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "swarm": self.swarm_name,
            "type": activity_type,
            "details": details
        }
        self.activity_log.append(entry)
        logger.debug(f"[CommsAgent:{self.swarm_name}] {activity_type}: {details}")
    
    def get_activity_log(self) -> List[Dict[str, Any]]:
        """Get the activity log for observability."""
        return self.activity_log.copy()


# Factory for creating CommsAgent instances
_comms_agents: Dict[str, CommsAgent] = {}

def get_comms_agent(swarm_name: str) -> CommsAgent:
    """Get or create a CommsAgent for a swarm."""
    global _comms_agents
    if swarm_name not in _comms_agents:
        _comms_agents[swarm_name] = CommsAgent(swarm_name)
    return _comms_agents[swarm_name]
