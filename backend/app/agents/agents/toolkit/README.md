# KnowledgeOps Agent Toolkit

The KnowledgeOps toolkit codifies reusable artefacts for onboarding research and compliance agents. It bundles prompt packs, deterministic fixture suites, and an evaluation harness so that new agents can be stood up with predictable baselines in less than a half day.

## Contents

| Path | Description |
| --- | --- |
| `prompt_packs.py` | Loader and renderer for YAML prompt packs with checksum validation. |
| `fixtures.py` | Deterministic fixture loader with RNG seeding and hash verification. |
| `evaluation.py` | Harness for executing agents against fixtures and computing rubric-aligned metrics. |
| `packs/` | Canonical prompt packs for research and compliance personas. |
| `fixtures/` | Curated fixture corpora aligned with PRP KnowledgeOps scenarios. |

## Adding a New Agent

1. **Author a prompt pack** in `agents/toolkit/packs/`:
   - Provide `meta` information (`name`, `version`, `agent_type`, `description`, maintainers).
   - Define one or more `prompts` with message templates. Variables must be explicitly enumerated under `inputs`.
   - Run `python -c "from agents.toolkit import PromptPack; PromptPack.load('path/to/pack.yaml')"` to validate structure and compute checksum.

2. **Create deterministic fixtures** in `agents/toolkit/fixtures/`:
   - Include realistic question/context pairs, document snippets, and expected assertions (contains/forbidden strings, citation counts, latency budgets, privilege thresholds).
   - Ensure every case has a stable `id`; the loader rejects duplicates and records a SHA-256 checksum for provenance.

3. **Exercise the evaluation harness**:
   ```python
   from agents.toolkit import EvaluationHarness, FixtureSet, PromptPack

   pack = PromptPack.load("agents/toolkit/packs/research_baseline.yaml")
   fixtures = FixtureSet.load("agents/toolkit/fixtures/research_baseline.json")
   harness = EvaluationHarness(pack, fixtures, template_id="case_synthesis")

   def agent(case, template):
       messages = template.render(
           question=case.question,
           context=case.context,
           references="\n\n".join(doc.title for doc in case.documents),
       )
       # Call out to your orchestrator here. Response schema documented below.
       return {
           "answer": "...",
           "citations": [{"docId": doc.doc_id, "span": doc.snippets[0]} for doc in case.documents],
           "telemetry": {"duration_ms": 950, "privileged_docs": 0},
       }

   result = harness.run(agent)
   print(result.to_summary())
   ```

4. **Interpret results**:
   - Each `CaseEvaluationResult.metrics` entry prefixed with `assert_` is a boolean gate.
   - `citation_density`, `latency_ms`, and `observed_privileged_documents` expose quantitative telemetry.
   - For CI integration, inspect `EvaluationSuiteResult.success_rate()` and `failures()`.

5. **Document onboarding steps**: capture agent-specific nuances (rate limits, compliance reviews) in the KnowledgeOps runbooks under `docs/AgentsMD_PRPs_and_AgentMemory/PRPs/`.

## Response Schema Expectations

The harness expects agent callables to return a mapping containing:

- `answer` *(str)* — natural language response.
- `citations` *(list)* — entries with `docId`/`document_id` and `span`.
- `telemetry` *(dict)* — includes `duration_ms`, `privileged_docs`, and optional `qa_average`.
- Optional `latency_ms` or `privileged_documents` overrides may be supplied for custom orchestrators.

These conventions align with the backend agents service, ensuring fixture evaluations mirror production execution.
