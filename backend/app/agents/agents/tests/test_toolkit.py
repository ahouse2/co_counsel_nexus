from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.toolkit import EvaluationHarness, FixtureSet, PromptPack

BASE_DIR = Path(__file__).resolve().parents[1]


def _load_pack(name: str) -> PromptPack:
    return PromptPack.load(BASE_DIR / "toolkit" / "packs" / f"{name}.yaml")


def _load_fixture(name: str) -> FixtureSet:
    return FixtureSet.load(BASE_DIR / "toolkit" / "fixtures" / f"{name}.json")


def test_prompt_pack_render_requires_variables() -> None:
    pack = _load_pack("research_baseline")
    template = pack.template("case_synthesis")
    with pytest.raises(ValueError):
        template.render(question="What happened?", context="")
    rendered = template.render(question="Test", context="Ctx", references="Ref")
    assert all({"role", "content"} <= message.keys() for message in rendered)


def test_fixture_set_shuffle_is_deterministic() -> None:
    fixtures = _load_fixture("research_baseline")
    order_one = [case.case_id for case in fixtures.iter_cases(shuffle=True)]
    order_two = [case.case_id for case in fixtures.iter_cases(shuffle=True)]
    assert order_one == order_two


def _successful_research_agent(case, template) -> Dict[str, object]:
    prompts = template.render(question=case.question, context=case.context, references="ref")
    assert prompts  # ensures template executed
    if case.case_id == "acme_beacon_timeline":
        answer = (
            "January 2023 board approval documented in doc-001. "
            "March 2023 regulatory response committed in doc-003. "
            "April 2023 integration window defined by doc-002."
        )
    elif case.case_id == "acme_financial_synergies":
        answer = (
            "$12M run-rate savings expected post Q4 2023 consolidation while DPIA remediation remains open."
        )
    else:
        answer = case.question
    citations: List[Dict[str, object]] = [
        {"docId": doc.doc_id, "span": doc.snippets[0] if doc.snippets else ""}
        for doc in case.documents
    ]
    telemetry = {"duration_ms": 900, "privileged_docs": 0, "qa_average": 8.6}
    return {"answer": answer, "citations": citations, "telemetry": telemetry}


def test_evaluation_harness_passes_research_agent() -> None:
    pack = _load_pack("research_baseline")
    fixtures = _load_fixture("research_baseline")
    harness = EvaluationHarness(pack, fixtures, template_id="case_synthesis")
    result = harness.run(_successful_research_agent)
    assert result.success_rate() == 1.0
    assert not result.failures()
    for case_result in result.results:
        assert case_result.success is True
        assert case_result.metrics["assert_overall"] is True
        assert case_result.prompts


def _failing_compliance_agent(case, template) -> Dict[str, object]:
    template.render(question=case.question, context=case.context, references="ref")
    # Deliberately omit citations and privilege signal to trigger metric failures.
    return {"answer": "Summary without detail", "citations": [], "telemetry": {"duration_ms": 400}}


def test_evaluation_harness_flags_compliance_failures() -> None:
    pack = _load_pack("compliance_baseline")
    fixtures = _load_fixture("compliance_baseline")
    harness = EvaluationHarness(pack, fixtures, template_id="privilege_review")
    result = harness.run(_failing_compliance_agent)
    assert result.success_rate() < 1.0
    failures = result.failures()
    assert failures
    failure = failures[0]
    assert failure.metrics["assert_minimum_citations"] is False
    assert failure.metrics["assert_overall"] is False
