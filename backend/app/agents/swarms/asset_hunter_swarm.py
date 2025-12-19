"""
Asset Hunter Swarm - Autonomous asset discovery and financial forensics with KG integration.

Agents:
1. EntitySearchAgent - Finds related entities (companies, trusts, people)
2. PropertySearchAgent - Searches for real property holdings
3. CryptoTracingAgent - Traces cryptocurrency transactions
4. FinancialDiscrepancyAgent - Identifies lifestyle/income discrepancies
5. SchemeDetectorAgent - Detects asset hiding schemes
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
class AssetAgentResult:
    agent_name: str
    success: bool
    output: Dict[str, Any]
    findings_count: int = 0


class AssetAgent:
    """Base class for asset hunter agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def investigate(self, target: str, context: Dict[str, Any]) -> AssetAgentResult:
        raise NotImplementedError


class EntitySearchAgent(AssetAgent):
    """Agent 1: Finds related entities."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "EntitySearchAgent")
    
    async def investigate(self, target: str, context: Dict[str, Any]) -> AssetAgentResult:
        try:
            case_id = context.get("case_id", "default")
            
            # Query KG for related entities
            entity_query = """
            MATCH (t:Entity {name: $target})-[r]-(related:Entity)
            RETURN related.name as name, related.type as type,
                   type(r) as relationship
            LIMIT 20
            """
            entities = await self.kg_service.run_cypher_query(entity_query, {"target": target})
            
            # Use LLM to analyze connections
            prompt = f"""Analyze this target for asset hiding through entity structures.

TARGET: {target}

KNOWN ENTITIES:
{chr(10).join([f"- {e.get('name')} ({e.get('type')}) - {e.get('relationship')}" for e in (entities or [])[:10]])}

Look for:
1. Shell companies
2. Trusts and LLCs
3. Nominee arrangements
4. Family transfers

Return JSON:
{{
    "related_entities": [{{"name": "...", "type": "...", "suspicion_level": "high|medium|low", "reason": "..."}}],
    "patterns_detected": ["pattern1"],
    "recommended_actions": ["action1"]
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return AssetAgentResult(
                    agent_name=self.name,
                    success=True,
                    output=data,
                    findings_count=len(data.get("related_entities", []))
                )
            
            return AssetAgentResult(self.name, False, {"error": "Parse failed"}, 0)
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return AssetAgentResult(self.name, False, {"error": str(e)}, 0)


class PropertySearchAgent(AssetAgent):
    """Agent 2: Searches for real property holdings."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "PropertySearchAgent")
    
    async def investigate(self, target: str, context: Dict[str, Any]) -> AssetAgentResult:
        try:
            # Query KG for property records
            property_query = """
            MATCH (e:Entity {name: $target})-[:OWNS|OWNED|TRANSFERRED]->(p:Property)
            RETURN p.address as address, p.value as value, p.type as type,
                   p.acquisition_date as acquired
            """
            properties = await self.kg_service.run_cypher_query(property_query, {"target": target})
            
            return AssetAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "properties": properties or [],
                    "total_value": sum([p.get("value", 0) for p in (properties or []) if isinstance(p.get("value"), (int, float))]),
                    "search_sources": ["KnowledgeGraph"]
                },
                findings_count=len(properties or [])
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return AssetAgentResult(self.name, False, {"error": str(e)}, 0)


class CryptoTracingAgent(AssetAgent):
    """Agent 3: Traces cryptocurrency transactions."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "CryptoTracingAgent")
    
    async def investigate(self, target: str, context: Dict[str, Any]) -> AssetAgentResult:
        try:
            case_id = context.get("case_id", "default")
            
            # Query KG for crypto addresses
            crypto_query = """
            MATCH (e:Entity)-[:HAS_WALLET]->(w:CryptoWallet)
            WHERE e.name CONTAINS $target OR e.case_id = $case_id
            RETURN w.address as address, w.blockchain as chain, w.balance as balance
            """
            wallets = await self.kg_service.run_cypher_query(crypto_query, {
                "target": target, "case_id": case_id
            })
            
            results = {
                "wallets_found": wallets or [],
                "blockchains": list(set([w.get("chain", "unknown") for w in (wallets or [])])),
                "total_balance": sum([w.get("balance", 0) for w in (wallets or []) if isinstance(w.get("balance"), (int, float))])
            }
            
            return AssetAgentResult(
                agent_name=self.name,
                success=True,
                output=results,
                findings_count=len(wallets or [])
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return AssetAgentResult(self.name, False, {"error": str(e)}, 0)


class FinancialDiscrepancyAgent(AssetAgent):
    """Agent 4: Identifies lifestyle/income discrepancies."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "FinancialDiscrepancyAgent")
    
    async def investigate(self, target: str, context: Dict[str, Any]) -> AssetAgentResult:
        try:
            # Gather financial data from KG
            financial_query = """
            MATCH (e:Entity {name: $target})-[:HAS_INCOME|HAS_EXPENSE|HAS_ASSET]->(f)
            RETURN labels(f)[0] as type, f.amount as amount, f.description as description
            """
            financials = await self.kg_service.run_cypher_query(financial_query, {"target": target})
            
            # Analyze with LLM
            prompt = f"""Analyze this financial data for income/lifestyle discrepancies.

TARGET: {target}

FINANCIAL DATA:
{chr(10).join([f"- {f.get('type')}: ${f.get('amount', 0):,.2f} - {f.get('description', '')}" for f in (financials or [])[:15]])}

Identify:
1. Income vs spending gaps
2. Unexplained wealth
3. Hidden income sources
4. Lavish lifestyle inconsistent with declared income

Return JSON:
{{
    "discrepancies": [{{"type": "...", "description": "...", "estimated_gap": 0}}],
    "red_flags": ["flag1"],
    "risk_score": 0.0-1.0
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return AssetAgentResult(self.name, True, data, len(data.get("discrepancies", [])))
            
            return AssetAgentResult(self.name, True, {"discrepancies": [], "risk_score": 0}, 0)
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return AssetAgentResult(self.name, False, {"error": str(e)}, 0)


class SchemeDetectorAgent(AssetAgent):
    """Agent 5: Detects asset hiding schemes."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "SchemeDetectorAgent")
    
    async def investigate(self, target: str, context: Dict[str, Any]) -> AssetAgentResult:
        try:
            entities = context.get("entities", {}).get("related_entities", [])
            properties = context.get("properties", {}).get("properties", [])
            discrepancies = context.get("discrepancies", {}).get("discrepancies", [])
            
            # Known scheme patterns
            schemes = [
                {"name": "Trust Scheme", "indicators": ["trust", "beneficiary", "trustee"]},
                {"name": "Shell Company", "indicators": ["llc", "inc", "offshore", "delaware"]},
                {"name": "Nominee Ownership", "indicators": ["family member", "employee", "relative"]},
                {"name": "Fraudulent Transfer", "indicators": ["recent transfer", "no consideration", "insider"]}
            ]
            
            detected_schemes = []
            
            # Check entities for scheme patterns
            for entity in entities:
                entity_name = entity.get("name", "").lower()
                for scheme in schemes:
                    if any(ind in entity_name for ind in scheme["indicators"]):
                        detected_schemes.append({
                            "scheme": scheme["name"],
                            "entity": entity.get("name"),
                            "indicators_matched": [ind for ind in scheme["indicators"] if ind in entity_name]
                        })
            
            return AssetAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "detected_schemes": detected_schemes,
                    "scheme_count": len(detected_schemes),
                    "risk_level": "high" if len(detected_schemes) > 2 else "medium" if detected_schemes else "low"
                },
                findings_count=len(detected_schemes)
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return AssetAgentResult(self.name, False, {"error": str(e)}, 0)


# ═══════════════════════════════════════════════════════════════════════════
# ASSET HUNTER SWARM
# ═══════════════════════════════════════════════════════════════════════════

class AssetHunterSwarm:
    """
    Full asset hunting swarm with 5 agents.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.entity_search = EntitySearchAgent(self.llm_service, self.kg_service)
        self.property_search = PropertySearchAgent(self.llm_service, self.kg_service)
        self.crypto_tracing = CryptoTracingAgent(self.llm_service, self.kg_service)
        self.discrepancy_detector = FinancialDiscrepancyAgent(self.llm_service, self.kg_service)
        self.scheme_detector = SchemeDetectorAgent(self.llm_service, self.kg_service)
        
        logger.info("AssetHunterSwarm initialized with 5 agents")
    
    async def investigate(self, target: str, case_id: str) -> Dict[str, Any]:
        """Run full asset investigation."""
        context = {"case_id": case_id}
        
        # Stage 1: Entity and property search (parallel)
        logger.info(f"[AssetHunterSwarm] Investigating target: {target}")
        
        entity_task = self.entity_search.investigate(target, context)
        property_task = self.property_search.investigate(target, context)
        crypto_task = self.crypto_tracing.investigate(target, context)
        
        entity_result, property_result, crypto_result = await asyncio.gather(
            entity_task, property_task, crypto_task
        )
        
        context["entities"] = entity_result.output
        context["properties"] = property_result.output
        context["crypto"] = crypto_result.output
        
        # Stage 2: Discrepancy analysis
        logger.info(f"[AssetHunterSwarm] Analyzing discrepancies")
        discrepancy_result = await self.discrepancy_detector.investigate(target, context)
        context["discrepancies"] = discrepancy_result.output
        
        # Stage 3: Scheme detection
        logger.info(f"[AssetHunterSwarm] Detecting schemes")
        scheme_result = await self.scheme_detector.investigate(target, context)
        
        # Store findings in KG
        total_findings = sum([
            entity_result.findings_count,
            property_result.findings_count,
            crypto_result.findings_count,
            discrepancy_result.findings_count,
            scheme_result.findings_count
        ])
        
        store_query = """
        MERGE (i:Investigation {target: $target, case_id: $case_id})
        SET i.total_findings = $findings,
            i.risk_level = $risk,
            i.completed_at = datetime()
        """
        await self.kg_service.run_cypher_query(store_query, {
            "target": target,
            "case_id": case_id,
            "findings": total_findings,
            "risk": scheme_result.output.get("risk_level", "unknown")
        })
        
        return {
            "target": target,
            "case_id": case_id,
            "entities": entity_result.output,
            "properties": property_result.output,
            "crypto": crypto_result.output,
            "discrepancies": discrepancy_result.output,
            "schemes": scheme_result.output,
            "total_findings": total_findings
        }


# Factory
_asset_hunter_swarm: Optional[AssetHunterSwarm] = None

def get_asset_hunter_swarm() -> AssetHunterSwarm:
    global _asset_hunter_swarm
    if _asset_hunter_swarm is None:
        _asset_hunter_swarm = AssetHunterSwarm()
    return _asset_hunter_swarm
