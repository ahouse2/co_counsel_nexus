from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime
from uuid import uuid4

from backend.app.services.llm_service import get_llm_service
from backend.app.services.timeline import get_timeline_service
from backend.app.storage.timeline_store import TimelineEvent
from backend.app.services.legal_theory_engine import LegalTheoryEngine
from backend.app.services.knowledge_graph_service import get_knowledge_graph_service
from backend.app.agents.teams.timeline_agent import TimelineAgent
from backend.app.agents.teams.tagger_agent import TaggerAgent
from backend.app.agents.teams.relation_miner_agent import RelationMinerAgent
from backend.app.agents.teams.summarizer_agent import SummarizerAgent
from backend.app.agents.swarms.research_swarm import get_research_swarm
from backend.app.storage.document_store import DocumentStore
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

class IntelligenceService:
    """
    Orchestrator for the full Agent Swarm:
    - Timeline extraction
    - Auto-tagging
    - Relation mining
    - Document summarization
    - Legal theory formulation
    - Autonomous legal research
    """
    def __init__(self):
        self.settings = get_settings()
        self.llm_service = get_llm_service()
        self.timeline_service = get_timeline_service()
        self.legal_theory_engine = LegalTheoryEngine()
        self.kg_service = get_knowledge_graph_service()
        self.document_store = DocumentStore(base_dir=self.settings.document_storage_path, encryption_key=self.settings.encryption_key)
        
        # Initialize Full Agent Swarm
        self.timeline_agent = TimelineAgent(self.llm_service)
        self.tagger_agent = TaggerAgent(self.llm_service)
        self.relation_miner = RelationMinerAgent(self.llm_service, self.kg_service)
        self.summarizer_agent = SummarizerAgent(self.llm_service)
        
        # Initialize Research Swarm
        self.research_swarm = get_research_swarm()
        
        logger.info("IntelligenceService initialized with full agent swarm + research swarm")

    async def on_document_ingested(self, case_id: str, doc_id: str, doc_text: str, metadata: Dict[str, Any]):
        """
        Triggered when a document is successfully ingested.
        Runs the full agent swarm in parallel for maximum efficiency.
        """
        logger.info(f"IntelligenceService: Full swarm triggered for doc {doc_id} in case {case_id}")
        
        swarm_results = {
            "doc_id": doc_id,
            "case_id": case_id,
            "agents_run": [],
            "tags": [],
            "relations": [],
            "summary": {},
            "timeline_events": 0
        }
        
        tasks = []

        # 1. Always run: Tagger Agent
        tasks.append(self._run_tagger(doc_id, doc_text, metadata, swarm_results))
        
        # 2. Always run: Relation Miner Agent
        tasks.append(self._run_relation_miner(doc_id, doc_text, metadata, swarm_results))
        
        # 3. Always run: Summarizer Agent
        tasks.append(self._run_summarizer(doc_id, doc_text, metadata, swarm_results))
        
        # 4. Timeline Extraction (most docs)
        if self._should_extract_timeline(doc_text, metadata):
            tasks.append(self._run_timeline_extraction(case_id, doc_id, doc_text, metadata, swarm_results))

        # 5. Legal Theory Update (significant docs only)
        if self._is_significant_legal_doc(metadata):
            tasks.append(self._update_legal_theories(case_id))
        
        # 6. Research Swarm (autonomous legal research)
        tasks.append(self._run_research_swarm(case_id, doc_id, doc_text, metadata, swarm_results))

        # Run all agents in parallel
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log swarm completion
        logger.info(f"Swarm completed for {doc_id}: {len(swarm_results['agents_run'])} agents, "
                   f"{len(swarm_results['tags'])} tags, {len(swarm_results['relations'])} relations")
        
        # Update document metadata with swarm results
        try:
            await self._save_swarm_results(case_id, doc_id, metadata, swarm_results)
        except Exception as e:
            logger.error(f"Failed to save swarm results: {e}")
        
        return swarm_results

    async def _run_tagger(self, doc_id: str, text: str, metadata: Dict[str, Any], results: Dict):
        """Run TaggerAgent and store results"""
        try:
            logger.info(f"Running TaggerAgent for {doc_id}")
            tags = await self.tagger_agent.generate_tags(text, metadata)
            results["tags"] = tags
            results["agents_run"].append("TaggerAgent")
            logger.info(f"TaggerAgent generated {len(tags)} tags for {doc_id}")
        except Exception as e:
            logger.error(f"TaggerAgent failed for {doc_id}: {e}", exc_info=True)

    async def _run_relation_miner(self, doc_id: str, text: str, metadata: Dict[str, Any], results: Dict):
        """Run RelationMinerAgent and store results"""
        try:
            logger.info(f"Running RelationMinerAgent for {doc_id}")
            relations = await self.relation_miner.extract_relations(text, doc_id, metadata)
            results["relations"] = relations
            results["agents_run"].append("RelationMinerAgent")
            logger.info(f"RelationMinerAgent extracted {len(relations)} relations for {doc_id}")
        except Exception as e:
            logger.error(f"RelationMinerAgent failed for {doc_id}: {e}", exc_info=True)

    async def _run_summarizer(self, doc_id: str, text: str, metadata: Dict[str, Any], results: Dict):
        """Run SummarizerAgent and store results"""
        try:
            logger.info(f"Running SummarizerAgent for {doc_id}")
            summary = await self.summarizer_agent.generate_summary(text, metadata)
            results["summary"] = summary
            results["agents_run"].append("SummarizerAgent")
            logger.info(f"SummarizerAgent generated summary for {doc_id}")
        except Exception as e:
            logger.error(f"SummarizerAgent failed for {doc_id}: {e}", exc_info=True)

    async def _save_swarm_results(self, case_id: str, doc_id: str, metadata: Dict[str, Any], results: Dict):
        """Persist swarm results to document metadata"""
        try:
            doc_type = metadata.get("doc_type", "my_documents")
            
            # Update document metadata with swarm results
            self.document_store.update_document_metadata(
                doc_type=doc_type,
                case_id=case_id,
                doc_id=doc_id,
                metadata_updates={
                    "ai_tags": results.get("tags", []),
                    "ai_summary": results.get("summary", {}),
                    "ai_relations_count": len(results.get("relations", [])),
                    "swarm_agents_run": results.get("agents_run", []),
                    "swarm_processed_at": datetime.now().isoformat()
                }
            )
            logger.info(f"Saved swarm results for {doc_id}")
        except Exception as e:
            logger.error(f"Failed to save swarm results for {doc_id}: {e}")

    def _should_extract_timeline(self, text: str, metadata: Dict[str, Any]) -> bool:
        # Heuristic: if it has dates and looks like a narrative or correspondence
        # For now, we'll be generous and try on most docs except very short ones
        if len(text) < 100:
            return False
        return True

    def _is_significant_legal_doc(self, metadata: Dict[str, Any]) -> bool:
        doc_type = metadata.get("doc_type", "")
        category = metadata.get("category", "").lower()
        return "pleading" in category or "motion" in category or "order" in category

    async def _run_timeline_extraction(self, case_id: str, doc_id: str, text: str, metadata: Dict[str, Any], swarm_results: Dict = None):
        try:
            logger.info(f"Running TimelineAgent for {doc_id}")
            extracted_events = await self.timeline_agent.extract_events(text, metadata)
            
            if extracted_events:
                logger.info(f"Extracted {len(extracted_events)} events from {doc_id}")
                
                # Convert to TimelineEvent objects
                timeline_events = []
                for event_data in extracted_events:
                    # Parse date
                    date_str = event_data.get("date", "")
                    ts = datetime.now()
                    try:
                        # Try ISO format first, then simple YYYY-MM-DD
                        ts = datetime.fromisoformat(date_str)
                    except ValueError:
                        try:
                            ts = datetime.strptime(date_str, "%Y-%m-%d")
                        except ValueError:
                            logger.warning(f"Could not parse date '{date_str}' for event in {doc_id}. Using now.")
                            ts = datetime.now()

                    timeline_event = TimelineEvent(
                        id=str(uuid4()),
                        case_id=case_id,
                        ts=ts,
                        title=event_data.get("title", "Untitled Event"),
                        summary=event_data.get("description", ""),
                        citations=[doc_id],
                        risk_score=0.0,
                        risk_band="low",
                        event_type="fact",
                        related_event_ids=[]
                    )
                    timeline_events.append(timeline_event)

                # Save to TimelineService
                self.timeline_service.store.append(timeline_events)
                
        except Exception as e:
            logger.error(f"Timeline extraction failed for {doc_id}: {e}", exc_info=True)

    async def _update_legal_theories(self, case_id: str):
        """Triggers a refresh of legal theories based on new evidence."""
        try:
            logger.info(f"Updating legal theories for case {case_id}")
            theories = await self.legal_theory_engine.suggest_theories(case_id)
            logger.info(f"Generated {len(theories)} theories")
        except Exception as e:
            logger.error(f"Error updating legal theories: {e}", exc_info=True)

    async def _run_research_swarm(self, case_id: str, doc_id: str, text: str, metadata: Dict[str, Any], swarm_results: Dict):
        """Run ResearchSwarm for autonomous legal research"""
        try:
            logger.info(f"Running ResearchSwarm for {doc_id}")
            research_results = await self.research_swarm.research_for_document(
                doc_id=doc_id,
                doc_text=text,
                metadata=metadata,
                case_id=case_id
            )
            swarm_results["agents_run"].append("ResearchSwarm")
            swarm_results["research"] = research_results
            logger.info(f"ResearchSwarm completed for {doc_id}")
        except Exception as e:
            logger.error(f"ResearchSwarm failed for {doc_id}: {e}", exc_info=True)

    async def run_full_case_analysis(self, case_id: str):
        """
        Manually triggers a full analysis of all documents in the case.
        Useful for backfilling intelligence on existing cases.
        """
        logger.info(f"Starting full case analysis for {case_id}")
        documents = self.document_store.list_all_documents(case_id)
        
        for doc in documents:
            doc_id = doc.get("id")
            # We need to fetch full content. 
            # This assumes we can get text easily.
            # In reality, might need to read from file.
            # For now, skipping full text fetch implementation details.
            pass
