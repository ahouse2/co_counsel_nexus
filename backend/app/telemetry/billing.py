"""Billing telemetry and commercial usage instrumentation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Dict, List

from opentelemetry import metrics

from ..config import Settings, get_settings
from ..security.authz import Principal

_meter = metrics.get_meter(__name__)
_usage_counter = _meter.create_counter(
    "billing_usage_events_total",
    unit="1",
    description="Total billing events recorded for usage analytics",
)
_consumption_ratio_histogram = _meter.create_histogram(
    "billing_usage_consumption_ratio",
    unit="1",
    description="Ratio of consumed quota versus plan allowance",
)
_health_score_histogram = _meter.create_histogram(
    "billing_customer_health_score",
    unit="1",
    description="Composite health score for each tenant (0-1)",
)
_storage_histogram = _meter.create_histogram(
    "billing_storage_gib",
    unit="GiBy",
    description="Ingestion volume attributed to tenants",
)
_projected_cost_histogram = _meter.create_histogram(
    "billing_projected_monthly_cost_usd",
    unit="USD",
    description="Projected monthly cost for the tenant based on current usage",
)


class BillingEventType(str, Enum):
    """Event taxonomies tracked for usage metering."""

    INGESTION = "ingestion.job"
    QUERY = "query.run"
    TIMELINE = "timeline.request"
    AGENT = "agent.run"
    SIGNUP = "onboarding.signup"


@dataclass(frozen=True)
class SupportTier:
    """Support posture details exposed to pricing collateral."""

    name: str
    response_sla_hours: int
    coverage: str
    contact_channel: str


@dataclass(frozen=True)
class BillingPlan:
    """Commercial plan definition and usage entitlements."""

    plan_id: str
    label: str
    monthly_price_usd: float
    included_queries: int
    included_ingest_gb: float
    included_seats: int
    support_tier: str
    overage_per_query_usd: float
    overage_per_gb_usd: float
    onboarding_sla_hours: int
    description: str


SUPPORT_TIERS: Dict[str, SupportTier] = {
    "community": SupportTier(
        name="Community",
        response_sla_hours=48,
        coverage="Business hours (GMT-5 to GMT+1)",
        contact_channel="Community forum & email triage",
    ),
    "standard": SupportTier(
        name="Standard",
        response_sla_hours=12,
        coverage="18x5 follow-the-sun",
        contact_channel="Zendesk queue & scheduled success reviews",
    ),
    "premium": SupportTier(
        name="Premium",
        response_sla_hours=2,
        coverage="24x7 global incident desk",
        contact_channel="Dedicated Slack Connect + direct hotline",
    ),
}


BILLING_PLANS: Dict[str, BillingPlan] = {
    "community": BillingPlan(
        plan_id="community",
        label="Community",
        monthly_price_usd=0.0,
        included_queries=500,
        included_ingest_gb=5.0,
        included_seats=5,
        support_tier="community",
        overage_per_query_usd=0.02,
        overage_per_gb_usd=3.0,
        onboarding_sla_hours=72,
        description="Self-serve evaluation tier with essential ingestion and research limits.",
    ),
    "professional": BillingPlan(
        plan_id="professional",
        label="Professional",
        monthly_price_usd=3499.0,
        included_queries=5000,
        included_ingest_gb=60.0,
        included_seats=25,
        support_tier="standard",
        overage_per_query_usd=0.015,
        overage_per_gb_usd=2.4,
        onboarding_sla_hours=24,
        description="Production-grade deployment with telemetry, premium connectors, and success management.",
    ),
    "enterprise": BillingPlan(
        plan_id="enterprise",
        label="Enterprise",
        monthly_price_usd=8999.0,
        included_queries=20000,
        included_ingest_gb=250.0,
        included_seats=100,
        support_tier="premium",
        overage_per_query_usd=0.01,
        overage_per_gb_usd=1.6,
        onboarding_sla_hours=4,
        description="Global roll-out with federated governance, white-glove onboarding, and dedicated SRE escorts.",
    ),
}


@dataclass
class TenantUsage:
    tenant_id: str
    plan_id: str
    support_tier: str
    total_events: float = 0.0
    successful_events: float = 0.0
    ingestion_jobs: float = 0.0
    ingestion_gb: float = 0.0
    query_count: float = 0.0
    query_latency_ms_total: float = 0.0
    timeline_requests: float = 0.0
    agent_runs: float = 0.0
    seats_requested: int = 0
    onboarding_completed: bool = False
    metadata: Dict[str, object] = field(default_factory=dict)
    last_event_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def record_success(self, success: bool, units: float) -> None:
        self.total_events += units
        if success:
            self.successful_events += units

    def success_rate(self) -> float:
        if self.total_events <= 0:
            return 1.0
        return max(0.0, min(1.0, self.successful_events / self.total_events))

    def query_latency_average(self) -> float:
        if self.query_count <= 0:
            return 0.0
        return self.query_latency_ms_total / self.query_count

    def usage_ratio(self, plan: BillingPlan) -> float:
        query_ratio = self.query_count / plan.included_queries if plan.included_queries else 0.0
        ingest_ratio = self.ingestion_gb / plan.included_ingest_gb if plan.included_ingest_gb else 0.0
        seat_ratio = (self.seats_requested or 0) / plan.included_seats if plan.included_seats else 0.0
        return max(query_ratio, ingest_ratio, seat_ratio)

    def projected_cost(self, plan: BillingPlan) -> float:
        extra_queries = max(0.0, self.query_count - plan.included_queries)
        extra_gb = max(0.0, self.ingestion_gb - plan.included_ingest_gb)
        return plan.monthly_price_usd + (extra_queries * plan.overage_per_query_usd) + (extra_gb * plan.overage_per_gb_usd)

    def health_score(self, plan: BillingPlan, settings: Settings) -> float:
        success_score = self.success_rate()
        usage_ratio = self.usage_ratio(plan)
        usage_headroom = max(0.0, 1.0 - min(1.5, usage_ratio))
        support_multiplier = {
            "community": 0.7,
            "standard": 0.85,
            "premium": 1.0,
        }.get(self.support_tier, 0.8)
        penalty = 0.0
        if usage_ratio >= settings.billing_health_hard_threshold:
            penalty = 0.35
        elif usage_ratio >= settings.billing_health_soft_threshold:
            penalty = 0.18
        base = (0.5 * success_score) + (0.3 * usage_headroom) + (0.2 * support_multiplier)
        score = max(0.0, min(1.0, base - penalty))
        if self.onboarding_completed:
            score = min(1.0, score + 0.05)
        return score

    def to_snapshot(self, plan: BillingPlan, settings: Settings) -> "TenantUsageSnapshot":
        return TenantUsageSnapshot(
            tenant_id=self.tenant_id,
            plan=plan,
            support=SUPPORT_TIERS.get(self.support_tier, SUPPORT_TIERS[plan.support_tier]),
            total_events=self.total_events,
            success_rate=self.success_rate(),
            usage_ratio=self.usage_ratio(plan),
            health_score=self.health_score(plan, settings),
            ingestion_jobs=self.ingestion_jobs,
            ingestion_gb=self.ingestion_gb,
            query_count=self.query_count,
            average_query_latency_ms=self.query_latency_average(),
            timeline_requests=self.timeline_requests,
            agent_runs=self.agent_runs,
            projected_monthly_cost=self.projected_cost(plan),
            seats_requested=self.seats_requested,
            onboarding_completed=self.onboarding_completed,
            last_event_at=self.last_event_at,
            metadata=dict(self.metadata),
        )

    def to_json(self) -> Dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "plan_id": self.plan_id,
            "support_tier": self.support_tier,
            "total_events": self.total_events,
            "successful_events": self.successful_events,
            "ingestion_jobs": self.ingestion_jobs,
            "ingestion_gb": self.ingestion_gb,
            "query_count": self.query_count,
            "query_latency_ms_total": self.query_latency_ms_total,
            "timeline_requests": self.timeline_requests,
            "agent_runs": self.agent_runs,
            "seats_requested": self.seats_requested,
            "onboarding_completed": self.onboarding_completed,
            "metadata": self.metadata,
            "last_event_at": self.last_event_at.isoformat(),
        }

    @classmethod
    def from_json(cls, payload: Dict[str, object]) -> "TenantUsage":
        last_event_raw = payload.get("last_event_at")
        last_event = (
            datetime.fromisoformat(last_event_raw)
            if isinstance(last_event_raw, str)
            else datetime.now(timezone.utc)
        )
        return cls(
            tenant_id=str(payload.get("tenant_id", "unknown")),
            plan_id=str(payload.get("plan_id", "community")),
            support_tier=str(payload.get("support_tier", "community")),
            total_events=float(payload.get("total_events", 0.0)),
            successful_events=float(payload.get("successful_events", 0.0)),
            ingestion_jobs=float(payload.get("ingestion_jobs", 0.0)),
            ingestion_gb=float(payload.get("ingestion_gb", 0.0)),
            query_count=float(payload.get("query_count", 0.0)),
            query_latency_ms_total=float(payload.get("query_latency_ms_total", 0.0)),
            timeline_requests=float(payload.get("timeline_requests", 0.0)),
            agent_runs=float(payload.get("agent_runs", 0.0)),
            seats_requested=int(payload.get("seats_requested", 0)),
            onboarding_completed=bool(payload.get("onboarding_completed", False)),
            metadata=dict(payload.get("metadata", {})),
            last_event_at=last_event,
        )


@dataclass
class TenantUsageSnapshot:
    tenant_id: str
    plan: BillingPlan
    support: SupportTier
    total_events: float
    success_rate: float
    usage_ratio: float
    health_score: float
    ingestion_jobs: float
    ingestion_gb: float
    query_count: float
    average_query_latency_ms: float
    timeline_requests: float
    agent_runs: float
    projected_monthly_cost: float
    seats_requested: int
    onboarding_completed: bool
    last_event_at: datetime
    metadata: Dict[str, object]

    def as_dict(self) -> Dict[str, object]:
        return {
            "tenant_id": self.tenant_id,
            "plan_id": self.plan.plan_id,
            "plan_label": self.plan.label,
            "support_tier": self.support.name,
            "support_sla_hours": self.support.response_sla_hours,
            "support_channel": self.support.contact_channel,
            "total_events": self.total_events,
            "success_rate": self.success_rate,
            "usage_ratio": self.usage_ratio,
            "health_score": self.health_score,
            "ingestion_jobs": self.ingestion_jobs,
            "ingestion_gb": self.ingestion_gb,
            "query_count": self.query_count,
            "average_query_latency_ms": self.average_query_latency_ms,
            "timeline_requests": self.timeline_requests,
            "agent_runs": self.agent_runs,
            "projected_monthly_cost": self.projected_monthly_cost,
            "seats_requested": self.seats_requested,
            "onboarding_completed": self.onboarding_completed,
            "last_event_at": self.last_event_at.isoformat(),
            "metadata": self.metadata,
        }


class BillingTelemetry:
    """Central registry for billing usage and customer health metrics."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._lock = Lock()
        self._usage: Dict[str, TenantUsage] = {}
        self._path: Path = self.settings.billing_usage_path
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return
        with self._lock:
            for tenant_payload in payload.get("tenants", []):
                usage = TenantUsage.from_json(tenant_payload)
                self._usage[usage.tenant_id] = usage

    def _persist(self) -> None:
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tenants": [usage.to_json() for usage in self._usage.values()],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")

    def reset(self) -> None:
        with self._lock:
            self._usage.clear()
        if self._path.exists():
            self._path.unlink()

    def resolve_plan(self, tenant_id: str | None) -> BillingPlan:
        plan_id = self.settings.billing_default_plan
        overrides = {k: v for k, v in self.settings.billing_plan_overrides.items() if k}
        if tenant_id and tenant_id in overrides:
            plan_id = overrides[tenant_id]
        plan = BILLING_PLANS.get(plan_id)
        if not plan:
            plan = BILLING_PLANS[self.settings.billing_default_plan]
        return plan

    def resolve_support_tier(self, tenant_id: str | None, plan: BillingPlan) -> str:
        if tenant_id and tenant_id in self.settings.billing_support_overrides:
            override = self.settings.billing_support_overrides[tenant_id]
            if override in SUPPORT_TIERS:
                return override
        return plan.support_tier

    def record_event(
        self,
        principal: Principal | None,
        event_type: BillingEventType,
        units: float = 1.0,
        *,
        success: bool = True,
        attributes: Dict[str, object] | None = None,
    ) -> None:
        tenant_id = attributes.get("tenant_id") if attributes else None
        if principal is not None:
            tenant_id = principal.tenant_id
        tenant_id = tenant_id or "public"
        plan = self.resolve_plan(tenant_id)
        support_tier = self.resolve_support_tier(tenant_id, plan)
        now = datetime.now(timezone.utc)
        extra = dict(attributes or {})

        with self._lock:
            usage = self._usage.get(tenant_id)
            if usage is None:
                usage = TenantUsage(tenant_id=tenant_id, plan_id=plan.plan_id, support_tier=support_tier)
                self._usage[tenant_id] = usage
            if usage.plan_id != plan.plan_id:
                usage.plan_id = plan.plan_id
            usage.support_tier = support_tier
            usage.last_event_at = now
            usage.record_success(success, units)

            if event_type is BillingEventType.INGESTION:
                usage.ingestion_jobs += units
                gigabytes = float(extra.get("gigabytes", 0.0))
                usage.ingestion_gb += gigabytes
                if gigabytes > 0:
                    _storage_histogram.record(
                        gigabytes,
                        attributes={
                            "tenant_id": tenant_id,
                            "plan": plan.plan_id,
                            "event_type": event_type.value,
                        },
                    )
            elif event_type is BillingEventType.QUERY:
                usage.query_count += units
                latency_ms = float(extra.get("latency_ms", 0.0))
                usage.query_latency_ms_total += latency_ms
            elif event_type is BillingEventType.TIMELINE:
                usage.timeline_requests += units
            elif event_type is BillingEventType.AGENT:
                usage.agent_runs += units
            elif event_type is BillingEventType.SIGNUP:
                seats = int(extra.get("seats", 0))
                if seats:
                    usage.seats_requested = max(usage.seats_requested, seats)
                if extra.get("completed"):
                    usage.onboarding_completed = True
                usage.metadata.update({k: v for k, v in extra.items() if k not in {"seats", "completed"}})

            ratio = usage.usage_ratio(plan)
            health = usage.health_score(plan, self.settings)
            projected_cost = usage.projected_cost(plan)

            metric_attributes = {
                "tenant_id": tenant_id,
                "plan": plan.plan_id,
                "support_tier": usage.support_tier,
                "event_type": event_type.value,
            }
            _usage_counter.add(units, attributes=metric_attributes)
            _consumption_ratio_histogram.record(ratio, attributes=metric_attributes)
            _health_score_histogram.record(health, attributes=metric_attributes)
            _projected_cost_histogram.record(projected_cost, attributes=metric_attributes)

            self._persist()

    def snapshot(self) -> List[TenantUsageSnapshot]:
        with self._lock:
            return [usage.to_snapshot(self.resolve_plan(tenant_id), self.settings) for tenant_id, usage in self._usage.items()]


_billing_registry: BillingTelemetry | None = None
_registry_lock = Lock()


def get_billing_registry() -> BillingTelemetry:
    global _billing_registry
    if _billing_registry is None:
        with _registry_lock:
            if _billing_registry is None:
                _billing_registry = BillingTelemetry()
    return _billing_registry


def reset_billing_registry() -> None:
    global _billing_registry
    with _registry_lock:
        if _billing_registry is not None:
            _billing_registry.reset()
        _billing_registry = None


def record_billing_event(
    principal: Principal | None,
    event_type: BillingEventType,
    units: float = 1.0,
    *,
    success: bool = True,
    attributes: Dict[str, object] | None = None,
) -> None:
    registry = get_billing_registry()
    registry.record_event(principal, event_type, units, success=success, attributes=attributes)


def export_plan_catalogue() -> List[Dict[str, object]]:
    catalogue: List[Dict[str, object]] = []
    for plan in BILLING_PLANS.values():
        support = SUPPORT_TIERS[plan.support_tier]
        catalogue.append(
            {
                "plan_id": plan.plan_id,
                "label": plan.label,
                "monthly_price_usd": plan.monthly_price_usd,
                "included_queries": plan.included_queries,
                "included_ingest_gb": plan.included_ingest_gb,
                "included_seats": plan.included_seats,
                "support_tier": support.name,
                "support_response_sla_hours": support.response_sla_hours,
                "support_contact": support.contact_channel,
                "overage_per_query_usd": plan.overage_per_query_usd,
                "overage_per_gb_usd": plan.overage_per_gb_usd,
                "onboarding_sla_hours": plan.onboarding_sla_hours,
                "description": plan.description,
            }
        )
    return catalogue


def export_customer_health() -> List[Dict[str, object]]:
    registry = get_billing_registry()
    return [snapshot.as_dict() for snapshot in registry.snapshot()]
