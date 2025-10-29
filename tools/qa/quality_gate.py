"""Quality gate CLI enforcing coverage thresholds for backend test suites."""

from __future__ import annotations

import argparse
import io
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

import coverage
import pytest

DEFAULT_THRESHOLD = 85.0
DEFAULT_SOURCES = ["backend/app"]
DEFAULT_DATA_FILE = ".coverage-quality-gate"


@dataclass(slots=True)
class QualityGateResult:
    """Container describing pytest and coverage outcomes."""

    pytest_exit_code: int
    coverage_percent: float
    threshold_percent: float
    report_text: str = field(repr=False)

    @property
    def tests_passed(self) -> bool:
        """Return ``True`` when pytest exited successfully."""

        return self.pytest_exit_code == 0

    @property
    def coverage_passed(self) -> bool:
        """Return ``True`` when measured coverage meets or exceeds the threshold."""

        return self.coverage_percent >= self.threshold_percent

    @property
    def passed(self) -> bool:
        """Return ``True`` only if tests and coverage succeeded."""

        return self.tests_passed and self.coverage_passed

    def exit_code(self) -> int:
        """Compute exit code respecting pytest results and coverage thresholds."""

        if not self.tests_passed:
            return self.pytest_exit_code or 1
        if not self.coverage_passed:
            return 2
        return 0

    def to_dict(self) -> dict[str, object]:
        """Serialise result for JSON output."""

        return {
            "pytest_exit_code": self.pytest_exit_code,
            "coverage_percent": round(self.coverage_percent, 2),
            "threshold_percent": round(self.threshold_percent, 2),
            "tests_passed": self.tests_passed,
            "coverage_passed": self.coverage_passed,
            "passed": self.passed,
        }

    def summary(self) -> str:
        """Human-readable summary for stdout."""

        status = "PASSED" if self.passed else "FAILED"
        tests_status = "pass" if self.tests_passed else "fail"
        coverage_status = "pass" if self.coverage_passed else "fail"
        return (
            f"[quality-gate] overall={status}; tests={tests_status}; "
            f"coverage={self.coverage_percent:.2f}% (threshold {self.threshold_percent:.2f}%) [{coverage_status}]"
        )


class QualityGate:
    """Coordinator executing pytest under coverage measurement."""

    def __init__(
        self,
        coverage_factory: Callable[[], coverage.Coverage] | None = None,
        pytest_runner: Callable[[Sequence[str]], int] | None = None,
    ) -> None:
        self.coverage_factory = coverage_factory or self._default_coverage_factory
        self.pytest_runner = pytest_runner or self._default_pytest_runner

    @staticmethod
    def _default_pytest_runner(args: Sequence[str]) -> int:
        return pytest.main(list(args))

    @staticmethod
    def _default_coverage_factory() -> coverage.Coverage:
        return coverage.Coverage(branch=True, source=DEFAULT_SOURCES, data_file=DEFAULT_DATA_FILE)

    def run(self, pytest_args: Sequence[str] | None, threshold_percent: float) -> QualityGateResult:
        """Execute pytest with coverage and evaluate against ``threshold_percent``."""

        args = list(pytest_args or ["backend/tests", "-q"])
        cov = self.coverage_factory()
        cov.erase()
        buffer = io.StringIO()
        cov.start()
        try:
            exit_code = self.pytest_runner(args)
        finally:
            cov.stop()
            cov.save()
        coverage_percent = cov.report(skip_empty=True, file=buffer)
        return QualityGateResult(
            pytest_exit_code=exit_code,
            coverage_percent=coverage_percent,
            threshold_percent=threshold_percent,
            report_text=buffer.getvalue(),
        )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Build and parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Run backend quality gate with coverage enforcement.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum acceptable coverage percentage (default: 85.0).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path to write JSON summary for CI ingestion.",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Source package(s) to measure (default: backend/app).",
    )
    parser.add_argument(
        "--omit",
        action="append",
        default=None,
        help="Glob(s) to omit from coverage analysis.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to pytest (prefix with -- to avoid parsing).",
    )
    args = parser.parse_args(argv)
    if args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]
    if not args.pytest_args:
        args.pytest_args = ["backend/tests", "-q"]
    args.source = args.source or DEFAULT_SOURCES
    args.omit = args.omit or []
    return args


def build_coverage_factory(source: Iterable[str], omit: Iterable[str]) -> Callable[[], coverage.Coverage]:
    """Construct a lazy coverage factory with consistent configuration."""

    source_list = list(source)
    omit_list = list(omit)

    def _factory() -> coverage.Coverage:
        return coverage.Coverage(
            branch=True,
            source=source_list,
            omit=omit_list or None,
            data_file=DEFAULT_DATA_FILE,
        )

    return _factory


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for CLI execution."""

    args = parse_args(argv or sys.argv[1:])
    coverage_factory = build_coverage_factory(args.source, args.omit)
    gate = QualityGate(coverage_factory=coverage_factory)
    result = gate.run(args.pytest_args, args.threshold)
    print(result.summary())
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return result.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
