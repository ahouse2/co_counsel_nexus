from __future__ import annotations

import logging
from typing import List, Dict, Any

from backend.app.services.graph import GraphService, get_graph_service
from backend.app.services.retrieval import RetrievalService, get_retrieval_service
from backend.app.config import Settings, get_settings
from backend.app.models.api import GraphStrategyBrief

LOGGER = logging.getLogger(__name__)

class ArgumentMappingService:
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        retrieval_service: RetrievalService = Depends(get_retrieval_service),
        graph_service: GraphService = Depends(get_graph_service),
    ) -> None:
        self.settings = settings
        self.retrieval_service = retrieval_service
        self.graph_service = graph_service

    async def get_argument_map_and_contradictions(
        self,
        question: str,
        focus_nodes: List[str] | None = None,
        limit: int = 5,
    ) -> GraphStrategyBrief:
        """Retrieves argument map and contradictions based on retrieved evidence and knowledge graph insights."""
        # This directly leverages the existing synthesize_strategy_brief from GraphService
        # which already computes argument_map and contradictions.
        strategy_brief = self.graph_service.synthesize_strategy_brief(
            focus_nodes=focus_nodes,
            limit=limit,
        )
        return strategy_brief

def get_argument_mapping_service() -> ArgumentMappingService:
    return ArgumentMappingService()
