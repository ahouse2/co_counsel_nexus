from __future__ import annotations
from typing import List, Dict, Any

# Assuming AgentDefinition and AgentTool are defined elsewhere in the framework
# For now, we'll use the simple classes defined in qa_agents.py
from backend.app.agents.definitions.qa_agents import AgentDefinition, AgentTool
from backend.app.agents.definitions.qa_agents import validator_qa_agent, critic_qa_agent, refinement_qa_agent

# Import the actual forensic tools implemented in Phase 1
from backend.app.agents.tools.forensic_tools import (
    PDFAuthenticatorTool,
    ImageAuthenticatorTool,
    CryptoTrackerTool,
    FinancialAnalysisTool
)
from backend.app.services.web_scraper_service import WebScraperService # For the QA coordinator to scrape techniques

# Instantiate the tools
pdf_authenticator_tool = PDFAuthenticatorTool()
image_authenticator_tool = ImageAuthenticatorTool()
crypto_tracker_tool = CryptoTrackerTool()
financial_analysis_tool = FinancialAnalysisTool()
web_scraper_service = WebScraperService() # Used by the QA coordinator

# Agent Definitions for Forensic Analysis Crew
# Primary Agents
document_authenticity_analyst_agent = AgentDefinition(
    name="DocumentAuthenticityAnalyst",
    role="Document Authenticity Analyst",
    description="Analyzes PDF and image documents for authenticity and signs of tampering.",
    tools=[pdf_authenticator_tool, image_authenticator_tool]
)

evidence_integrity_agent = AgentDefinition(
    name="EvidenceIntegrityAgent",
    role="Evidence Integrity Agent",
    description="Ensures the integrity of digital evidence, focusing on images and scanned documents.",
    tools=[image_authenticator_tool] # Can also use PDFAuthenticatorTool
)

forensic_media_analyst_agent = AgentDefinition(
    name="ForensicMediaAnalyst",
    role="Forensic Media Analyst",
    description="Analyzes various media files for forensic insights.",
    tools=[image_authenticator_tool] # Placeholder for more specific media tools
)

forensic_accountant_agent = AgentDefinition(
    name="ForensicAccountant",
    role="Forensic Accountant",
    description="Performs financial analysis to detect fraud and financial irregularities.",
    tools=[financial_analysis_tool]
)

forensic_cryptocurrency_asset_tracker_agent = AgentDefinition(
    name="ForensicCryptocurrencyAssetTracker",
    role="Forensic Cryptocurrency Asset Tracker",
    description="Tracks cryptocurrency transactions and attributes wallets across blockchains.",
    tools=[crypto_tracker_tool]
)

data_analyst_agent = AgentDefinition(
    name="ForensicDataAnalyst",
    role="Forensic Data Analyst",
    description="Performs general data analysis on forensic datasets.",
    tools=[financial_analysis_tool] # Can use other data analysis tools
)

# Backup Agents (for redundancy)
backup_document_authenticity_analyst_agent = AgentDefinition(
    name="BackupDocumentAuthenticityAnalyst",
    role="Backup Document Authenticity Analyst",
    description="Backup agent for analyzing PDF and image documents for authenticity.",
    tools=[pdf_authenticator_tool, image_authenticator_tool]
)

backup_evidence_integrity_agent = AgentDefinition(
    name="BackupEvidenceIntegrityAgent",
    role="Backup Evidence Integrity Agent",
    description="Backup agent for ensuring the integrity of digital evidence.",
    tools=[image_authenticator_tool]
)

backup_forensic_media_analyst_agent = AgentDefinition(
    name="BackupForensicMediaAnalyst",
    role="Backup Forensic Media Analyst",
    description="Backup agent for analyzing various media files for forensic insights.",
    tools=[image_authenticator_tool]
)

backup_forensic_accountant_agent = AgentDefinition(
    name="BackupForensicAccountant",
    role="Backup Forensic Accountant",
    description="Backup agent for performing financial analysis.",
    tools=[financial_analysis_tool]
)

backup_forensic_cryptocurrency_asset_tracker_agent = AgentDefinition(
    name="BackupForensicCryptocurrencyAssetTracker",
    role="Backup Forensic Cryptocurrency Asset Tracker",
    description="Backup agent for tracking cryptocurrency transactions and attributing wallets.",
    tools=[crypto_tracker_tool]
)

backup_data_analyst_agent = AgentDefinition(
    name="BackupForensicDataAnalyst",
    role="Backup Forensic Data Analyst",
    description="Backup agent for performing general data analysis on forensic datasets.",
    tools=[financial_analysis_tool]
)

# QA Lead for the crew
forensic_documents_qa_coordinator_agent = AgentDefinition(
    name="ForensicDocumentsQACoordinator",
    role="Forensic Documents QA Coordinator",
    description="Leads the QA for forensic analysis, ensuring proper techniques and standardization. Scrapes web for techniques.",
    tools=[WebScraperService()], # The QA coordinator will use the scraper to gather techniques
    delegates=[
        validator_qa_agent.name,
        critic_qa_agent.name,
        refinement_qa_agent.name
    ]
)

forensic_finance_qa_reviewer_agent = AgentDefinition(
    name="ForensicFinanceQAReviewer",
    role="Forensic Finance QA Reviewer",
    description="QA lead for financial analysis, ensuring accuracy and compliance.",
    delegates=[
        validator_qa_agent.name,
        critic_qa_agent.name,
        refinement_qa_agent.name
    ]
)

# Supervisor Agent for the crew
forensic_analysis_supervisor_agent = AgentDefinition(
    name="ForensicAnalysisSupervisor",
    role="Forensic Analysis Crew Supervisor",
    description="Oversees forensic analysis tasks, delegates to specialized analysts, and manages redundancy.",
    delegates=[
        document_authenticity_analyst_agent.name,
        backup_document_authenticity_analyst_agent.name,
        evidence_integrity_agent.name,
        backup_evidence_integrity_agent.name,
        forensic_media_analyst_agent.name,
        backup_forensic_media_analyst_agent.name,
        forensic_accountant_agent.name,
        backup_forensic_accountant_agent.name,
        forensic_cryptocurrency_asset_tracker_agent.name,
        backup_forensic_cryptocurrency_asset_tracker_agent.name,
        data_analyst_agent.name,
        backup_data_analyst_agent.name,
        forensic_documents_qa_coordinator_agent.name,
        forensic_finance_qa_reviewer_agent.name
    ]
)


def build_forensic_analysis_team(tools: List[AgentTool]) -> Dict[str, Any]:
    """
    Builds the Forensic Analysis Team with redundancy and a 3-step QA process.
    """
    all_agents = [
        forensic_analysis_supervisor_agent,
        document_authenticity_analyst_agent,
        backup_document_authenticity_analyst_agent,
        evidence_integrity_agent,
        backup_evidence_integrity_agent,
        forensic_media_analyst_agent,
        backup_forensic_media_analyst_agent,
        forensic_accountant_agent,
        backup_forensic_accountant_agent,
        forensic_cryptocurrency_asset_tracker_agent,
        backup_forensic_cryptocurrency_asset_tracker_agent,
        data_analyst_agent,
        backup_data_analyst_agent,
        forensic_documents_qa_coordinator_agent,
        forensic_finance_qa_reviewer_agent,
        validator_qa_agent,
        critic_qa_agent,
        refinement_qa_agent
    ]

    # Define the workflow (simplified representation)
    workflow = {
        "start": forensic_analysis_supervisor_agent.name,
        "tasks": [
            {
                "agent": forensic_analysis_supervisor_agent.name,
                "action": "delegate_analysis",
                "target": [
                    document_authenticity_analyst_agent.name,
                    evidence_integrity_agent.name,
                    forensic_media_analyst_agent.name,
                    forensic_accountant_agent.name,
                    forensic_cryptocurrency_asset_tracker_agent.name,
                    data_analyst_agent.name
                ]
            },
            {
                "agent": document_authenticity_analyst_agent.name,
                "action": "analyze_document",
                "target": forensic_documents_qa_coordinator_agent.name
            },
            {
                "agent": forensic_accountant_agent.name,
                "action": "analyze_financials",
                "target": forensic_finance_qa_reviewer_agent.name
            },
            {
                "agent": forensic_documents_qa_coordinator_agent.name,
                "action": "run_qa_process",
                "target": [validator_qa_agent.name, critic_qa_agent.name, refinement_qa_agent.name]
            },
            {
                "agent": forensic_finance_qa_reviewer_agent.name,
                "action": "run_qa_process",
                "target": [validator_qa_agent.name, critic_qa_agent.name, refinement_qa_agent.name]
            }
            # More complex delegation and aggregation logic would go here
        ]
    }

    return {
        "name": "ForensicAnalysisCrew",
        "agents": {agent.name: agent for agent in all_agents},
        "workflow": workflow,
        "tools": {tool.name: tool for tool in tools} # Pass relevant tools
    }