# Agentic Systems Architecture

This document outlines the architecture of the Co-Counsel application's agentic systems, detailing the various agent teams, their roles, and how they interact within the Microsoft Agents Framework SDK.

## Core Principles

*   **Modularity:** Each agent team is designed as a modular unit with a specific focus.
*   **Redundancy:** Key agents within each team have primary and backup counterparts to ensure fault tolerance.
*   **Three-Step QA:** Every team's output undergoes a rigorous three-step Quality Assurance process (Validation, Critique, Refinement) to ensure accuracy, quality, and compliance.
*   **Supervisor-led Workflow:** Each team is led by a Supervisor agent responsible for task delegation, workflow orchestration (both inside the team and to the master orchestration unit), and managing redundancy.
*   **Tool-driven:** Agents leverage a rich set of specialized tools to perform their tasks, ensuring non-mocked, production-ready, intelligent, and near-autonomous functionality.
*   **Asynchronous Oversight:** A dedicated AI QA Oversight Committee operates asynchronously to monitor and improve the overall agentic system's performance and safety.

## Agent Teams Overview

The Co-Counsel application features several specialized agent teams, each designed to handle a distinct aspect of legal work.

### 1. DocumentIngestionCrew

**Role:** Responsible for the entire document ingestion pipeline, from preprocessing to knowledge graph integration and summarization.

**Key Agents:**
*   **DocumentIngestionSupervisor:** Oversees the ingestion process.
*   **DocumentIngestionPreprocessor (x2-5) (Primary/Backup):** Handles initial OCR/ LLM vision, categorizing, cleaning, and initial structuring.
*   **ContentIndexingEmbedder (Primary/Backup):** Indexes content and generates embeddings.
*   **KnowledgeGraphBuilder (Primary/Backup):** Extracts entities/relationships and updates the Knowledge Graph.
*   **DatabaseQueryAgent (Primary/Backup):** Queries databases for context.
*   **DocumentSummarizer (Primary/Backup):** Generates document summaries.
*   **DataIntegrityQAIngestionQA (Lead QA):** Leads the QA process for ingestion.
*   **ValidatorQA, CriticQA, RefinementQA:** Standard 3-step QA.

**Workflow:** Documents are preprocessed, categorized, indexed, integrated into the KG, and summarized, followed by a comprehensive QA process.

### 2. ForensicAnalysisCrew

**Role:** Performs deep forensic analysis on digital evidence (PDFs, images, financial data, cryptocurrency transactions) to detect tampering and extract insights.

**Key Agents:**
*   **ForensicAnalysisSupervisor:** Oversees forensic tasks.
*   **DocumentAuthenticityAnalyst (Primary/Backup):** Analyzes PDFs and images for authenticity, validating internal structures and metadata, as well as standard forgery detection.
*   **EvidenceIntegrityAgent (Primary/Backup):** Ensures integrity of digital evidence.
*   **ForensicMediaAnalyst (Primary/Backup):** Analyzes various media files.
*   **ForensicAccountant (Primary/Backup):** Performs financial analysis.
*   **ForensicCryptocurrencyAssetTracker (Primary/Backup):** Tracks crypto transactions and attributes wallets.
*   **ForensicDataAnalyst (Primary/Backup):** General data analysis.
*   **ForensicDocumentsQACoordinator (Lead QA):** Leads QA for document forensics.
*   **ForensicFinanceQAReviewer (Lead QA):** Leads QA for financial forensics.
*   **ValidatorQA, CriticQA, RefinementQA:** Standard 3-step QA.

**Workflow:** Supervisor delegates analysis based on evidence type. Results are aggregated and undergo specialized QA.

### 3. LegalResearchCrew

**Role:** Conducts comprehensive legal and factual research using various APIs and web scraping tools.

**Key Agents:**
*   **ResearchCoordinatorIntegrator (Supervisor):** Coordinates research tasks and integrates findings.
*   **CaseLawResearcher (Primary/Backup):** Researches case law (CourtListener, Case.law).
*   **StatuteRegulationResearcher (Primary/Backup):** Researches statutes and regulations both state (selected by user during case creation) and federal (GovInfo, CA Codes, ECFR).
*   **ProcedureCourtRulesAgent (Primary/Backup):** Researches court rules (web scraping).
*   **EvidenceLawExpert (Primary/Backup):** Provides expertise on evidence law (web scraping).
*   **LegalHistoryContextAgent (Primary/Backup):** Provides legislative historical context (web scraping).
*   **ValidatorQA, CriticQA, RefinementQA:** Standard 3-step QA.

**Workflow:** Coordinator delegates research sub-tasks, synthesizes findings, and then passes through QA.

### 4. LitigationSupportCrew

**Role:** The core strategic team responsible for formulating the theory of the case, drafting motions, and preparing for litigation.

**Key Agents:**
*   **LeadCounselStrategist (Supervisor):** Formulates case theory, cross-references resources.
*   **StrategistFinderOfFact (Primary/Backup):** Identifies factual elements from the Knowledge Graph.
*   **StrategistDevilsAdvocate (Primary/Backup):** Critiques factual conclusions.
*   **StrategistTimelineEventCoordinator (Primary/Backup):** Ensures chronological correctness using the Timeline Tool, and uses the tool to construct timelines.
*   **StrategistFinderOfLaw (Primary/Backup):** Integrates legal doctrine from research.
*   **MotionDraftingAgent (Primary/Backup):** Drafts legal motions.
*   **LitigationTrainingCoach (Primary/Backup):** Provides mock court simulations.
*   **LegalStrategyReviewerSeniorCounsel (Lead QA):** Reviews overall legal strategy.
*   **ValidatorQA, CriticQA, RefinementQA:** Standard 3-step QA.

**Workflow:** Strategist coordinates fact and law finding, critiques, drafting, and simulation, all reviewed by senior counsel QA.

### 5. SoftwareDevelopmentCrew

**Role:** The internal development team responsible for maintaining, extending, and improving the Co-Counsel application itself.

**Key Agents:**
*   **DevTeamLead (Supervisor):** Coordinates development tasks.
*   **SoftwareArchitect:** Designs technical solutions.
*   **FrontEndDevUIAgent (Primary/Backup):** Develops UI and fixes front-end issues.
*   **BackEndDevToolsmithAgent (Primary/Backup):** Develops backend tools and fixes issues.
*   **QATestEngineer (Primary/Backup):** Performs QA and testing using the Agentic Testing Harness.
*   **ValidatorQA, CriticQA, RefinementQA:** Standard 3-step QA.

**Workflow:** Lead delegates tasks to developers, who then pass their work to QA for testing and review.

### 6. AI_QA_Oversight_Committee

**Role:** A meta-level, asynchronous committee that audits the entire agentic system for behavior, prompt engineering, memory, and safety.

**Key Agents:**
*   **AIBehaviorAnalystLead:** Analyzes agent decision paths and output rationale.
*   **PromptScenarioEngineerLead:** Crafts structured, edge-case, and adversarial prompts for testing.
*   **MemoryStateAuditorLead:** Monitors agent memory and state transitions for drift, leakage, or bias.
*   **SafetyEscalationReviewLead:** Reviews high-risk decisions and oversees escalation to Human-in-the-Loop (HITL).
*   **QAArchitectAgenticSystemsQALEAD:** Designs overall QA strategy (strategic role, not active agent).
*   **ValidatorQA, CriticQA, RefinementQA:** Standard 3-step QA for the committee's own findings.

**Workflow:** Triggered asynchronously by the `QAOversightService`, which feeds logs, traces, and memory data. Leads analyze data, generate new test scenarios, audit memory, and flag safety concerns.

### 7. Board_of_Supervisor

**Role:** Meta level supervisory panel of agents, responsible for cross-system orchestration and communication from individual team supervisors and communication to the Co-Counsel Chat Agent.

**Key Agents:**
*   **OversightBoard:** Oversees the overall orchestration between the team leads and the relay agent, accepting communication requests from the various team leads on behalf of the RelayAgent when the RelayAgent is unavailable or busy with a task, and then feeds communications to the RelayAgent when available. Also accepts communications directly from the AI_QA_Oversight_Committee on behalf of the Board, and relays communications to and from the ChairmanoftheBoard in hose cases. 
*   **RelayAgent:** Relays communication to and from individual team leads or supervisors to the Board.
*   **ChairManoftheBoard:** Responsible for making any executive decisions, after a deliberation and voting process by the Board of Supervisors. Any impactful decisions are run by the Co-Counsel-Chat Agent for addressing to the Human-in-the-Loop before implementation.
*   **VotingBoardMember:** Standard Board member, participates in deliberations and voting processes, as well as general oversight of the cross-system communication orchestration. Validator QA member.
*   **VotingBoardMember:** Standard Board member, participates in deliberations and voting processes, as well as general oversight of the cross-system communication orchestration. Acts as Critic QA Member.
*   **VotingBoardMember:** Standard Board member, participates in deliberations and voting processes, as well as general oversight of the cross-system communication orchestration. Acts as QA Refinement member.
*   **AgenticSystemsArchitect:** Designs overall orchestration strategy (strategic role, not active agent).

**Workflow:** Constantly monitors, architects, and supervises the overall operations and orchestration of the system's agentic teams, ensuring smooth operation.
In situations in which a decision needs to be made, the deliberation and voting process is triggered, leading to a deliberative process amongst the board members, and a subsequent vote to determine the direction and outcome, ensuring almost complete autonomy and self determination by the system. For high impact decisions, a Human-in-the-Loop request is triggered and sent to Co-Counsel-Chat-Agent for relay to the user for input. 

## Tooling Architecture

The agent teams leverage a comprehensive suite of specialized tools, many of which were developed in Phase 1.

*   **Forensic Tools:** `PDFAuthenticatorTool`, `ImageAuthenticatorTool`, `CryptoTrackerTool`, `FinancialAnalysisTool`.
*   **Research Tools:** `LegalResearchTool` (orchestrates `CourtListenerClient`, `CaseLawClient`, `GovInfoClient`, `CaliforniaCodesScraper`, `ECFRScraper`), `WebScraperTool`, `ResearchSummarizerTool`.
*   **Presentation Tools:** `TimelineTool`, `ExhibitManagerTool`, `PresentationStateTool`.
*   **Testing Harness:** `TestingHarnessService` (used by `TestExecutionTool`).
*   **QA Oversight Tools:** `AIBehaviorAnalysisTool`, `PromptScenarioEngineeringTool`, `MemoryStateAuditingTool`, `SafetyEscalationReviewTool`.
*   **General Purpose Tools:** `DocumentPreprocessingTool`, `ContentIndexingTool`, `KnowledgeGraphBuilderTool`, `DatabaseQueryTool`, `DocumentSummaryTool`, `KnowledgeGraphQueryTool`, `LLMDraftingTool`, `SimulationTool`.

## Orchestration and Routing

The `MicrosoftAgentsOrchestrator` dynamically routes incoming user questions to the most appropriate agent team based on keyword analysis and intent. This allows for a flexible and scalable system where specialized teams can be invoked as needed.

## Future Enhancements

*   **Advanced Routing:** Implement a more sophisticated routing mechanism using an LLM-based router for better intent recognition.
*   **Dynamic Tool Loading:** Allow agents to dynamically discover and load tools at runtime.
*   **Human-in-the-Loop (HITL) Integration:** Formalize HITL workflows for high-risk decisions flagged by the `Safety_and_Escalation_Review_Lead`.
*   **Observability and Telemetry:** Enhance telemetry collection and visualization for better monitoring of agent performance and interactions.
