"""
Narrative Swarm - Autonomous case narrative and timeline analysis.

Agents:
1. TimelineBuilderAgent - Constructs chronological timeline from KG
2. ContradictionDetectorAgent - Identifies factual inconsistencies
3. StoryArcAgent - Maps narrative tension and key turning points
4. CausationAnalystAgent - Traces cause-effect relationships
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
class NarrativeAgentResult:
    """Result from a narrative agent."""
    agent_name: str
    success: bool
    output: Dict[str, Any]


class NarrativeAgent:
    """Base class for narrative swarm agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> NarrativeAgentResult:
        raise NotImplementedError


class TimelineBuilderAgent(NarrativeAgent):
    """Agent 1: Constructs a master timeline from the Knowledge Graph."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "TimelineBuilderAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> NarrativeAgentResult:
        """Build timeline from graph events."""
        try:
            # Query KG for all events
            query = """
            MATCH (e:Event {case_id: $case_id})
            OPTIONAL MATCH (e)-[:INVOLVES]->(entity:Entity)
            OPTIONAL MATCH (e)<-[:DOCUMENTS]-(d:Document)
            RETURN e.date as date, e.title as title, e.description as description,
                   collect(DISTINCT entity.name) as entities,
                   collect(DISTINCT d.id) as documents
            ORDER BY e.date
            """
            
            events = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            
            if not events:
                # Fallback: use LLM to construct from documents
                return NarrativeAgentResult(self.name, True, {"events": [], "source": "empty"})
            
            timeline_events = []
            for event in events:
                timeline_events.append({
                    "date": str(event.get("date", "unknown")),
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                    "entities": event.get("entities", []),
                    "documents": event.get("documents", [])
                })
            
            return NarrativeAgentResult(
                agent_name=self.name,
                success=True,
                output={"events": timeline_events, "source": "knowledge_graph"}
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return NarrativeAgentResult(self.name, False, {"error": str(e)})


class ContradictionDetectorAgent(NarrativeAgent):
    """Agent 2: Identifies factual contradictions across documents and events."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "ContradictionDetectorAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> NarrativeAgentResult:
        """Detect contradictions using graph and LLM."""
        try:
            # Query for existing contradiction relationships
            query = """
            MATCH (e1)-[:CONTRADICTS]->(e2)
            WHERE e1.case_id = $case_id OR e2.case_id = $case_id
            RETURN e1.description as claim1, e2.description as claim2,
                   e1.source as source1, e2.source as source2
            LIMIT 10
            """
            
            graph_contradictions = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            
            # Use LLM to analyze timeline for additional contradictions
            timeline_events = context.get("timeline", {}).get("events", [])
            
            if timeline_events:
                events_text = "\n".join([
                    f"- {e['date']}: {e['title']} - {e['description']}"
                    for e in timeline_events[:20]
                ])
                
                prompt = f"""Analyze these timeline events for factual contradictions:

{events_text}

Find instances where:
- Two events claim different things happened
- Timestamps are impossible (effect before cause)
- Facts directly contradict each other

Return JSON:
{{
    "contradictions": [
        {{
            "claim1": "...",
            "claim2": "...",
            "type": "temporal|factual|logical",
            "severity": "high|medium|low",
            "explanation": "..."
        }}
    ]
}}"""
                
                response = await self.llm_service.generate_text(prompt)
                import json
                import re
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    
                    # Publish event if high-severity contradiction found
                    high_severity = [c for c in data.get("contradictions", []) if c.get("severity") == "high"]
                    if high_severity:
                        from backend.app.services.autonomous_orchestrator import get_orchestrator, SystemEvent, EventType
                        orchestrator = get_orchestrator()
                        await orchestrator.publish(SystemEvent(
                            event_type=EventType.CONTRADICTION_DETECTED,
                            case_id=case_id,
                            source_service=self.name,
                            payload={"contradictions": high_severity}
                        ))
                    
                    return NarrativeAgentResult(self.name, True, data)
            
            return NarrativeAgentResult(self.name, True, {"contradictions": []})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return NarrativeAgentResult(self.name, False, {"error": str(e)})


class StoryArcAgent(NarrativeAgent):
    """Agent 3: Maps narrative tension and key turning points."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "StoryArcAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> NarrativeAgentResult:
        """Generate story arc with tension levels."""
        try:
            timeline_events = context.get("timeline", {}).get("events", [])
            
            if not timeline_events:
                return NarrativeAgentResult(self.name, True, {"arc": []})
            
            events_text = "\n".join([
                f"- {e['date']}: {e['title']} - {e['description']}"
                for e in timeline_events[:30]
            ])
            
            prompt = f"""Analyze this case timeline and create a narrative arc with tension levels.

TIMELINE:
{events_text}

For each event, assign a TENSION LEVEL (0.0-1.0):
- 0.0-0.2: Setup, background
- 0.3-0.5: Rising action, complications
- 0.6-0.8: Conflict, confrontation
- 0.9-1.0: Climax, crisis

Also identify:
- Inciting incident
- Rising action events
- Climax
- Resolution (if any)

Return JSON:
{{
    "arc_points": [
        {{"date": "...", "event": "...", "tension": 0.5, "arc_stage": "rising_action"}}
    ],
    "inciting_incident": "...",
    "climax": "...",
    "narrative_summary": "..."
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return NarrativeAgentResult(self.name, True, data)
            
            return NarrativeAgentResult(self.name, False, {"error": "Failed to parse story arc"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return NarrativeAgentResult(self.name, False, {"error": str(e)})


class CausationAnalystAgent(NarrativeAgent):
    """Agent 4: Traces cause-effect relationships for legal causation."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "CausationAnalystAgent")
    
    async def process(self, case_id: str, context: Dict[str, Any]) -> NarrativeAgentResult:
        """Analyze causation chains from graph."""
        try:
            # Query KG for causal relationships
            query = """
            MATCH path = (cause)-[:CAUSED|RESULTED_IN*1..3]->(effect)
            WHERE cause.case_id = $case_id
            RETURN cause.description as cause, effect.description as effect,
                   length(path) as chain_length
            LIMIT 20
            """
            
            causal_chains = await self.kg_service.run_cypher_query(query, {"case_id": case_id})
            
            chains = []
            for chain in causal_chains or []:
                chains.append({
                    "cause": chain.get("cause", ""),
                    "effect": chain.get("effect", ""),
                    "chain_length": chain.get("chain_length", 1)
                })
            
            # Use LLM to strengthen causation analysis
            timeline = context.get("timeline", {}).get("events", [])
            if timeline and not chains:
                # Generate causation from timeline
                prompt = f"""Analyze these case events for cause-effect relationships:

{chr(10).join([f"- {e['date']}: {e['title']}" for e in timeline[:15]])}

Identify clear causation chains (A caused B, B led to C).

Return JSON:
{{
    "causation_chains": [
        {{
            "chain": ["event A", "event B", "event C"],
            "strength": "strong|moderate|weak",
            "legal_significance": "..."
        }}
    ]
}}"""
                
                response = await self.llm_service.generate_text(prompt)
                import json
                import re
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    return NarrativeAgentResult(self.name, True, data)
            
            return NarrativeAgentResult(self.name, True, {"causation_chains": chains})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return NarrativeAgentResult(self.name, False, {"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# NARRATIVE SWARM
# ═══════════════════════════════════════════════════════════════════════════

class NarrativeSwarm:
    """
    Swarm for autonomous narrative analysis with KG integration.
    
    Workflow:
    1. TimelineBuilderAgent → Build timeline from KG
    2. ContradictionDetectorAgent → Find inconsistencies (parallel)
    3. StoryArcAgent → Map narrative structure (parallel)
    4. CausationAnalystAgent → Trace causation
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.timeline_builder = TimelineBuilderAgent(self.llm_service, self.kg_service)
        self.contradiction_detector = ContradictionDetectorAgent(self.llm_service, self.kg_service)
        self.story_arc = StoryArcAgent(self.llm_service, self.kg_service)
        self.causation_analyst = CausationAnalystAgent(self.llm_service, self.kg_service)
        
        logger.info("NarrativeSwarm initialized with 4 agents")
    
    async def analyze_case(self, case_id: str) -> Dict[str, Any]:
        """Run full narrative analysis on a case."""
        context = {"case_id": case_id}
        results = {}
        
        # Stage 1: Build timeline
        logger.info(f"[NarrativeSwarm] Building timeline for case {case_id}")
        timeline_result = await self.timeline_builder.process(case_id, context)
        results["timeline"] = timeline_result.output
        context["timeline"] = timeline_result.output
        
        # Stage 2: Parallel analysis (contradictions + story arc)
        logger.info(f"[NarrativeSwarm] Parallel contradiction + story arc analysis")
        contradiction_task = self.contradiction_detector.process(case_id, context)
        story_arc_task = self.story_arc.process(case_id, context)
        
        contradiction_result, story_arc_result = await asyncio.gather(contradiction_task, story_arc_task)
        results["contradictions"] = contradiction_result.output
        results["story_arc"] = story_arc_result.output
        
        # Stage 3: Causation analysis
        logger.info(f"[NarrativeSwarm] Causation analysis")
        causation_result = await self.causation_analyst.process(case_id, context)
        results["causation"] = causation_result.output
        
        logger.info(f"[NarrativeSwarm] Analysis complete for case {case_id}")
        
        return {
            "case_id": case_id,
            "success": True,
            "results": results
        }


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

_narrative_swarm: Optional[NarrativeSwarm] = None

def get_narrative_swarm() -> NarrativeSwarm:
    """Get or create the narrative swarm instance."""
    global _narrative_swarm
    if _narrative_swarm is None:
        _narrative_swarm = NarrativeSwarm()
    return _narrative_swarm
