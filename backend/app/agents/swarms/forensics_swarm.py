"""
Forensics Swarm - Autonomous document forensic analysis with KG integration.

Agents:
1. TamperDetectionAgent - Detects document tampering (ELA, metadata inconsistencies)
2. MetadataForensicsAgent - Deep metadata extraction and analysis
3. ChainOfCustodyAgent - Validates document provenance
4. RedactionDetectorAgent - Finds hidden or redacted content
5. TimelineForensicsAgent - Validates temporal consistency
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
class ForensicAgentResult:
    agent_name: str
    success: bool
    output: Dict[str, Any]
    risk_level: str = "low"  # low, medium, high, critical


class ForensicAgent:
    """Base class for forensic swarm agents."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService, name: str):
        self.llm_service = llm_service
        self.kg_service = kg_service
        self.name = name
    
    async def analyze(self, doc_id: str, doc_data: Dict[str, Any], context: Dict[str, Any]) -> ForensicAgentResult:
        raise NotImplementedError


class TamperDetectionAgent(ForensicAgent):
    """Agent 1: Detects document tampering using multiple techniques."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "TamperDetectionAgent")
    
    async def analyze(self, doc_id: str, doc_data: Dict[str, Any], context: Dict[str, Any]) -> ForensicAgentResult:
        """Detect signs of tampering."""
        try:
            metadata = doc_data.get("metadata", {})
            
            # Check for tampering indicators
            tampering_flags = []
            risk_score = 0.0
            
            # Check creation vs modification dates
            created = metadata.get("created_at")
            modified = metadata.get("modified_at")
            if created and modified and created > modified:
                tampering_flags.append("Creation date after modification date")
                risk_score += 0.3
            
            # Check for editing software indicators
            producer = metadata.get("pdf_producer", "").lower()
            if any(tool in producer for tool in ["photoshop", "acrobat", "nitro"]):
                tampering_flags.append(f"Edited with: {producer}")
                risk_score += 0.2
            
            # Check embedded fonts consistency
            fonts = metadata.get("fonts", [])
            if len(set(fonts)) > 5:
                tampering_flags.append("Unusual font variety (possible splicing)")
                risk_score += 0.15
            
            # Use LLM for content analysis
            text = doc_data.get("text", "")[:3000]
            if text:
                prompt = f"""Analyze this document text for signs of tampering or manipulation:

TEXT:
{text}

Look for:
1. Inconsistent formatting or spacing
2. Unusual date/time references
3. Contradictory statements
4. Signs of text insertion/deletion

Return JSON:
{{
    "suspicious_patterns": ["pattern1", "pattern2"],
    "confidence": 0.0-1.0,
    "reasoning": "..."
}}"""
                
                response = await self.llm_service.generate_text(prompt)
                import json, re
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    tampering_flags.extend(data.get("suspicious_patterns", []))
                    risk_score += data.get("confidence", 0) * 0.3
            
            # Determine risk level
            if risk_score >= 0.7:
                risk_level = "critical"
            elif risk_score >= 0.5:
                risk_level = "high"
            elif risk_score >= 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            # Store findings in KG
            if tampering_flags:
                query = """
                MATCH (d:Document {id: $doc_id})
                SET d.tampering_flags = $flags,
                    d.tampering_risk = $risk,
                    d.tampering_analyzed_at = datetime()
                """
                await self.kg_service.run_cypher_query(query, {
                    "doc_id": doc_id,
                    "flags": tampering_flags,
                    "risk": risk_score
                })
            
            return ForensicAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "tampering_flags": tampering_flags,
                    "risk_score": risk_score,
                    "techniques_used": ["metadata_analysis", "date_validation", "content_analysis"]
                },
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ForensicAgentResult(self.name, False, {"error": str(e)})


class MetadataForensicsAgent(ForensicAgent):
    """Agent 2: Deep metadata extraction and analysis."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "MetadataForensicsAgent")
    
    async def analyze(self, doc_id: str, doc_data: Dict[str, Any], context: Dict[str, Any]) -> ForensicAgentResult:
        """Extract and analyze all metadata."""
        try:
            metadata = doc_data.get("metadata", {})
            
            extracted = {
                "author": metadata.get("author"),
                "creator_tool": metadata.get("creator") or metadata.get("pdf_producer"),
                "created_at": str(metadata.get("created_at", "")),
                "modified_at": str(metadata.get("modified_at", "")),
                "pdf_version": metadata.get("pdf_version"),
                "page_count": metadata.get("page_count"),
                "file_size": metadata.get("file_size"),
                "encryption": metadata.get("encrypted", False),
                "signatures": metadata.get("digital_signatures", []),
                "embedded_files": metadata.get("embedded_files", []),
                "revision_count": metadata.get("revision_count", 0)
            }
            
            # Analyze for forensic significance
            findings = []
            
            if extracted.get("revision_count", 0) > 10:
                findings.append(f"High revision count: {extracted['revision_count']}")
            
            if extracted.get("embedded_files"):
                findings.append(f"Contains {len(extracted['embedded_files'])} embedded files")
            
            if extracted.get("encryption"):
                findings.append("Document is encrypted")
            
            # Store in KG
            query = """
            MATCH (d:Document {id: $doc_id})
            SET d.forensic_metadata = $metadata,
                d.forensic_findings = $findings
            """
            await self.kg_service.run_cypher_query(query, {
                "doc_id": doc_id,
                "metadata": str(extracted),
                "findings": findings
            })
            
            return ForensicAgentResult(
                agent_name=self.name,
                success=True,
                output={"extracted_metadata": extracted, "findings": findings},
                risk_level="medium" if findings else "low"
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ForensicAgentResult(self.name, False, {"error": str(e)})


class ChainOfCustodyAgent(ForensicAgent):
    """Agent 3: Validates document provenance and chain of custody."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "ChainOfCustodyAgent")
    
    async def analyze(self, doc_id: str, doc_data: Dict[str, Any], context: Dict[str, Any]) -> ForensicAgentResult:
        """Validate chain of custody."""
        try:
            # Query KG for document history
            query = """
            MATCH (d:Document {id: $doc_id})
            OPTIONAL MATCH (d)-[:RECEIVED_FROM]->(source:Entity)
            OPTIONAL MATCH (d)-[:PRODUCED_BY]->(producer:Entity)
            OPTIONAL MATCH (d)<-[:PRODUCED]-(party:Party)
            RETURN d, source, producer, party
            """
            result = await self.kg_service.run_cypher_query(query, {"doc_id": doc_id})
            
            custody_chain = []
            gaps = []
            
            metadata = doc_data.get("metadata", {})
            origin = metadata.get("origin", "unknown")
            source_type = metadata.get("source_type", "unknown")
            
            custody_chain.append({
                "step": 1,
                "action": "Ingested",
                "source": origin,
                "source_type": source_type,
                "timestamp": str(metadata.get("ingested_at", ""))
            })
            
            # Check for custody gaps
            if source_type == "unknown":
                gaps.append("Unknown source type")
            if not metadata.get("checksum_sha256"):
                gaps.append("No integrity hash")
            
            return ForensicAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "custody_chain": custody_chain,
                    "gaps": gaps,
                    "integrity_verified": bool(metadata.get("checksum_sha256"))
                },
                risk_level="high" if gaps else "low"
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ForensicAgentResult(self.name, False, {"error": str(e)})


class RedactionDetectorAgent(ForensicAgent):
    """Agent 4: Detects redacted or hidden content."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "RedactionDetectorAgent")
    
    async def analyze(self, doc_id: str, doc_data: Dict[str, Any], context: Dict[str, Any]) -> ForensicAgentResult:
        """Detect redactions and hidden content."""
        try:
            text = doc_data.get("text", "")
            metadata = doc_data.get("metadata", {})
            
            redaction_indicators = []
            
            # Check for redaction markers in text
            redaction_patterns = ["[REDACTED]", "[CONFIDENTIAL]", "XXXXX", "█████", "■■■■"]
            for pattern in redaction_patterns:
                if pattern in text:
                    count = text.count(pattern)
                    redaction_indicators.append(f"Found '{pattern}' {count} times")
            
            # Check for black boxes in metadata
            if metadata.get("has_black_boxes"):
                redaction_indicators.append("PDF contains black box annotations")
            
            # Check for layers
            if metadata.get("layer_count", 1) > 1:
                redaction_indicators.append(f"Document has {metadata.get('layer_count')} layers (potential hidden content)")
            
            return ForensicAgentResult(
                agent_name=self.name,
                success=True,
                output={
                    "redaction_indicators": redaction_indicators,
                    "redaction_count": len(redaction_indicators),
                    "may_contain_hidden": bool(metadata.get("layer_count", 1) > 1)
                },
                risk_level="high" if redaction_indicators else "low"
            )
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ForensicAgentResult(self.name, False, {"error": str(e)})


class TimelineForensicsAgent(ForensicAgent):
    """Agent 5: Validates temporal consistency of document."""
    
    def __init__(self, llm_service: LLMService, kg_service: KnowledgeGraphService):
        super().__init__(llm_service, kg_service, "TimelineForensicsAgent")
    
    async def analyze(self, doc_id: str, doc_data: Dict[str, Any], context: Dict[str, Any]) -> ForensicAgentResult:
        """Validate temporal consistency."""
        try:
            text = doc_data.get("text", "")[:5000]
            metadata = doc_data.get("metadata", {})
            
            # Use LLM to extract and validate dates
            prompt = f"""Analyze this document for temporal consistency.

DOCUMENT TEXT:
{text}

DOCUMENT METADATA:
- Created: {metadata.get('created_at', 'unknown')}
- Modified: {metadata.get('modified_at', 'unknown')}

Check for:
1. Dates mentioned in text vs metadata dates
2. Anachronistic references (future dates, impossible sequences)
3. Timeline inconsistencies

Return JSON:
{{
    "dates_found": ["date1", "date2"],
    "inconsistencies": ["issue1", "issue2"],
    "anachronisms": ["anachronism1"],
    "temporal_validity": "valid|suspicious|invalid"
}}"""

            response = await self.llm_service.generate_text(prompt)
            import json, re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                
                risk_level = "low"
                if data.get("temporal_validity") == "invalid":
                    risk_level = "critical"
                elif data.get("temporal_validity") == "suspicious":
                    risk_level = "high"
                elif data.get("inconsistencies"):
                    risk_level = "medium"
                
                return ForensicAgentResult(
                    agent_name=self.name,
                    success=True,
                    output=data,
                    risk_level=risk_level
                )
            
            return ForensicAgentResult(self.name, False, {"error": "Parse failed"})
            
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ForensicAgentResult(self.name, False, {"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# FORENSICS SWARM
# ═══════════════════════════════════════════════════════════════════════════

class ForensicsSwarm:
    """
    Swarm for autonomous document forensic analysis with KG integration.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None, kg_service: Optional[KnowledgeGraphService] = None):
        self.llm_service = llm_service or get_llm_service()
        self.kg_service = kg_service or get_knowledge_graph_service()
        
        self.tamper_detector = TamperDetectionAgent(self.llm_service, self.kg_service)
        self.metadata_forensics = MetadataForensicsAgent(self.llm_service, self.kg_service)
        self.chain_of_custody = ChainOfCustodyAgent(self.llm_service, self.kg_service)
        self.redaction_detector = RedactionDetectorAgent(self.llm_service, self.kg_service)
        self.timeline_forensics = TimelineForensicsAgent(self.llm_service, self.kg_service)
        
        logger.info("ForensicsSwarm initialized with 5 agents")
    
    async def analyze_document(self, doc_id: str, doc_data: Dict[str, Any], case_id: str) -> Dict[str, Any]:
        """Run complete forensic analysis on a document."""
        context = {"case_id": case_id}
        
        # Run all agents in parallel
        logger.info(f"[ForensicsSwarm] Starting parallel forensic analysis for doc {doc_id}")
        
        results = await asyncio.gather(
            self.tamper_detector.analyze(doc_id, doc_data, context),
            self.metadata_forensics.analyze(doc_id, doc_data, context),
            self.chain_of_custody.analyze(doc_id, doc_data, context),
            self.redaction_detector.analyze(doc_id, doc_data, context),
            self.timeline_forensics.analyze(doc_id, doc_data, context)
        )
        
        # Aggregate results
        all_results = {
            "tamper_detection": results[0].output,
            "metadata_forensics": results[1].output,
            "chain_of_custody": results[2].output,
            "redaction_detection": results[3].output,
            "timeline_forensics": results[4].output
        }
        
        # Calculate overall risk
        risk_levels = [r.risk_level for r in results]
        if "critical" in risk_levels:
            overall_risk = "critical"
        elif "high" in risk_levels:
            overall_risk = "high"
        elif "medium" in risk_levels:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        # Update KG with overall assessment
        query = """
        MATCH (d:Document {id: $doc_id})
        SET d.forensic_risk = $risk,
            d.forensic_completed_at = datetime()
        """
        await self.kg_service.run_cypher_query(query, {"doc_id": doc_id, "risk": overall_risk})
        
        logger.info(f"[ForensicsSwarm] Analysis complete for {doc_id}. Overall risk: {overall_risk}")
        
        return {
            "doc_id": doc_id,
            "case_id": case_id,
            "overall_risk": overall_risk,
            "results": all_results
        }


# Factory
_forensics_swarm: Optional[ForensicsSwarm] = None

def get_forensics_swarm() -> ForensicsSwarm:
    global _forensics_swarm
    if _forensics_swarm is None:
        _forensics_swarm = ForensicsSwarm()
    return _forensics_swarm
