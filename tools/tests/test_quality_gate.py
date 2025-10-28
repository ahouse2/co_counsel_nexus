from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Sequence

import pytest

from tools.qa.quality_gate import (
    DEFAULT_DATA_FILE,
    DEFAULT_SOURCES,
    DEFAULT_THRESHOLD,
    QualityGate,
    QualityGateResult,
    build_coverage_factory,
    parse_args,
)


class DummyCoverage:
    def __init__(self, percent: float = 90.0) -> None:
        self.percent = percent
        self.started = False
        self.stopped = False
        self.saved = False
        self.erased = False
        self.report_requested = False

    def erase(self) -> None:
        self.erased = True

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def save(self) -> None:
        self.saved = True

    def report(self, skip_empty: bool = True, file=None) -> float:  # noqa: D401
        """Simulate coverage report."""

        self.report_requested = True
        if file is not None:
            file.write("dummy report\n")
        return self.percent


class DummyError(Exception):
    """Signal pytest runner failure for lifecycle verification."""


def _stub_pytest_runner(return_code: int) -> Callable[[Sequence[str]], int]:
    def _run(_: Sequence[str]) -> int:
        return return_code

    return _run


def test_quality_gate_passes_with_sufficient_coverage() -> None:
    fake_cov = DummyCoverage(percent=91.7)
    gate = QualityGate(coverage_factory=lambda: fake_cov, pytest_runner=_stub_pytest_runner(0))
    result = gate.run(["tests"], 85.0)
    assert isinstance(result, QualityGateResult)
    assert result.passed is True
    assert result.tests_passed is True
    assert result.coverage_passed is True
    assert result.exit_code() == 0
    assert fake_cov.started and fake_cov.stopped and fake_cov.saved and fake_cov.erased
    assert fake_cov.report_requested is True


def test_quality_gate_fails_when_pytest_fails() -> None:
    fake_cov = DummyCoverage(percent=95.0)
    gate = QualityGate(coverage_factory=lambda: fake_cov, pytest_runner=_stub_pytest_runner(5))
    result = gate.run(["tests"], 85.0)
    assert result.tests_passed is False
    assert result.passed is False
    assert result.exit_code() == 5


def test_quality_gate_fails_when_coverage_below_threshold() -> None:
    fake_cov = DummyCoverage(percent=72.4)
    gate = QualityGate(coverage_factory=lambda: fake_cov, pytest_runner=_stub_pytest_runner(0))
    result = gate.run(["tests"], 80.0)
    assert result.tests_passed is True
    assert result.coverage_passed is False
    assert result.passed is False
    assert result.exit_code() == 2


def test_quality_gate_stops_coverage_on_pytest_exception() -> None:
    fake_cov = DummyCoverage(percent=88.0)

    def _raise(_: Sequence[str]) -> int:
        raise DummyError("pytest crash")

    gate = QualityGate(coverage_factory=lambda: fake_cov, pytest_runner=_raise)
    with pytest.raises(DummyError):
        gate.run(["tests"], 85.0)
    assert fake_cov.started is True
    assert fake_cov.stopped is True
    assert fake_cov.saved is True


def test_result_summary_contains_threshold_and_percentages() -> None:
    result = QualityGateResult(pytest_exit_code=0, coverage_percent=91.234, threshold_percent=85.0, report_text="dummy")
    summary = result.summary()
    assert "overall=PASSED" in summary
    assert "coverage=91.23%" in summary
    assert "threshold 85.00%" in summary


def test_result_to_dict_rounds_percentages() -> None:
    result = QualityGateResult(pytest_exit_code=0, coverage_percent=89.876, threshold_percent=85.4321, report_text="")
    payload = result.to_dict()
    assert payload["coverage_percent"] == 89.88
    assert payload["threshold_percent"] == 85.43
    assert payload["passed"] is True


def test_parse_args_defaults_to_backend_suite() -> None:
    args = parse_args([])
    assert args.threshold == DEFAULT_THRESHOLD
    assert args.pytest_args == ["backend/tests", "-q"]
    assert args.source == DEFAULT_SOURCES
    assert args.omit == []


def test_parse_args_strips_remainder_separator(tmp_path: Path) -> None:
    args = parse_args(["--threshold", "90", "--json-output", str(tmp_path / "out.json"), "--", "backend/tests/test_api.py", "-k", "ingest"])
    assert args.threshold == 90
    assert args.pytest_args == ["backend/tests/test_api.py", "-k", "ingest"]
    assert args.json_output.name == "out.json"


def test_build_coverage_factory_produces_configured_instances(tmp_path: Path) -> None:
    source = ["backend/app", "backend/utils"]
    omit = ["*/tests/*"]
    factory = build_coverage_factory(source, omit)
    cov1 = factory()
    cov2 = factory()
    assert cov1 is not cov2
    assert cov1.config.source == source
    assert cov1.config.run_omit == omit
    assert cov1.config.data_file == DEFAULT_DATA_FILE
    assert cov2.config.source == source
    assert cov2.config.run_omit == omit


def test_json_output_structure(tmp_path: Path) -> None:
    target = tmp_path / "summary.json"
    result = QualityGateResult(pytest_exit_code=0, coverage_percent=97.3, threshold_percent=85.0, report_text="")
    data = json.dumps(result.to_dict())
    target.write_text(data)
    payload = json.loads(target.read_text())
    assert payload["passed"] is True
    assert payload["coverage_percent"] == 97.3
