
### Migration and Implementation Plan: Co-Counsel Agentic Framework

This plan outlines the necessary steps to adapt and integrate the agent teams and tools from the `toolsnteams_previous` directory into the production `MicrosoftAgentsOrchestrator` framework.

#### **Phase 1: Foundational Tool Development & Enhancement**

This phase focuses on creating and upgrading the core tools that all agent teams will rely on.

1.  **Task: Enhance Forensic Toolkit**
    *   **Description:** Overhaul the `ForensicTools` to create a production-grade, multi-faceted forensic analysis toolkit. This is a non-mocked, fully functional implementation.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/tools/forensic_tools.py` (New or Overwrite)
        *   `backend/app/services/web_scraper_service.py` (New)
    *   **Steps:**
        1.  **Web Scraper for Techniques:** Implement a `WebScraperService` capable of searching for and scraping articles, white papers, and forum discussions on PDF and image forensic analysis techniques.
        2.  **Knowledge Integration:** Create a `ForensicTechniqueIngestor` that uses the scraper to gather data and formats it for the system's Knowledge Graph.
        3.  **PDF Authenticity Tool:** Implement a `PDFAuthenticatorTool` that performs deep analysis on PDF internal structures (cross-reference tables, object streams, fonts, metadata history) to detect alterations, based on the scraped techniques. It will integrate with the `VerifyPDF` API as a secondary check.
        4.  **Image Authenticity Tool:** Implement an `ImageAuthenticatorTool` for various formats (`.png`, `.jpg`, `.heic`). It will perform Error Level Analysis (ELA), metadata (EXIF) analysis, and check for signs of cloning or splicing.
        5.  **Crypto Asset Tracker Tool:** Create a `CryptoTrackerTool` that uses regular expressions to find wallet addresses in documents. It will then use public blockchain APIs (e.g., Etherscan, Blockchair) to pull transaction histories and build relationship graphs between wallets.
        6.  **Financial Analysis Tool:** Refine the existing `FinancialAnalysisTool` to use `pandas` for statistical analysis (including Benford's Law) and an LLM for identifying anomalies and red flags in financial statements.

2.  **Task: Enhance Research Toolkit**
    *   **Description:** Build a comprehensive legal and general research toolkit with dedicated API clients and web scrapers for the specified resources.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/tools/research_tools.py` (New or Overwrite)
        *   `backend/app/services/api_clients/courtlistener_client.py` (New)
        *   `backend/app/services/api_clients/govinfo_client.py` (New)
        *   `backend/app/services/web_scrapers/california_codes_scraper.py` (New)
        *   `backend/app/services/web_scrapers/ecfr_scraper.py` (New)
    *   **Steps:**
        1.  **CourtListener/Case.Law Client:** Build a robust API client for the CourtListener and Case.Law APIs.
        2.  **GovInfo API Client:** Build a client for the `api.govinfo.gov` endpoint to search and retrieve US Code.
        3.  **Statute Scrapers:** Implement dedicated scrapers for the California Legislative Information and eCFR websites, as they lack APIs. These scrapers must be resilient to website structure changes.
        4.  **General Web Scraper:** Create a general-purpose `WebScraperTool` that can be directed by agents to find information on legal history, evidence law, and judicial analytics from specified sources (e.g., Trellis, university sites).
        5.  **Research Summarizer:** Create a `ResearchSummarizerTool` that uses an LLM to synthesize findings from all research sources into a coherent report.

3.  **Task: Develop Timeline, Presentation, and Trial HUD Toolkit**
    *   **Description:** Create the backend tools necessary to manage the interactive timeline and in-court presentation system.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/tools/presentation_tools.py` (New)
        *   `backend/app/services/timeline_service.py` (New)
        *   `backend/app/api/timeline.py` (Modify)
        *   `backend/app/api/presentation.py` (New)
    *   **Steps:**
        1.  **Timeline Service:** Develop a `TimelineService` that manages a chronological list of case events. Each event can be linked to evidence, documents, and citations.
        2.  **Timeline Tool:** Create a `TimelineTool` for agents to add, remove, and analyze events in the timeline.
        3.  **Exhibit Management Tool:** Create an `ExhibitTool` that allows agents to designate documents or media as exhibits, assign them numbers, and prepare them for presentation.
        4.  **Presentation State Tool:** Develop a `PresentationStateTool` that manages the state of the "Trial HUD," including the current script step, the active exhibit, and communication channels for sharing with external parties.
        5.  **API Endpoints:** Expose all these functionalities through secure FastAPI endpoints for the frontend to consume.

4.  **Task: Design and Implement the Agentic Testing Harness**
    *   **Description:** Build a testing suite that allows for the programmatic execution and evaluation of agent teams.
    *   **Files to Create/Modify:**
        *   `backend/app/testing_harness/harness.py` (New)
        *   `backend/app/testing_harness/scenarios/` (New Directory)
        *   `backend/app/api/testing.py` (New)
    *   **Steps:**
        1.  **Harness Service:** Create a `TestingHarnessService` that can load a test scenario (e.g., a specific prompt and a set of expected outcomes).
        2.  **Agent Invoker:** The service will invoke the specified agent team with the scenario's prompt.
        3.  **Output Evaluator:** The service will compare the agent team's final output against the scenario's expected outcomes (e.g., keyword matching, citation count, schema validation).
        4.  **API for Scenarios:** Create an API endpoint for the `Prompt_and_Scenario_Engineer_Lead` to define, manage, and run these test scenarios.

#### **Phase 2: Core Agent Team Implementation**

This phase focuses on building the primary legal, forensic, and data-processing teams.

1.  **Task: Implement the `DocumentIngestionCrew`**
    *   **Description:** Build the agent team responsible for the entire document ingestion pipeline.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/teams/document_ingestion.py` (New)
    *   **Steps:**
        1.  **Define Agents:** Create `AgentDefinition`s for the `Supervisor`, `Primary/Backup Preprocessor`, `Primary/Backup Indexer`, `Primary/Backup KG Builder`, and `Primary/Backup Summarizer`.
        2.  **Define QA Squad:** Add the `ValidatorQA`, `CriticQA`, and `RefinementQA` agents to the end of the workflow.
        3.  **Construct Team Graph:** In `build_document_ingestion_team`, define the workflow where a document is preprocessed, indexed, added to the KG, and summarized, followed by the full QA process.

2.  **Task: Implement the `ForensicAnalysisCrew`**
    *   **Description:** Build the team for deep forensic analysis of evidence.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/teams/forensic_analysis.py` (New)
    *   **Steps:**
        1.  **Define Agents:** Create `AgentDefinition`s for the `Forensics_Team_Lead` (Supervisor), `Primary/Backup PDF Authenticity Analyst`, `Primary/Backup Image Authenticity Analyst`, `Primary/Backup Crypto Asset Tracker`, and `Primary/Backup Forensic Accountant`.
        2.  **Define QA Squad:** Add the three QA agents, led by the `forensic_documents_qa_coordinator_agent`.
        3.  **Construct Team Graph:** The lead agent delegates analysis tasks based on document type. The results are aggregated and then passed through the QA process. The lead will first use the web scraper to gather and standardize techniques before analysis begins.

3.  **Task: Implement the `LegalResearchCrew`**
    *   **Description:** Build the team responsible for all legal and factual research.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/teams/legal_research.py` (New)
    *   **Steps:**
        1.  **Define Agents:** Create `AgentDefinition`s for the `research_coordinator_integrator_agent` (Supervisor), and Primary/Backup versions of `case_law_research_agent`, `statute_regulation_research_agent`, `procedure_court_rules_agent`, `evidence_law_expert_agent`, and `legal_history_context_agent`.
        2.  **Define QA Squad:** Add the three QA agents.
        3.  **Construct Team Graph:** The coordinator agent breaks down the research request and delegates sub-tasks to the specialized research agents. It then synthesizes their findings into a single report, which is then passed to the QA squad.

4.  **Task: Implement the `LitigationSupportCrew`**
    *   **Description:** Build the core strategic team that formulates the theory of the case.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/teams/litigation_support.py` (New)
    *   **Steps:**
        1.  **Define Agents:** Create `AgentDefinition`s for all the new roles: `lead_Counsel_Strategist_Agent` (Supervisor), `Finder_of_Fact`, `Devil's_Advocate`, `Timeline_Event_Coordinator`, `Finder_of_Law`, `Motion_Drafting_Agent`, and `Litigation_Training_Coach_Agent`.
        2.  **Define QA Squad:** The `Legal_Strategy_Reviewer_Senior_Counsel_Agent` will act as the lead QA, supplemented by the standard `CriticQA` and `RefinementQA`.
        3.  **Construct Team Graph:** This will be a complex, collaborative graph. The `lead_Counsel_Strategist_Agent` will coordinate the activities of the fact-finders and law-finders, use the `Devil's_Advocate` to test the emerging theory, and then delegate drafting and training tasks.

#### **Phase 3: Support and Meta-Team Implementation**

This phase focuses on the teams that support the core legal work and the overall system.

1.  **Task: Implement the `SoftwareDevelopmentCrew`**
    *   **Description:** Build the internal "Dev Team" responsible for maintaining and extending the system itself.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/teams/software_development.py` (New)
    *   **Steps:**
        1.  This team will be integrated with the existing `dev_agent` API. The agents (`Software_Architect`, `Front_End_Dev_UI_Agent`, `Back_End_Dev_Toolsmith_Agent`) will be defined to handle tasks submitted through the `/dev-agent/propose` endpoint.
        2.  The `QA_Test_Engineer_Agent` will be responsible for running the Agentic Testing Harness developed in Phase 1.

2.  **Task: Implement the `AI_QA_Oversight_Committee`**
    *   **Description:** Implement the meta-level QA committee that audits the entire agentic system. This team will operate asynchronously.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/teams/ai_qa_oversight.py` (New)
        *   `backend/app/services/qa_oversight_service.py` (New)
    *   **Steps:**
        1.  **Create Service:** The `QAOversightService` will run on a schedule (e.g., every hour). It will read the telemetry and memory logs from all other agent runs.
        2.  **Define Agents:** Define the agents for this committee: `AI_Behavior_Analyst_Lead`, `Prompt_and_Scenario_Engineer_Lead`, `Memory_and_State_Auditor_lead`, and `Safety_and_Escalation_Review_Lead`.
        3.  **Construct Team Graph:** The service will feed the logs to the `AI_Behavior_Analyst_Lead`, who delegates analysis tasks. The `Prompt_and_Scenario_Engineer_Lead` will use the findings to create new test scenarios for the Testing Harness. The `Memory_and_State_Auditor_lead` will specifically check for session drift and bias. The `Safety_and_Escalation_Review_Lead` will flag high-risk outputs for human review.
        4.  **Architect Role:** The `QA_Architect` will be a high-level configuration that defines the overall strategy, but not an active agent in the runtime loop.

#### **Phase 4: Integration and Finalization**

1.  **Task: Finalize Orchestrator Integration**
    *   **Description:** Update the main `MicrosoftAgentsOrchestrator` to include all new teams and provide a mechanism for selecting the correct team for a given task.
    *   **Files to Create/Modify:**
        *   `backend/app/agents/runner.py` (Modify)
    *   **Steps:**
        1.  Instantiate all new tools and teams.
        2.  Implement a "master router" agent or a simple routing logic in the `run` method that looks at the user's prompt and directs it to the most appropriate team (e.g., if the prompt contains "draft a motion," route to `LitigationSupportCrew`).

2.  **Task: Documentation and Configuration**
    *   **Description:** Update all relevant documentation and configuration files.
    *   **Files to Create/Modify:**
        *   `backend/app/config.py` (Modify)
        *   `docs/architecture/agentic_systems.md` (New)
        *   `README.md` (Modify)
    *   **Steps:**
        1.  Add all new API keys, URLs, and other settings to the `Settings` class.
        2.  Create a new architecture document that describes the full agentic framework, including all teams, their roles, and their interaction patterns.
        3.  Update the main project README to reflect the new capabilities.
