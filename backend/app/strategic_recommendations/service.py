from __future__ import annotations

import logging
from typing import Dict, List, Any
import random

from backend.app.config import Settings, get_settings
from backend.app.services.predictive_analytics import PredictiveAnalyticsService, get_predictive_analytics_service
from backend.app.models.api import GraphStrategyBrief

LOGGER = logging.getLogger(__name__)

class StrategicRecommendationsService:
    def __init__(
        self,
        settings: Settings = Depends(get_settings),
        predictive_analytics_service: PredictiveAnalyticsService = Depends(get_predictive_analytics_service),
    ) -> None:
        self.settings = settings
        self.predictive_analytics_service = predictive_analytics_service

    async def get_strategic_recommendations(
        self,
        question: str,
        focus_nodes: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Provides strategic recommendations based on predictive analytics and legal theories."""
        # Step 1: Get predictive analytics for case outcome
        prediction_result = await self.predictive_analytics_service.predict_case_outcome(
            question=question,
            focus_nodes=focus_nodes,
        )
        predicted_outcome = prediction_result["predicted_outcome"]
        strategy_brief: GraphStrategyBrief = prediction_result["strategy_brief"]

        # Step 2: Generate recommendations based on the predicted outcome and strategy brief
        recommendations = []
        if predicted_outcome == "favorable":
            recommendations.append("Focus on strengthening supporting arguments and leveraging key connections.")
            if strategy_brief.contradictions:
                recommendations.append("Address identified contradictions to solidify your position.")
        elif predicted_outcome == "unfavorable":
            recommendations.append("Identify and mitigate weaknesses in your arguments.")
            recommendations.append("Explore alternative legal theories or settlement options.")
            if strategy_brief.leverage_points:
                recommendations.append("Consider exploiting leverage points of the opposing side.")
        else: # settlement
            recommendations.append("Prepare for negotiation by understanding key arguments and potential compromises.")
            if strategy_brief.contradictions:
                recommendations.append("Be aware of contradictions that could impact negotiation.")

        recommendations.append(f"Consider the following focus nodes: {[node['label'] for node in strategy_brief.focus_nodes]}")
        recommendations.append(f"Key leverage points: {[lp['node']['label'] for lp in strategy_brief.leverage_points]}")

        return {
            "predicted_outcome": predicted_outcome,
            "recommendations": recommendations,
            "prediction_details": prediction_result,
        }


def get_strategic_recommendations_service() -> StrategicRecommendationsService:
    return StrategicRecommendationsService()
