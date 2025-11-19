from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

# Simple static status for agent teams; can be upgraded to dynamic runtime checks
TEAMS = [
    {
        "id": "document_ingestion",
        "name": "Document Ingestion Crew",
        "status": "Operational",
        "members": ["DocumentIngestionSupervisor", "DocumentPreprocessingTool", "ContentIndexingTool", "KnowledgeGraphBuilderTool"],
    },
    {
        "id": "forensics",
        "name": "Forensics / Chain",
        "status": "Operational",
        "members": ["ForensicAnalysisSupervisor", "DocumentAuthenticityAnalyst", "EvidenceIntegrityAgent"],
    },
    {
        "id": "legal_research",
        "name": "Legal Research Crew",
        "status": "Operational",
        "members": ["ResearchCoordinatorIntegrator", "CaseLawResearcher"],
    },
    {
        "id": "litigation_support",
        "name": "Litigation Support Crew",
        "status": "Operational",
        "members": ["LeadCounselStrategist", "StrategistFinderOfFact"],
    },
    {
        "id": "software_development",
        "name": "Software Development Crew",
        "status": "Operational",
        "members": ["DevTeamLead", "SoftwareArchitect", "FrontEndDevUIAgent"],
    },
    {
        "id": "ai_qa_oversight",
        "name": "AI QA Oversight Committee",
        "status": "Operational",
        "members": ["QAArchitectAgenticSystemsQALead", "AIBehaviorAnalystLead"],
    },
]

@router.get("/agents/status", tags=["Agents Status"], response_model=List[Dict[str, Any]])
async def get_agents_status():
    return TEAMS
