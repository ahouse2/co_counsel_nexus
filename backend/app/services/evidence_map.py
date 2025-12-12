"""Evidence mapping service for visualizing evidence relationships and legal element connections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..services.graph import GraphService, get_graph_service
from ..services.llm_service import LLMService, get_llm_service


@dataclass
class EvidenceStrength:
    """Evidence strength assessment."""
    evidence_id: str
    score: float  # 0.0-1.0
    reliability: str  # "high", "medium", "low"
    reasoning: str
    factors: Dict[str, Any]


@dataclass
class EvidenceGap:
    """Identified gap in evidence chain."""
    gap_id: str
    description: str
    legal_element: str
    severity: str  # "critical", "important", "minor"
    suggested_evidence: List[str]


@dataclass
class ArgumentPath:
    """Path of evidence supporting a claim."""
    claim: str
    evidence_chain: List[Dict[str, Any]]
    strength_score: float
    weak_points: List[str]


class EvidenceMapService:
    """Service for evidence mapping and analysis."""

    def __init__(
        self,
        graph_service: Optional[GraphService] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        self.graph_service = graph_service or get_graph_service()
        self.llm_service = llm_service or get_llm_service()

    async def map_evidence_to_elements(self, case_id: str) -> Dict[str, Any]:
        """Map evidence to legal elements they support.
        
        Args:
            case_id: Case identifier
            
        Returns:
            Mapping of evidence to legal elements with relationships
        """
        # Query graph for all evidence nodes related to case
        evidence_query = """
        MATCH (d:Document {case_id: $case_id})
        OPTIONAL MATCH (d)-[r:MENTIONS]->(e:Entity)
        RETURN d, collect({entity: e, relation: type(r)}) as entities
        """
        
        # Execute query
        if self.graph_service.mode == "neo4j":
            with self.graph_service.driver.session() as session:
                result = session.run(evidence_query, case_id=case_id)
                evidence_nodes = []
                for record in result:
                    doc = record["d"]
                    entities = record["entities"]
                    evidence_nodes.append({
                        "id": doc["id"],
                        "title": doc.get("title", "Untitled"),
                        "type": doc.get("type", "document"),
                        "entities": entities,
                    })
        else:
            # Memory mode fallback
            evidence_nodes = []
            for node_id, node in self.graph_service._nodes.items():
                if node.type == "Document" and node.properties.get("case_id") == case_id:
                    evidence_nodes.append({
                        "id": node.id,
                        "title": node.properties.get("title", "Untitled"),
                        "type": node.type,
                        "entities": [],
                    })

        # Use LLM to identify legal elements each piece supports
        legal_elements = ["Duty", "Breach", "Causation", "Damages", "Intent", "Knowledge"]
        
        mapping = {}
        for evidence in evidence_nodes:
            prompt = f"""
            Analyze this evidence and identify which legal elements it supports.
            
            Evidence: {evidence['title']}
            Type: {evidence['type']}
            
            Legal Elements to consider: {', '.join(legal_elements)}
            
            Return a JSON object with:
            {{
                "supported_elements": [list of legal elements this evidence supports],
                "strength": "strong" | "moderate" | "weak",
                "reasoning": "brief explanation"
            }}
            """
            
            try:
                response = await self.llm_service.generate_text(prompt)
                # Parse JSON from response
                import json
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    mapping[evidence["id"]] = {
                        "evidence": evidence,
                        "legal_elements": data.get("supported_elements", []),
                        "strength": data.get("strength", "weak"),
                        "reasoning": data.get("reasoning", ""),
                    }
            except Exception as e:
                print(f"Error mapping evidence {evidence['id']}: {e}")
                mapping[evidence["id"]] = {
                    "evidence": evidence,
                    "legal_elements": [],
                    "strength": "unknown",
                    "reasoning": "Analysis failed",
                }

        return {
            "case_id": case_id,
            "evidence_count": len(evidence_nodes),
            "mapping": mapping,
            "legal_elements": legal_elements,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def calculate_evidence_strength(self, evidence_id: str) -> EvidenceStrength:
        """Calculate strength/reliability of a piece of evidence.
        
        Args:
            evidence_id: Evidence identifier
            
        Returns:
            Evidence strength assessment
        """
        # Retrieve evidence metadata
        evidence_node = self.graph_service._node_cache.get(evidence_id)
        if not evidence_node and self.graph_service.mode == "memory":
            evidence_node = self.graph_service._nodes.get(evidence_id)

        if not evidence_node:
            return EvidenceStrength(
                evidence_id=evidence_id,
                score=0.0,
                reliability="unknown",
                reasoning="Evidence not found",
                factors={},
            )

        # Analyze factors affecting strength
        factors = {
            "source_type": evidence_node.properties.get("type", "unknown"),
            "has_metadata": bool(evidence_node.properties.get("metadata")),
            "corroboration_count": 0,  # Would count related evidence
            "chain_of_custody": evidence_node.properties.get("chain_of_custody", False),
        }

        # Use LLM to assess reliability
        prompt = f"""
        Assess the reliability and strength of this evidence.
        
        Evidence ID: {evidence_id}
        Type: {factors['source_type']}
        Has Metadata: {factors['has_metadata']}
        Chain of Custody: {factors['chain_of_custody']}
        
        Consider:
        - Source credibility
        - Corroboration
        - Chain of custody
        - Potential challenges
        
        Return JSON:
        {{
            "score": 0.0-1.0,
            "reliability": "high" | "medium" | "low",
            "reasoning": "explanation"
        }}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return EvidenceStrength(
                    evidence_id=evidence_id,
                    score=float(data.get("score", 0.5)),
                    reliability=data.get("reliability", "medium"),
                    reasoning=data.get("reasoning", ""),
                    factors=factors,
                )
        except Exception as e:
            print(f"Error calculating strength for {evidence_id}: {e}")

        return EvidenceStrength(
            evidence_id=evidence_id,
            score=0.5,
            reliability="medium",
            reasoning="Default assessment",
            factors=factors,
        )

    async def find_evidence_gaps(
        self, case_id: str, legal_theory: str
    ) -> List[EvidenceGap]:
        """Identify gaps in evidence for a legal theory.
        
        Args:
            case_id: Case identifier
            legal_theory: Legal theory being pursued
            
        Returns:
            List of identified evidence gaps
        """
        # Get current evidence mapping
        mapping = await self.map_evidence_to_elements(case_id)

        # Analyze gaps using LLM
        prompt = f"""
        Analyze this case's evidence for gaps in supporting the legal theory.
        
        Legal Theory: {legal_theory}
        
        Current Evidence Coverage:
        {self._format_evidence_coverage(mapping)}
        
        Identify gaps where evidence is missing or weak. Return JSON:
        {{
            "gaps": [
                {{
                    "description": "what's missing",
                    "legal_element": "which element needs support",
                    "severity": "critical" | "important" | "minor",
                    "suggested_evidence": ["types of evidence that would fill gap"]
                }}
            ]
        }}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                gaps = []
                for gap_data in data.get("gaps", []):
                    gaps.append(EvidenceGap(
                        gap_id=f"gap::{uuid4().hex[:8]}",
                        description=gap_data.get("description", ""),
                        legal_element=gap_data.get("legal_element", ""),
                        severity=gap_data.get("severity", "minor"),
                        suggested_evidence=gap_data.get("suggested_evidence", []),
                    ))
                return gaps
        except Exception as e:
            print(f"Error finding gaps: {e}")

        return []

    async def generate_argument_path(
        self, case_id: str, claim: str
    ) -> ArgumentPath:
        """Generate evidence chain supporting a specific claim.
        
        Args:
            case_id: Case identifier
            claim: Claim to support
            
        Returns:
            Argument path with evidence chain
        """
        # Get evidence mapping
        mapping = await self.map_evidence_to_elements(case_id)

        # Use LLM to trace argument path
        prompt = f"""
        Trace the evidence chain that supports this claim.
        
        Claim: {claim}
        
        Available Evidence:
        {self._format_evidence_coverage(mapping)}
        
        Return JSON:
        {{
            "evidence_chain": [
                {{"evidence_id": "id", "contribution": "how it supports claim"}}
            ],
            "strength_score": 0.0-1.0,
            "weak_points": ["list of weaknesses in the chain"]
        }}
        """

        try:
            response = await self.llm_service.generate_text(prompt)
            import json
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return ArgumentPath(
                    claim=claim,
                    evidence_chain=data.get("evidence_chain", []),
                    strength_score=float(data.get("strength_score", 0.5)),
                    weak_points=data.get("weak_points", []),
                )
        except Exception as e:
            print(f"Error generating argument path: {e}")

        return ArgumentPath(
            claim=claim,
            evidence_chain=[],
            strength_score=0.0,
            weak_points=["Analysis failed"],
        )

    def _format_evidence_coverage(self, mapping: Dict[str, Any]) -> str:
        """Format evidence mapping for LLM prompts."""
        lines = []
        for evidence_id, data in mapping.get("mapping", {}).items():
            evidence = data["evidence"]
            elements = ", ".join(data["legal_elements"])
            lines.append(f"- {evidence['title']}: supports {elements} ({data['strength']})")
        return "\n".join(lines) if lines else "No evidence mapped yet"


def get_evidence_map_service() -> EvidenceMapService:
    """Get or create evidence map service instance."""
    return EvidenceMapService()
