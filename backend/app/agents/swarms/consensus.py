"""
Consensus Mechanisms for Swarm Decision-Making.

Implements multiple strategies for reaching consensus among agents:
1. Majority Vote - Agents vote on discrete options
2. Weighted Average - Combine outputs with confidence weighting
3. Debate & Refine - Iterative discussion until agreement
4. Supervisor Decision - Designated lead makes final call

Each swarm can choose the consensus method appropriate for their task.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from backend.app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class ConsensusMethod(Enum):
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    DEBATE_AND_REFINE = "debate_and_refine"
    SUPERVISOR_DECISION = "supervisor_decision"


@dataclass
class AgentOutput:
    """Output from a single agent."""
    agent_name: str
    output: Any
    confidence: float = 1.0
    reasoning: str = ""


@dataclass
class ConsensusConfig:
    """Configuration for consensus process."""
    method: ConsensusMethod = ConsensusMethod.MAJORITY_VOTE
    min_agreement: float = 0.6  # 60% agreement required
    max_iterations: int = 3
    supervisor_agent: Optional[str] = None  # For supervisor method
    allow_dissent: bool = True


class ConsensusMechanism:
    """
    Handles consensus-building among multiple agent outputs.
    """
    
    def __init__(self, config: ConsensusConfig = None):
        self.config = config or ConsensusConfig()
        self.llm_service = get_llm_service()
    
    async def reach_consensus(
        self,
        agent_outputs: List[AgentOutput],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Reach consensus among agent outputs using configured method.
        
        Args:
            agent_outputs: List of outputs from individual agents
            context: Additional context for decision-making
            
        Returns:
            Consensus result with final_output, confidence, and metadata
        """
        if not agent_outputs:
            return {"final_output": None, "confidence": 0.0, "method": "none"}
        
        if len(agent_outputs) == 1:
            return {
                "final_output": agent_outputs[0].output,
                "confidence": agent_outputs[0].confidence,
                "method": "single_agent",
                "participating_agents": [agent_outputs[0].agent_name],
                "dissenting_agents": []
            }
        
        method = self.config.method
        
        if method == ConsensusMethod.MAJORITY_VOTE:
            return await self._majority_vote(agent_outputs)
        elif method == ConsensusMethod.WEIGHTED_AVERAGE:
            return await self._weighted_average(agent_outputs)
        elif method == ConsensusMethod.DEBATE_AND_REFINE:
            return await self._debate_and_refine(agent_outputs, context)
        elif method == ConsensusMethod.SUPERVISOR_DECISION:
            return await self._supervisor_decision(agent_outputs, context)
        else:
            return await self._majority_vote(agent_outputs)
    
    async def _majority_vote(self, outputs: List[AgentOutput]) -> Dict[str, Any]:
        """
        Majority vote consensus - agents vote on discrete options.
        
        Works best when outputs can be compared/hashed (strings, dicts with key fields).
        """
        votes = {}
        voters = {}
        
        for output in outputs:
            # Create a vote key from the output
            if isinstance(output.output, dict):
                # Use key fields for comparison
                key = str(output.output.get("decision") or output.output.get("result") or output.output)
            else:
                key = str(output.output)
            
            if key not in votes:
                votes[key] = 0
                voters[key] = []
            
            votes[key] += 1
            voters[key].append(output.agent_name)
        
        # Find majority
        total_votes = len(outputs)
        winning_key = max(votes.keys(), key=lambda k: votes[k])
        winning_votes = votes[winning_key]
        winning_agents = voters[winning_key]
        
        agreement = winning_votes / total_votes
        
        # Find dissenting agents
        all_agents = [o.agent_name for o in outputs]
        dissenting = [a for a in all_agents if a not in winning_agents]
        
        # Get the actual output object that won
        winning_output = None
        for output in outputs:
            key = str(output.output.get("decision") or output.output.get("result") or output.output) if isinstance(output.output, dict) else str(output.output)
            if key == winning_key:
                winning_output = output.output
                break
        
        return {
            "final_output": winning_output,
            "confidence": agreement,
            "method": "majority_vote",
            "votes": votes,
            "agreement": agreement,
            "participating_agents": winning_agents,
            "dissenting_agents": dissenting,
            "iterations": 1
        }
    
    async def _weighted_average(self, outputs: List[AgentOutput]) -> Dict[str, Any]:
        """
        Weighted average - combine outputs based on confidence scores.
        
        Works best for numerical or structured outputs that can be merged.
        """
        all_agents = [o.agent_name for o in outputs]
        total_weight = sum(o.confidence for o in outputs)
        
        if total_weight == 0:
            total_weight = len(outputs)
        
        # Try to merge outputs
        merged = {}
        
        for output in outputs:
            weight = output.confidence / total_weight
            
            if isinstance(output.output, dict):
                for key, value in output.output.items():
                    if key not in merged:
                        merged[key] = []
                    merged[key].append({"value": value, "weight": weight, "agent": output.agent_name})
        
        # Resolve each key
        final_output = {}
        for key, weighted_values in merged.items():
            # For numerical values, do weighted average
            # For others, take highest weighted value
            values = [wv["value"] for wv in weighted_values]
            weights = [wv["weight"] for wv in weighted_values]
            
            if all(isinstance(v, (int, float)) for v in values):
                final_output[key] = sum(v * w for v, w in zip(values, weights))
            else:
                # Take value with highest weight
                max_idx = weights.index(max(weights))
                final_output[key] = values[max_idx]
        
        avg_confidence = sum(o.confidence for o in outputs) / len(outputs)
        
        return {
            "final_output": final_output,
            "confidence": avg_confidence,
            "method": "weighted_average",
            "participating_agents": all_agents,
            "dissenting_agents": [],
            "iterations": 1
        }
    
    async def _debate_and_refine(self, outputs: List[AgentOutput], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Debate and refine - iterative refinement until agreement.
        
        Uses LLM to synthesize a consensus from multiple viewpoints.
        """
        all_agents = [o.agent_name for o in outputs]
        
        # Format outputs for LLM
        outputs_text = "\n\n".join([
            f"**{o.agent_name}** (confidence: {o.confidence:.0%}):\n{o.output}\nReasoning: {o.reasoning}"
            for o in outputs
        ])
        
        prompt = f"""You are a consensus-building facilitator. Multiple agents have provided different outputs.
Your job is to synthesize a single consensus output that incorporates the best elements from each.

AGENT OUTPUTS:
{outputs_text}

CONTEXT:
{context or 'None provided'}

Synthesize a consensus that:
1. Incorporates valid points from all agents
2. Resolves any contradictions
3. Produces a unified, high-quality result

Return JSON:
{{
    "consensus_output": <the synthesized result>,
    "incorporated_from": ["agent1", "agent2"],
    "resolved_contradictions": ["contradiction1"],
    "confidence": 0.0-1.0
}}"""

        try:
            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    "final_output": data.get("consensus_output"),
                    "confidence": data.get("confidence", 0.8),
                    "method": "debate_and_refine",
                    "incorporated_from": data.get("incorporated_from", all_agents),
                    "resolved_contradictions": data.get("resolved_contradictions", []),
                    "participating_agents": all_agents,
                    "dissenting_agents": [],
                    "iterations": 1
                }
        except Exception as e:
            logger.error(f"Debate consensus failed: {e}")
        
        # Fallback to majority vote
        return await self._majority_vote(outputs)
    
    async def _supervisor_decision(self, outputs: List[AgentOutput], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Supervisor decision - designated lead makes final call.
        
        Supervisor reviews all outputs and makes the decision.
        """
        supervisor = self.config.supervisor_agent
        all_agents = [o.agent_name for o in outputs]
        
        # Check if supervisor is among outputs
        supervisor_output = None
        other_outputs = []
        
        for output in outputs:
            if output.agent_name == supervisor:
                supervisor_output = output
            else:
                other_outputs.append(output)
        
        if supervisor_output:
            # Supervisor's output is the decision
            return {
                "final_output": supervisor_output.output,
                "confidence": supervisor_output.confidence,
                "method": "supervisor_decision",
                "supervisor": supervisor,
                "participating_agents": all_agents,
                "dissenting_agents": [o.agent_name for o in other_outputs if o.output != supervisor_output.output],
                "iterations": 1
            }
        
        # No supervisor output - use LLM as supervisor
        outputs_text = "\n".join([f"- {o.agent_name}: {o.output}" for o in outputs])
        
        prompt = f"""As the supervisor, review these agent outputs and make a final decision.

OUTPUTS:
{outputs_text}

Choose the best output or synthesize a better one. Return JSON:
{{
    "decision": <your decision>,
    "chosen_from": "agent_name" or "synthesized",
    "reasoning": "...",
    "confidence": 0.0-1.0
}}"""

        try:
            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    "final_output": data.get("decision"),
                    "confidence": data.get("confidence", 0.8),
                    "method": "supervisor_decision",
                    "supervisor": "LLM",
                    "chosen_from": data.get("chosen_from"),
                    "reasoning": data.get("reasoning"),
                    "participating_agents": all_agents,
                    "dissenting_agents": [],
                    "iterations": 1
                }
        except Exception as e:
            logger.error(f"Supervisor decision failed: {e}")
        
        # Fallback to majority
        return await self._majority_vote(outputs)


# Convenience function
async def reach_consensus(
    outputs: List[AgentOutput],
    method: ConsensusMethod = ConsensusMethod.MAJORITY_VOTE,
    config: ConsensusConfig = None
) -> Dict[str, Any]:
    """Quick consensus function."""
    if config is None:
        config = ConsensusConfig(method=method)
    mechanism = ConsensusMechanism(config)
    return await mechanism.reach_consensus(outputs)
