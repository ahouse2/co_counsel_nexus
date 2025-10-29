from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import reset_settings_cache
from backend.app.security.authz import Principal
from backend.app.telemetry.billing import (
    BILLING_PLANS,
    BillingEventType,
    export_customer_health,
    export_plan_catalogue,
    record_billing_event,
    reset_billing_registry,
)


def test_export_plan_catalogue_contains_pricing_and_support() -> None:
    catalogue = export_plan_catalogue()
    plan_ids = {plan["plan_id"] for plan in catalogue}
    assert {"community", "professional", "enterprise"}.issubset(plan_ids)
    enterprise = next(plan for plan in catalogue if plan["plan_id"] == "enterprise")
    assert enterprise["support_tier"] == "Premium"
    assert enterprise["overage_per_query_usd"] < BILLING_PLANS["professional"].overage_per_query_usd


def test_record_billing_event_accumulates_usage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    usage_path = tmp_path / "usage.json"
    monkeypatch.setenv("BILLING_USAGE_PATH", str(usage_path))
    reset_settings_cache()
    reset_billing_registry()

    principal = Principal(
        client_id="client-1",
        subject="user@example.com",
        tenant_id="tenant-alpha",
        roles={"CustomerSuccessManager"},
        token_roles=set(),
        certificate_roles=set(),
        scopes={"billing:read"},
    )

    record_billing_event(principal, BillingEventType.QUERY, attributes={"latency_ms": 42.0})
    record_billing_event(principal, BillingEventType.INGESTION, units=2, attributes={"gigabytes": 3.5})

    snapshot = export_customer_health()
    assert snapshot, "expected customer health snapshot to contain data"
    tenant = snapshot[0]
    assert tenant["tenant_id"] == "tenant-alpha"
    assert tenant["query_count"] == pytest.approx(1.0)
    assert tenant["ingestion_gb"] == pytest.approx(3.5)
    assert tenant["projected_monthly_cost"] >= BILLING_PLANS["community"].monthly_price_usd


def test_billing_endpoints_and_onboarding_flow(
    client: TestClient,
    auth_headers_factory,
) -> None:
    onboarding_payload = {
        "tenant_id": "tenant-beta",
        "organization": "Beta Legal Partners",
        "contact_name": "Sam Counsel",
        "contact_email": "sam@example.com",
        "seats": 12,
        "primary_use_case": "Litigation support",
        "departments": ["Litigation", "Investigations"],
        "estimated_matters_per_month": 40,
        "roi_baseline_hours_per_matter": 8.0,
        "automation_target_percent": 0.35,
        "go_live_date": datetime.now(timezone.utc).isoformat(),
        "notes": "Requires SSO integration and priority onboarding.",
        "success_criteria": ["Reduce brief preparation time by 60%"],
    }
    billing_headers = auth_headers_factory(
        scopes=["billing:read"],
        roles=["CustomerSuccessManager"],
        audience=["co-counsel.billing"],
    )
    onboarding_response = client.post("/onboarding", json=onboarding_payload, headers=billing_headers)
    assert onboarding_response.status_code == 201
    onboarded = onboarding_response.json()
    assert onboarded["tenant_id"] == "tenant-beta"

    plans_response = client.get("/billing/plans", headers=billing_headers)
    assert plans_response.status_code == 200
    plans = plans_response.json()
    assert any(plan["plan_id"] == onboarded["recommended_plan"] for plan in plans["plans"])

    usage_response = client.get("/billing/usage", headers=billing_headers)
    assert usage_response.status_code == 200
    payload = usage_response.json()
    assert payload["tenants"]
    assert any(tenant["tenant_id"] == "tenant-beta" for tenant in payload["tenants"])
