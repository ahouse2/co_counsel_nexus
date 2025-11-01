"""Pytest configuration shared across all test suites."""

from __future__ import annotations

from tests._oso_stub import ensure_oso_stub

ensure_oso_stub()
