"""
Swarm Registry - Central registry for all agent swarms.

Provides unified access to all swarms in the system.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

# Import all swarm factories
from backend.app.agents.swarms.ingestion_swarm import get_ingestion_swarm, EnhancedIngestionSwarm
from backend.app.agents.swarms.research_swarm import get_research_swarm
from backend.app.agents.swarms.narrative_swarm import get_narrative_swarm, NarrativeSwarm
from backend.app.agents.swarms.trial_prep_swarm import get_trial_prep_swarm, TrialPrepSwarm
from backend.app.agents.swarms.forensics_swarm import get_forensics_swarm, ForensicsSwarm
from backend.app.agents.swarms.context_engine_swarm import get_context_engine_swarm, ContextEngineSwarm
from backend.app.agents.swarms.legal_research_swarm import get_legal_research_swarm, LegalResearchSwarm
from backend.app.agents.swarms.drafting_swarm import get_drafting_swarm, DraftingSwarm
from backend.app.agents.swarms.asset_hunter_swarm import get_asset_hunter_swarm, AssetHunterSwarm
from backend.app.agents.swarms.simulation_swarm import get_simulation_swarm, SimulationSwarm


class SwarmRegistry:
    """
    Central registry for all agent swarms.
    
    Swarms Available:
    - ingestion: 6 agents (document classification, privilege, metadata, graph)
    - research: existing research automation
    - narrative: 4 agents (timeline, contradictions, story arc, causation)
    - trial_prep: 4 agents (mock trial, jury sentiment, cross-exam, witness)
    - forensics: 5 agents (tampering, metadata, custody, redaction, timeline)
    - context_engine: 4 agents (query, retrieval, reranking, synthesis)
    - legal_research: 5 agents (case law, statutes, secondary, citations, synthesis)
    - drafting: 6 agents (template, facts, arguments, content, citations, proofread)
    - asset_hunter: 5 agents (entity, property, crypto, discrepancy, schemes)
    - simulation: 5 agents (scenarios, outcomes, settlement, risk, strategy)
    
    Total: 48+ agents across 10 swarms
    """
    
    _instance: Optional["SwarmRegistry"] = None
    
    def __init__(self):
        self._swarms = {}
    
    @classmethod
    def get_instance(cls) -> "SwarmRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_swarm(self, name: str):
        """Get a swarm by name."""
        swarm_factories = {
            "ingestion": get_ingestion_swarm,
            "research": get_research_swarm,
            "narrative": get_narrative_swarm,
            "trial_prep": get_trial_prep_swarm,
            "forensics": get_forensics_swarm,
            "context_engine": get_context_engine_swarm,
            "legal_research": get_legal_research_swarm,
            "drafting": get_drafting_swarm,
            "asset_hunter": get_asset_hunter_swarm,
            "simulation": get_simulation_swarm,
        }
        
        factory = swarm_factories.get(name)
        if factory:
            return factory()
        
        raise ValueError(f"Unknown swarm: {name}")
    
    def list_swarms(self) -> Dict[str, int]:
        """List all available swarms with agent counts."""
        return {
            "ingestion": 6,
            "research": 4,
            "narrative": 4,
            "trial_prep": 4,
            "forensics": 5,
            "context_engine": 4,
            "legal_research": 5,
            "drafting": 6,
            "asset_hunter": 5,
            "simulation": 5,
        }
    
    def total_agents(self) -> int:
        """Get total agent count across all swarms."""
        return sum(self.list_swarms().values())


def get_swarm_registry() -> SwarmRegistry:
    """Get the swarm registry singleton."""
    return SwarmRegistry.get_instance()


def get_swarm(name: str):
    """Convenience function to get a swarm by name."""
    return get_swarm_registry().get_swarm(name)
