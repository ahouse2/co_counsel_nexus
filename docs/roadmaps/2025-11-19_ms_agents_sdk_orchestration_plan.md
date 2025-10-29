# Microsoft Agents SDK Orchestration Integration Plan

## Phase 1 · Discovery and Architectural Alignment
- ### Objective 1.1 · Inventory Existing Agent Workflows
  - #### Task 1.1.1 · Catalogue current `AgentsService` responsibilities
    - ##### Note 1.1.1.1 · Document retry, circuit breaker, QA scoring, telemetry expectations
    - ##### Note 1.1.1.2 · Capture audit hooks and persistence requirements tied to `AgentMemoryStore`
  - #### Task 1.1.2 · Map TRD personas to SDK agents
    - ##### Note 1.1.2.1 · CoCounsel orchestrator
    - ##### Note 1.1.2.2 · Strategy planner
    - ##### Note 1.1.2.3 · Research analyst
    - ##### Note 1.1.2.4 · Ingestion steward
    - ##### Note 1.1.2.5 · QA adjudicator
- ### Objective 1.2 · Define Microsoft Agents SDK integration surface
  - #### Task 1.2.1 · Confirm session graph lifecycle semantics
    - ##### Note 1.2.1.1 · Node execution contracts and delegation events
    - ##### Note 1.2.1.2 · Shared memory schema for case thread state
  - #### Task 1.2.2 · Identify required tool adapters for existing services
    - ##### Note 1.2.2.1 · Retrieval tool wrapper (vector + graph fusion)
    - ##### Note 1.2.2.2 · Forensics artifact loader tool
    - ##### Note 1.2.2.3 · Timeline/ingestion health probes if triggered by agents

## Phase 2 · Implementation Blueprint
- ### Objective 2.1 · Scaffold `backend/app/agents/`
  - #### Task 2.1.1 · Create agent definitions module mirroring TRD roles
    - ##### Note 2.1.1.1 · Encode prompts/instructions for each persona
  - #### Task 2.1.2 · Build graph/session orchestration harness
    - ##### Note 2.1.2.1 · Support deterministic turn ordering + explicit hand-offs
    - ##### Note 2.1.2.2 · Preserve retry + circuit breaker semantics per component
- ### Objective 2.2 · Memory + Telemetry Infrastructure
  - #### Task 2.2.1 · Implement SDK-aligned memory abstractions backed by `AgentMemoryStore`
    - ##### Note 2.2.1.1 · Case-level state (question, plan, artifacts, QA)
    - ##### Note 2.2.1.2 · Turn transcript persistence
  - #### Task 2.2.2 · Telemetry envelope for multi-agent execution
    - ##### Note 2.2.2.1 · Track turn durations, retries, delegated roles

## Phase 3 · Service Refactor and Integration
- ### Objective 3.1 · Refactor `AgentsService`
  - #### Task 3.1.1 · Replace bespoke pipeline with SDK conversation runner
    - ##### Note 3.1.1.1 · Maintain audit hooks and workflow exception mapping
  - #### Task 3.1.2 · Expose orchestrator via FastAPI dependency graph
    - ##### Note 3.1.2.1 · Update `/agents/run` endpoint to call orchestrator session
- ### Objective 3.2 · Tool Registration
  - #### Task 3.2.1 · Wrap `RetrievalService`, `ForensicsService`, `IngestionService`
    - ##### Note 3.2.1.1 · Provide capability descriptors + telemetry metadata
  - #### Task 3.2.2 · Register QA evaluator as SDK tool invoked by QA agent
    - ##### Note 3.2.2.1 · Ensure QA rubric persists to memory + telemetry

## Phase 4 · Validation and Observability
- ### Objective 4.1 · Regression Coverage
  - #### Task 4.1.1 · Expand `backend/tests/test_agents.py`
    - ##### Note 4.1.1.1 · Cover multi-agent hand-offs + retries + telemetry emission
  - #### Task 4.1.2 · Validate shared memory persistence semantics
- ### Objective 4.2 · Documentation & Diagrams
  - #### Task 4.2.1 · Author docs under `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/`
    - ##### Note 4.2.1.1 · Include sequence diagrams for SDK graph + memory flow
    - ##### Note 4.2.1.2 · Summarize tool registry updates

## Phase 5 · Quality Gate & Review
- ### Objective 5.1 · Execute ACE trio review (Retriever → Planner → Critic)
  - #### Task 5.1.1 · Validate code twice end-to-end per quality discipline
    - ##### Note 5.1.1.1 · Confirm no TODOs, placeholders, or mock implementations remain
  - #### Task 5.1.2 · Prepare stewardship log entry + PR narrative
