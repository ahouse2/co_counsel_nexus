
## Agent LLM Usage Audit - Complete Report

### Core Agents (All LLM-Powered ✓)

1. **StrategyTool** (`backend/app/agents/base_tools.py`)
   - ✅ LLM-Powered: Uses `llm_service.generate_text()` for dynamic plan generation
   - Generates 4-step execution plans tailored to user requests
   - Identifies key entities and legal concepts
   - Has heuristic fallback for reliability

2. **QAAgent** (`backend/app/agents/qa.py`)
   - ✅ LLM-Powered: Uses `llm_service.generate_text()` for rubric-based evaluation
   - Evaluates responses against 15 TRD rubric categories
   - Generates detailed assessment notes
   - Has heuristic scoring as robust fallback

3. **GraphManagerAgent** (`backend/app/agents/graph_manager.py`)
   - ✅ LLM-Powered: Uses `LLMTextToCypherChain` for text-to-Cypher generation
   - Converts natural language to graph queries
   - Falls back to `HeuristicTextToCypherChain` if no LLM provided

4. **ResearchTool** (`backend/app/agents/base_tools.py`)
   - ✅ Indirectly LLM-Powered: Delegates to `RetrievalService`
   - Uses `graph_agent` (which is LLM-powered)
   - **FIXED**: Now properly receives `retrieval_service` parameter

### Supporting Tools (LLM-Powered where applicable)

5. **ResearchSummarizerTool** (`backend/app/agents/tools/research_tools.py`)
   - ✅ LLM-Powered: Creates own `llm_service` via `create_llm_service()`
   - Summarizes research findings in context of queries

6. **DocumentSummaryTool** (`backend/app/agents/teams/document_ingestion.py`)
   - ✅ LLM-Powered: Uses `get_llm_service()` for document summarization

7. **LLMDraftingTool** (`backend/app/agents/teams/litigation_support.py`)
   - ✅ LLM-Powered (by name and purpose)

8. **EchoTool** (`backend/app/agents/echo_tool.py`)
   - ✅ LLM-Powered: Receives `llm_service` in constructor

### Non-LLM Tools (By Design)

9. **IngestionTool** (`backend/app/agents/base_tools.py`)
   - ⚙️ Utility: Audits document manifests (counts, types)
   - Does NOT need LLM - pure data aggregation

10. **ForensicsTool** (`backend/app/agents/base_tools.py`)
    - ⚙️ Utility: Loads and maps forensics artifacts
    - Does NOT need LLM - artifact retrieval and mapping

11. **LegalResearchTool** (`backend/app/agents/tools/research_tools.py`)
    - ⚙️ API Orchestrator: Coordinates legal research APIs
    - Does NOT need LLM - delegates to external services

12. **WebScraperTool** (`backend/app/agents/tools/research_tools.py`)
    - ⚙️ Utility: Web page content extraction
    - Does NOT need LLM - pure scraping

### Fixes Applied

1. **ResearchTool Parameter Fix**
   - Added `retrieval_service` parameter to `get_orchestrator()`
   - Made parameter optional with `get_retrieval_service()` default
   - Fixed instantiation to pass `retrieval_service` to `ResearchTool`

### Verification Status

✅ **All primary decision-making and reasoning agents are LLM-powered**
✅ **All content generation/summarization tools are LLM-powered**
✅ **Utility/data-processing tools appropriately use direct logic**

### LLM Service Architecture

The system uses two LLM service patterns:
1. **`create_llm_service()`** (`backend.ingestion.llama_index_factory`)
   - Returns `BaseLlmService` (synchronous)
   - Used by: StrategyTool, QAAgent, GraphManagerAgent, etc.

2. **`get_llm_service()`** (`backend.app.services.llm_service`)
   - Returns `LLMService` (asynchronous)
   - Used by: DocumentSummaryTool, etc.
   - Uses provider registry for flexible model selection
