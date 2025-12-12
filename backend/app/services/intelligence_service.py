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
from backend.app.storage.document_store import DocumentStore
from backend.app.config import get_settings

logger = logging.getLogger(__name__)

class IntelligenceService:
    """
    Orchestrator for high-level intelligence tasks:
    - Autonomous timeline extraction
    - Legal theory formulation
    - Cross-document relationship building
    """
    def __init__(self):
        self.settings = get_settings()
        self.llm_service = get_llm_service()
        self.timeline_service = get_timeline_service()
        self.legal_theory_engine = LegalTheoryEngine()
        self.kg_service = get_knowledge_graph_service()
        self.document_store = DocumentStore(base_dir=self.settings.document_storage_path, encryption_key=self.settings.encryption_key)
        
        # Initialize Agents
        self.timeline_agent = TimelineAgent(self.llm_service)

    async def on_document_ingested(self, case_id: str, doc_id: str, doc_text: str, metadata: Dict[str, Any]):
        """
        Triggered when a document is successfully ingested.
        Decides which autonomous agents to run based on document content/metadata.
        """
        logger.info(f"IntelligenceService triggered for doc {doc_id} in case {case_id}")
        
        tasks = []

        # 1. Timeline Extraction
        if self._should_extract_timeline(doc_text, metadata):
            tasks.append(self._run_timeline_extraction(case_id, doc_id, doc_text, metadata))

        # 2. Legal Theory Update (if significant)
        if self._is_significant_legal_doc(metadata):
            tasks.append(self._update_legal_theories(case_id))

        if tasks:
            await asyncio.gather(*tasks)

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

    async def _run_timeline_extraction(self, case_id: str, doc_id: str, text: str, metadata: Dict[str, Any]):
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
