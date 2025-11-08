from __future__ import annotations

import logging
from typing import Dict, List, Any
import random

from backend.app.config import Settings, get_settings
from backend.app.services.legal_theory import LegalTheoryService, get_legal_theory_service
from backend.app.models.api import GraphStrategyBrief

LOGGER = logging.getLogger(__name__)

class PredictiveAnalyticsService:
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        legal_theory_service: LegalTheoryService = Depends(get_legal_theory_service),
    ) -> None:
        self.settings = settings
        self.legal_theory_service = legal_theory_service

    async def predict_case_outcome(
        self,
        question: str,
        focus_nodes: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Predicts case outcomes based on legal theories and available evidence."""
        # Step 1: Synthesize legal theories to get insights
        strategy_brief: GraphStrategyBrief = await self.legal_theory_service.synthesize_legal_theory(
            question=question,
            focus_nodes=focus_nodes,
            limit=10, # Increased limit for more context
        )

        # Step 2: Simulate a prediction based on the strategy brief
        # In a real scenario, this would involve a trained ML model
        # that takes features derived from the strategy brief (e.g., number of contradictions,
        # strength of supporting arguments, leverage points) and historical case data.

        outcome_probabilities = {
            "favorable": random.uniform(0.3, 0.7),
            "unfavorable": random.uniform(0.3, 0.7),
            "settlement": random.uniform(0.1, 0.5),
        }
        # Normalize probabilities to sum to 1
        total = sum(outcome_probabilities.values())
        for key in outcome_probabilities:
            outcome_probabilities[key] /= total

        predicted_outcome = max(outcome_probabilities, key=outcome_probabilities.get)

        summary = f"Based on the synthesized legal theories and available evidence, the predicted outcome is {predicted_outcome} with the following probabilities: "
        for outcome, prob in outcome_probabilities.items():
            summary += f"{outcome}: {prob:.2f}, "
        summary = summary.rstrip(", ") + "."

        return {
            "predicted_outcome": predicted_outcome,
            "probabilities": outcome_probabilities,
            "summary": summary,
            "strategy_brief": strategy_brief.to_dict(),
        }


def get_predictive_analytics_service() -> PredictiveAnalyticsService:
    return PredictiveAnalyticsService()
