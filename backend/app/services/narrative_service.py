from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.services.llm_service import get_llm_service
from backend.app.services.timeline_service import TimelineService
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service, KnowledgeGraphService
from backend.app.storage.document_store import DocumentStore
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

class Contradiction(BaseModel):
    id: str = Field(..., description="Unique ID for the contradiction")
    description: str = Field(..., description="Description of the contradiction")
    source_a: str = Field(..., description="First conflicting source (e.g., 'Timeline Event: Meeting')")
    source_b: str = Field(..., description="Second conflicting source (e.g., 'Document: Email Log')")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    severity: str = Field(..., description="Severity: 'high', 'medium', 'low'")

class NarrativeService:
    """
    Service for generating case narratives and detecting contradictions using LLM.
    Enhanced with KnowledgeGraphService integration for richer context.
    """
    def __init__(self, timeline_service: TimelineService, document_store: DocumentStore, kg_service: Optional[KnowledgeGraphService] = None):
        self.timeline_service = timeline_service
        self.document_store = document_store
        self.llm_service = get_llm_service()
        self.settings = get_settings()
        # KG Integration: Query graph for entities, relationships, and case context
        self.kg_service = kg_service or get_knowledge_graph_service()

    async def generate_narrative(self, case_id: str) -> str:
        """
        Generates a coherent narrative summary of the case based on timeline events and key documents.
        """
        logger.info(f"Generating narrative for case {case_id}")
        
        # 1. Gather Context
        events = self.timeline_service.get_timeline(case_id)
        documents = self.document_store.list_all_documents(case_id)
        
        # Sort events by date
        sorted_events = sorted(events, key=lambda x: x.event_date)
        
        # Prepare context string
        context_lines = ["TIMELINE EVENTS:"]
        for event in sorted_events:
            context_lines.append(f"- {event.event_date}: {event.title} - {event.description}")
        
        # ═══════════════════════════════════════════════════════════════════
        # KG INTEGRATION: Query graph for entities, relationships, and insights
        # ═══════════════════════════════════════════════════════════════════
        kg_context = await self._get_kg_context(case_id)
        if kg_context:
            context_lines.append("\nKNOWLEDGE GRAPH INSIGHTS:")
            context_lines.extend(kg_context)
            
        context_lines.append("\nKEY DOCUMENTS:")
        # Limit to top 20 documents to avoid context window issues for now
        # Ideally we'd use vector search to find relevant ones, but this is a global summary.
        for doc in documents[:20]: 
            summary = (doc.get("metadata") or {}).get("ai_summary", {}).get("summary", "No summary available")
            context_lines.append(f"- {doc['filename']}: {summary}")
            
        context_str = "\n".join(context_lines)
        
        # 2. Construct Prompt
        prompt = f"""
        You are an expert legal analyst. Your task is to generate a comprehensive narrative summary for a legal case based on the following timeline events and document summaries.
        
        The narrative should:
        1. Be written in a professional, objective tone.
        2. Chronologically weave together the events and evidence.
        3. Highlight key actors and their actions.
        4. Identify the central conflict or legal issue.
        
        CASE CONTEXT:
        {context_str}
        
        NARRATIVE:
        """
        
        # 3. Call LLM
        try:
            narrative = await self.llm_service.generate_text(prompt)
            return narrative.strip()
        except Exception as e:
            logger.error(f"Failed to generate narrative: {e}")
            return "Failed to generate narrative due to an internal error."

    async def detect_contradictions(self, case_id: str) -> List[Contradiction]:
        """
        Analyzes the case data to detect contradictions between timeline events and documents.
        """
        logger.info(f"Detecting contradictions for case {case_id}")
        
        # 1. Gather Context (Reuse similar logic)
        events = self.timeline_service.get_timeline(case_id)
        documents = self.document_store.list_all_documents(case_id)
        
        context_lines = ["TIMELINE EVENTS:"]
        for event in events:
            context_lines.append(f"- [Event ID: {event.id}] {event.event_date}: {event.title} - {event.description}")
            
        context_lines.append("\nDOCUMENTS:")
        for doc in documents[:20]:
            summary = (doc.get("metadata") or {}).get("ai_summary", {}).get("summary", "No summary available")
            context_lines.append(f"- [Doc ID: {doc['id']}] {doc['filename']}: {summary}")
            
        context_str = "\n".join(context_lines)
        
        # 2. Construct Prompt
        prompt = f"""
        You are an expert legal analyst. Analyze the following timeline events and document summaries to identify factual contradictions or inconsistencies.
        
        A contradiction occurs when:
        - Two events claim different things happened at the same time.
        - A document contradicts a timeline event description.
        - Timestamps are impossible (e.g., action before cause).
        
        Return the result as a JSON list of objects with the following keys:
        - "description": Brief description of the contradiction.
        - "source_a": The first conflicting source (e.g., "Event: Meeting on 2023-01-01").
        - "source_b": The second conflicting source.
        - "confidence": Float between 0.0 and 1.0.
        - "severity": "high", "medium", or "low".
        
        If no contradictions are found, return an empty list [].
        
        CASE CONTEXT:
        {context_str}
        
        JSON OUTPUT:
        """
        
        # 3. Call LLM
        try:
            logger.info("Calling LLM for contradiction detection...")
            response_text = await self.llm_service.generate_text(prompt)
            logger.info(f"LLM response received (Length: {len(response_text)})")
            
            # Clean up response to ensure it's valid JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            import json
            import uuid
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM: {e}. Response: {response_text}")
                return []
            
            contradictions = []
            for item in data:
                contradictions.append(Contradiction(
                    id=str(uuid.uuid4()),
                    description=item.get("description", "Unknown contradiction"),
                    source_a=item.get("source_a", "Unknown"),
                    source_b=item.get("source_b", "Unknown"),
                    confidence=float(item.get("confidence", 0.5)),
                    severity=item.get("severity", "medium")
                ))
                
            logger.info(f"Detected {len(contradictions)} contradictions.")
            return contradictions
            
        except Exception as e:
            logger.error(f"Failed to detect contradictions: {e}")
            return []

    async def generate_branching_narrative(
        self, case_id: str, pivot_point: str, alternative_fact: str
    ) -> Dict[str, Any]:
        """
        Generates an alternative narrative based on a 'what if' scenario.
        """
        logger.info(f"Generating branching narrative for case {case_id}")
        
        # 1. Gather Context
        events = self.timeline_service.get_timeline(case_id)
        sorted_events = sorted(events, key=lambda x: x.event_date)
        
        context_lines = ["ORIGINAL TIMELINE:"]
        for event in sorted_events:
            context_lines.append(f"- {event.event_date}: {event.title} - {event.description}")
        
        context_str = "\n".join(context_lines)
        
        # 2. Construct Prompt
        prompt = f"""
        You are an expert legal strategist. Analyze the following case timeline and generate an ALTERNATIVE narrative based on the "what if" scenario.
        
        PIVOT POINT: {pivot_point}
        ALTERNATIVE FACT: {alternative_fact}
        
        Your task:
        1. Re-imagine the case as if the alternative fact were true.
        2. Describe how the narrative would change.
        3. List 3-5 strategic implications for the case.
        
        Return the result as JSON with the following structure:
        {{
            "scenario_id": "scenario_<random_id>",
            "narrative": "<alternative narrative text>",
            "implications": ["<implication 1>", "<implication 2>", ...]
        }}
        
        ORIGINAL CASE CONTEXT:
        {context_str}
        
        JSON OUTPUT:
        """
        
        # 3. Call LLM
        try:
            import json
            import uuid
            
            response_text = await self.llm_service.generate_text(prompt)
            response_text = response_text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            try:
                data = json.loads(response_text)
                return {
                    "scenario_id": data.get("scenario_id", f"scenario_{uuid.uuid4().hex[:8]}"),
                    "narrative": data.get("narrative", "Unable to generate alternative narrative."),
                    "implications": data.get("implications", [])
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, treat response as raw narrative
                return {
                    "scenario_id": f"scenario_{uuid.uuid4().hex[:8]}",
                    "narrative": response_text,
                    "implications": ["LLM response was not structured JSON"]
                }
                
        except Exception as e:
            logger.error(f"Failed to generate branching narrative: {e}")
            return {
                "scenario_id": "error",
                "narrative": f"Failed to generate alternative narrative: {e}",
                "implications": []
            }

    async def generate_story_arc(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Generates story arc data points with tension levels for visualization.
        """
        logger.info(f"Generating story arc for case {case_id}")
        
        # 1. Gather Timeline Events
        events = self.timeline_service.get_timeline(case_id)
        sorted_events = sorted(events, key=lambda x: x.event_date)
        
        if not sorted_events:
            return []
        
        # 2. Construct Prompt
        event_list = []
        for event in sorted_events:
            event_list.append(f"- {event.event_date}: {event.title} - {event.description}")
        
        events_str = "\n".join(event_list)
        
        prompt = f"""
        You are an expert narrative analyst. Analyze the following timeline events and assign a TENSION LEVEL (0.0 to 1.0) to each event based on its narrative significance.
        
        Guidelines for tension levels:
        - 0.0-0.2: Routine events, setup, background
        - 0.3-0.5: Rising action, complications developing
        - 0.6-0.8: Conflict, confrontation, critical decisions
        - 0.9-1.0: Climax, crisis, turning point
        
        Return the result as a JSON list with the following structure:
        [
            {{"timestamp": "<date>", "event": "<title>", "tension_level": <float>}},
            ...
        ]
        
        TIMELINE EVENTS:
        {events_str}
        
        JSON OUTPUT:
        """
        
        # 3. Call LLM
        try:
            import json
            
            response_text = await self.llm_service.generate_text(prompt)
            response_text = response_text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            try:
                data = json.loads(response_text)
                return data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse story arc JSON: {response_text}")
                # Fallback: assign linear tension
                return [
                    {
                        "timestamp": str(event.event_date),
                        "event": event.title,
                        "tension_level": min(1.0, 0.2 + (i * 0.1))
                    }
                    for i, event in enumerate(sorted_events)
                ]
                
        except Exception as e:
            logger.error(f"Failed to generate story arc: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════
    # KNOWLEDGE GRAPH INTEGRATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _get_kg_context(self, case_id: str) -> List[str]:
        """
        Query the Knowledge Graph component for entities, relationships, and insights
        related to the case. This enriches narrative generation with graph-derived context.
        """
        context_lines = []
        
        try:
            # 1. Get case context from KG (entities, relationships, and their connections)
            case_context = await self.kg_service.get_case_context(case_id)
            
            if case_context:
                # Extract key entities
                entities = case_context.get("entities", [])
                if entities:
                    context_lines.append("KEY ENTITIES:")
                    for entity in entities[:10]:  # Limit to top 10
                        entity_type = entity.get("type", "Unknown")
                        entity_name = entity.get("name") or entity.get("label", "Unknown")
                        context_lines.append(f"  - [{entity_type}] {entity_name}")
                
                # Extract relationships
                relationships = case_context.get("relationships", [])
                if relationships:
                    context_lines.append("KEY RELATIONSHIPS:")
                    for rel in relationships[:10]:
                        source = rel.get("source", "?")
                        target = rel.get("target", "?")
                        rel_type = rel.get("type", "RELATED_TO")
                        context_lines.append(f"  - {source} --[{rel_type}]--> {target}")
            
            # 2. Query for legal research findings (from ResearchSwarm)
            research_query = f"""
            MATCH (c:Case {{id: $case_id}})-[:HAS_RESEARCH]->(r:ResearchFinding)
            RETURN r.source as source, r.summary as summary
            LIMIT 5
            """
            try:
                research_results = await self.kg_service.run_cypher_query(
                    research_query, 
                    {"case_id": case_id}
                )
                if research_results:
                    context_lines.append("LEGAL RESEARCH FINDINGS:")
                    for result in research_results:
                        source = result.get("source", "Unknown Source")
                        summary = result.get("summary", "")[:200]
                        if summary:
                            context_lines.append(f"  - [{source}] {summary}...")
            except Exception as e:
                logger.debug(f"No research findings in graph: {e}")
            
            # 3. Query for cause of action support scores
            cause_scores = await self.kg_service.cause_support_scores(case_id)
            if cause_scores:
                context_lines.append("CAUSE OF ACTION SUPPORT:")
                for cause, score in sorted(cause_scores.items(), key=lambda x: -x[1])[:5]:
                    context_lines.append(f"  - {cause}: {score:.1%} confidence")
            
        except Exception as e:
            logger.warning(f"Failed to get KG context: {e}")
            # Non-blocking - return empty context if KG unavailable
        
        return context_lines


