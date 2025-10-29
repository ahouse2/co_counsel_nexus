from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping

from .fixtures import FixtureCase, FixtureSet
from .prompt_packs import PromptPack, PromptTemplate

AgentCallable = Callable[[FixtureCase, PromptTemplate], Mapping[str, Any]]


@dataclass
class CaseEvaluationResult:
    case: FixtureCase
    success: bool
    metrics: Dict[str, Any]
    notes: List[str]
    response: Dict[str, Any]
    prompts: List[Dict[str, str]]


@dataclass
class EvaluationSuiteResult:
    pack: PromptPack
    fixture_set: FixtureSet
    template_id: str
    results: List[CaseEvaluationResult]

    def success_rate(self) -> float:
        if not self.results:
            return 0.0
        return round(
            sum(1 for result in self.results if result.success) / len(self.results),
            3,
        )

    def failures(self) -> List[CaseEvaluationResult]:
        return [result for result in self.results if not result.success]

    def to_summary(self) -> Dict[str, Any]:
        return {
            "prompt_pack": self.pack.name,
            "pack_checksum": self.pack.checksum,
            "fixture_set": self.fixture_set.name,
            "fixture_checksum": self.fixture_set.checksum,
            "template": self.template_id,
            "cases": len(self.results),
            "passed": len(self.results) - len(self.failures()),
            "failed": len(self.failures()),
            "success_rate": self.success_rate(),
        }


class EvaluationHarness:
    def __init__(self, pack: PromptPack, fixture_set: FixtureSet, template_id: str) -> None:
        self.pack = pack
        self.fixture_set = fixture_set
        self.template = pack.template(template_id)
        self.template_id = template_id

    def run(self, agent: AgentCallable, *, shuffle: bool = False) -> EvaluationSuiteResult:
        results: List[CaseEvaluationResult] = []
        for case in self.fixture_set.iter_cases(shuffle=shuffle):
            prompts = self._render_prompts(case)
            response_mapping = dict(agent(case, self.template))
            metrics, notes = self._evaluate_case(case, response_mapping)
            success = all(bool(value) for key, value in metrics.items() if key.startswith("assert_"))
            results.append(
                CaseEvaluationResult(
                    case=case,
                    success=success,
                    metrics=metrics,
                    notes=notes,
                    response=response_mapping,
                    prompts=prompts,
                )
            )
        return EvaluationSuiteResult(self.pack, self.fixture_set, self.template_id, results)

    def _render_prompts(self, case: FixtureCase) -> List[Dict[str, str]]:
        references = []
        for document in case.documents:
            first_snippet = document.snippets[0] if document.snippets else ""
            references.append(f"[{document.doc_id}] {document.title}\n{first_snippet}")
        reference_block = "\n\n".join(references)
        return self.template.render(question=case.question, context=case.context, references=reference_block)

    def _evaluate_case(self, case: FixtureCase, response: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
        expected = case.expected
        metrics: Dict[str, Any] = {}
        notes: List[str] = []

        answer = str(response.get("answer", ""))
        lowercase_answer = answer.lower()
        contains_terms = case.expected_strings("contains")
        forbidden_terms = case.expected_strings("forbidden")
        metrics["assert_contains_terms"] = all(term.lower() in lowercase_answer for term in contains_terms)
        metrics["assert_forbidden_absent"] = all(term.lower() not in lowercase_answer for term in forbidden_terms)
        if contains_terms:
            notes.append(f"Contains terms met: {metrics['assert_contains_terms']}")
        if forbidden_terms:
            notes.append(f"Forbidden terms absent: {metrics['assert_forbidden_absent']}")

        citations = list(response.get("citations", []))
        citation_ids = {str(item.get("docId") or item.get("document_id") or item.get("id")) for item in citations}
        minimum_citations = int(expected.get("minimum_citations", 0))
        metrics["observed_citations"] = len(citations)
        metrics["assert_minimum_citations"] = len(citations) >= minimum_citations
        required_documents = set(case.required_documents())
        metrics["assert_required_documents"] = required_documents.issubset(citation_ids or set())
        if required_documents:
            notes.append(
                "Required documents present: "
                f"{metrics['assert_required_documents']} ({sorted(required_documents)})"
            )

        privileged_budget = int(expected.get("max_privileged_documents", 0))
        telemetry = dict(response.get("telemetry", {}))
        observed_privileged = int(
            response.get("privileged_documents", telemetry.get("privileged_docs", 0))
        )
        metrics["observed_privileged_documents"] = observed_privileged
        metrics["assert_privileged_within_bounds"] = observed_privileged <= privileged_budget
        if privileged_budget:
            notes.append(
                "Privileged documents within bounds: "
                f"{metrics['assert_privileged_within_bounds']} (budget={privileged_budget})"
            )

        latency_budget = expected.get("max_latency_ms")
        observed_latency = float(
            response.get("latency_ms", telemetry.get("duration_ms", telemetry.get("total_duration_ms", 0.0)))
        )
        metrics["latency_ms"] = round(observed_latency, 2)
        if latency_budget is not None:
            metrics["assert_latency_within_bounds"] = observed_latency <= float(latency_budget)
            notes.append(
                "Latency within bounds: "
                f"{metrics['assert_latency_within_bounds']} (budget={latency_budget} ms)"
            )
        else:
            metrics["assert_latency_within_bounds"] = True

        citation_density = 0.0
        if answer:
            citation_density = len(citations) / max(len(answer.split()), 1)
        metrics["citation_density"] = round(citation_density, 3)
        if citations:
            notes.append(f"Citation density: {metrics['citation_density']}")

        sentiment = telemetry.get("qa_average")
        if sentiment is not None:
            notes.append(f"QA average score from agent telemetry: {sentiment}")

        metrics["assert_answer_present"] = bool(answer.strip())
        notes.append(f"Answer length: {len(answer)} characters")

        boolean_keys = [key for key in metrics if key.startswith("assert_")]
        if boolean_keys:
            metrics["assert_overall"] = all(bool(metrics[key]) for key in boolean_keys)
        else:
            metrics["assert_overall"] = True

        return metrics, notes


__all__ = [
    "EvaluationHarness",
    "EvaluationSuiteResult",
    "CaseEvaluationResult",
]
