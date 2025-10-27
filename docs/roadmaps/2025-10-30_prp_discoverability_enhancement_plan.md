# Roadmap — PRP Discoverability & Command Templates (2025-10-30)

## Vision
Deliver a self-documenting PRP workspace where contributors can navigate between strategy, specification, execution, and validation assets without friction, while providing structured run-analysis templates for rapid-development workflows.

## Outcomes
1. Navigation snippet binds together base, planning, spec, tasks, and supporting guides.
2. Contributors locate canonical templates exactly where onboarding describes.
3. Rapid-development experiments surface the PRP analyze run template from the command catalog.

## Phased Breakdown
### Phase A — Discovery Audit
- Confirm referenced paths in `ONBOARDING.md` and command catalog.
- Enumerate missing directories/files that block navigation (e.g., `PRPs/templates/`, `rapid-development/experimental/prp-analyze-run.md`).

### Phase B — Information Architecture Updates
- Introduce navigation banner across PRP core docs and supporting guides.
- Cross-link ACE execution guide and command catalog to new analysis template.
- Ensure supporting docs reference automation commands and templates.

### Phase C — Template Authoring
- Populate `PRPs/templates/` with base/planning/spec/tasks scaffolds reflecting current canonical structure.
- Document usage guidelines encouraging cross-link hygiene and removal of placeholders.

### Phase D — Rapid-Development Artifacts
- Create analysis template Markdown under `.codex/commands/rapid-development/experimental/`.
- Document usage instructions and context for ACE loops.

### Phase E — Repository Communication
- Update `ONBOARDING.md` to match directory reality and highlight new resources.
- Append Chain-of-Stewardship entry and ensure future contributors can trace changes.

## Decision Tree & Contingencies
- **If** templates already exist elsewhere ➜ **then** deprecate duplicate references and point onboarding to canonical location.
- **If** new navigation banner conflicts with future automation parsing ➜ **then** wrap snippet in blockquote for easy detection/removal.
- **If** command catalog expands ➜ **then** extend README with index referencing experimental commands (deferred after initial wiring).

## Acceptance Criteria
- All referenced paths in onboarding resolve to real files/directories.
- Each PRP core doc renders navigation banner linking to siblings + supporting materials.
- New `prp-analyze-run` template adopted in ACE execution guide and onboarding narrative.
- Templates directory contains README and four scaffold files mirroring canonical structure.
- No broken relative links detected by `tools/docs/validate_links.py` (manual run recommended post-merge).

## Notes & Follow-Ups
- Future enhancement: build automation to insert navigation snippet when generating new PRPs.
- Consider companion template for retrospective reporting once rapid-development commands mature.
