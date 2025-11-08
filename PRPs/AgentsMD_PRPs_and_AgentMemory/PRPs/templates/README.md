# PRP Templates

The templates in this directory provide starting points for drafting or updating Product Requirements Packets (PRPs). Each file mirrors an officially maintained document in `../` and captures the canonical section ordering, terminology, and metadata expected in this repository.

## Available Templates

| Template | Purpose |
| --- | --- |
| `PRP_base_template.md` | Summarise the goal, scope, context, blueprint, validation, risks, and deliverables for a product slice. |
| `PRP_planning_template.md` | Translate the base into research focuses, executive summary, flows, architecture, technical specs, and backlog signals. |
| `PRP_spec_template.md` | Capture detailed system behaviours, APIs, data contracts, non-functional requirements, and compliance notes. |
| `PRP_tasks_template.md` | Break down the work into phases, swimlanes, deliverables, and acceptance gates aligned to the spec. |

## Usage Guidelines
1. Copy the relevant template next to the PRP variant you are authoring (e.g., duplicate it and rename to `PRP_NewInitiative_base.md`).
2. Replace bracketed guidance with project-specific content—do not leave placeholders behind.
3. Cross-link the resulting PRP with its sibling documents using the navigation snippet included in each template.
4. Keep supporting documents (e.g., `PRE_PRP_PLAN.md`, `EXECUTION_GUIDE_ACE.md`) updated to reflect new artefacts and validation workflows.

> _Note_: These templates are living documents. When the canonical PRPs evolve, update the templates to stay in sync.
