# PRP Co-Counsel Review Run — Analysis Blueprint (2025-10-31)

## 0. Mission Definition
- 0.1. Objective
  - 0.1.1. Re-evaluate Co-Counsel MVP PRP against live repository state
  - 0.1.2. Produce rubric-scored QA assessment with remediation roadmap
- 0.2. Deliverables
  - 0.2.1. Structured run log following PRP Analyze template
  - 0.2.2. Rubric table (10–15 categories, scored 0–10)
  - 0.2.3. Updated stewardship log entry in root `AGENTS.md`
  - 0.2.4. Final narrative summary with citations

## 1. Discovery Phase
- 1.1. Artifact Enumeration
  - 1.1.1. Inspect `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/PRP_CoCounsel_MSAgents_LlamaIndex_Swarms_spec.md`
  - 1.1.2. Map dependent specs (tasks, planning, execution guides)
  - 1.1.3. Catalogue backend implementation modules (`backend/app/**`)
- 1.2. Constraint Gathering
  - 1.2.1. Review root `AGENTS.md` for stewardship + ACE requirements
  - 1.2.2. Identify absence/presence of nested `AGENTS.md`
  - 1.2.3. Note operational expectations (no placeholder logic, thorough verification)
- 1.3. Tooling Prep
  - 1.3.1. Ensure access to `rg`, `sed`, `find` for inspection
  - 1.3.2. Confirm no prohibited commands (`ls -R`, `grep -R`)
  - 1.3.3. Prepare to capture citations for final summary

## 2. Analysis Phase
- 2.1. PRP Deep Dive
  - 2.1.1. Parse API requirements (ingest, query, timeline, graph, forensics)
  - 2.1.2. Record non-functional expectations (security, telemetry, ACE traces)
  - 2.1.3. Trace storage + agent orchestration mandates
- 2.2. Implementation Evaluation
  - 2.2.1. Audit FastAPI endpoints in `backend/app/main.py`
  - 2.2.2. Inspect services (`ingestion`, `retrieval`, `timeline`, `graph`, `forensics`, `vector`)
  - 2.2.3. Verify supporting modules (storage, utils, config) for completeness
  - 2.2.4. Note runtime blockers (missing modules, import errors, stubbed paths)
- 2.3. Gap Mapping
  - 2.3.1. Compare implemented behaviour vs PRP acceptance criteria
  - 2.3.2. Enumerate compliance/security shortfalls
  - 2.3.3. Capture telemetry/testing coverage gaps

## 3. Documentation Phase
- 3.1. Run Log Composition
  - 3.1.1. Populate PRP Analyze template within `build_logs/`
  - 3.1.2. Timestamp actions in UTC, list operators + environment
  - 3.1.3. Provide evidence references for each issue
- 3.2. Rubric Synthesis
  - 3.2.1. Define 12–14 evaluation categories spanning functionality, NFRs, ops
  - 3.2.2. Assign 0–10 scores with concise justification
  - 3.2.3. Articulate remediation requirements for achieving 10/10 per category
- 3.3. Stewardship Update
  - 3.3.1. Append chain-of-stewardship entry to root `AGENTS.md`
  - 3.3.2. Include files touched, tests executed, rubric average

## 4. Quality Assurance Phase
- 4.1. Self-Review Loop
  - 4.1.1. First pass: verify accuracy of findings vs source files
  - 4.1.2. Second pass: ensure rubric + remediation align with PRP scope
  - 4.1.3. Third pass: confirm template completeness, citation coverage
- 4.2. Consistency Checks
  - 4.2.1. Run `git status` to confirm intended file set
  - 4.2.2. Validate Markdown formatting + numbering

## 5. Delivery Phase
- 5.1. Final Outputs
  - 5.1.1. Present QA review in assistant response with rubric + remediation
  - 5.1.2. Cite sources in summary per instructions
  - 5.1.3. Declare tests executed (if any) using mandated emoji notation
- 5.2. Post-Delivery Notes
  - 5.2.1. Highlight unresolved risks for follow-up agents
  - 5.2.2. Recommend next validation cycle timing

