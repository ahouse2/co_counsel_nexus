name: "Spec — <Initiative Name>"
version: <version>
status: draft
owners:
  - "<Tech Lead>"
reviewers:
  - "<Product Lead>"
  - "<QA Lead>"

> **PRP Navigation:** [Base](./PRP_base_template.md) · [Planning](./PRP_planning_template.md) · [Spec](./PRP_spec_template.md) · [Tasks](./PRP_tasks_template.md) · [Pre-PRP Plan](../PRE_PRP_PLAN.md) · [ACE Execution Guide](../EXECUTION_GUIDE_ACE.md) · [Task List Master](../TASK_LIST_MASTER.md) · [Rubric](../RUBRIC.md)

## Overview
- Objective: <concise problem statement>
- Target users / personas: <list>
- Success measures: <KPIs>

## Functional Requirements
- Feature A: <description + acceptance criteria>
- Feature B: <description + acceptance criteria>

## API & Interface Contracts
- REST / GraphQL: <endpoint tables>
- Events / PubSub: <topic schema>
- CLI / Automation: <commands>

## Data Model
- Entities: <tables or documents with key fields>
- Relationships: <graph edges, constraints>
- Storage policies: <retention, encryption>

## Agent & Workflow Design
- Roles: <agents, triggers, hand-offs>
- Memory: <short-term/long-term state handling>
- Observability: <traces, logs, metrics>

## Non-Functional Requirements
- Performance: <latency, throughput>
- Reliability: <SLOs, failover>
- Security & Compliance: <authn/z, auditing, regulatory>
- Accessibility & UX: <requirements>

## Validation Strategy
- Test plan: <unit, integration, scenario>
- Tooling: <automation harnesses, datasets>
- Entry / exit criteria: <definition of ready/done>

## Risks & Mitigations
- <risk>: <mitigation>

## Appendices
- Glossary
- Open questions / decisions log
