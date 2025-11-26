from __future__ import annotations

import logging
import random
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ..agents import MicrosoftAgentsOrchestrator, get_orchestrator
from ..agents.graph_manager import GraphManagerAgent
from ..agents.qa import QAAgent
from ..agents.types import AgentThread, AgentTurn
from ..config import get_settings
from ..security.authz import Principal
from ..storage.agent_memory_store import AgentMemoryStore, AgentThreadRecord
from ..storage.document_store import DocumentStore
from ..storage.timeline_store import TimelineStore
from ..utils.audit import AuditEvent, get_audit_trail
from .errors import (
    CircuitOpenError,
    WorkflowAbort,
    WorkflowComponent,
    WorkflowError,
    WorkflowException,
    WorkflowSeverity,
    http_status_for_error,
)
from .forensics import ForensicsService, get_forensics_service
from .graph import GraphService, get_graph_service
from .retrieval import RetrievalService, get_retrieval_service


_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)

_agents_runs_counter = _meter.create_counter(
    "agents_runs_total",
    unit="1",
    description="Agent orchestration runs processed",
)
_agents_run_duration = _meter.create_histogram(
    "agents_run_duration_ms",
    unit="ms",
    description="Latency of agent orchestration runs",
)
_agents_turn_counter = _meter.create_counter(
    "agents_turns_total",
    unit="1",
    description="Total agent turns emitted per run",
)
_agents_retry_counter = _meter.create_counter(
    "agents_retries_total",
    unit="1",
    description="Retries executed within agent workflow components",
)
_agents_failure_counter = _meter.create_counter(
    "agents_failures_total",
    unit="1",
    description="Agent runs ending in failure",
)

_agents_policy_decisions_counter = _meter.create_counter(
    "agents_policy_decisions_total",
    unit="1",
    description="Adaptive policy decisions evaluated for agent runs",
)
_agents_policy_reward_histogram = _meter.create_histogram(
    "agents_policy_reward",
    unit="1",
    description="Reward adjustments applied to agent trust scores",
)

_COMPONENT_TO_ROLE = {
    WorkflowComponent.STRATEGY: "strategy",
    WorkflowComponent.INGESTION: "ingestion",
    WorkflowComponent.RETRIEVAL: "research",
    WorkflowComponent.GRAPH: "cocounsel",
    WorkflowComponent.FORENSICS: "cocounsel",
    WorkflowComponent.QA: "qa",
}


@dataclass(slots=True)
class PolicyDecision:
    enabled: bool
    trust_snapshot: Dict[str, float]
    suppressed_roles: List[str]
    elevated_roles: List[str]
    graph_overrides: Dict[str, List[str]]
    exploration: bool
    seed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "trust": dict(self.trust_snapshot),
            "suppressed_roles": list(self.suppressed_roles),
            "elevated_roles": list(self.elevated_roles),
            "graph_overrides": {k: list(v) for k, v in self.graph_overrides.items()},
            "exploration": self.exploration,
            "seed": self.seed,
        }


class AdaptivePolicyEngine:
    """Observes telemetry and produces delegate graph policy decisions."""

    def __init__(
        self,
        settings: Any,
        *,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.enabled = bool(getattr(settings, "agents_policy_enabled", False))
        self.initial_trust = float(getattr(settings, "agents_policy_initial_trust", 0.5))
        self.trust_threshold = float(getattr(settings, "agents_policy_trust_threshold", 0.2))
        self.decay = float(getattr(settings, "agents_policy_decay", 0.0))
        self.success_reward = float(getattr(settings, "agents_policy_success_reward", 0.1))
        self.failure_penalty = float(getattr(settings, "agents_policy_failure_penalty", 0.4))
        self.exploration_probability = float(
            getattr(settings, "agents_policy_exploration_probability", 0.0)
        )
        self.roles = tuple(
            str(role) for role in getattr(settings, "agents_policy_observable_roles", ())
        ) or ("strategy", "ingestion", "research", "cocounsel", "qa")
        self.suppressible_roles = {
            str(role)
            for role in getattr(settings, "agents_policy_suppressible_roles", ())
        }
        self._seed: Optional[int] = getattr(settings, "agents_policy_seed", None)
        self._rng = rng or random.Random(self._seed)
        self._scores: Dict[str, float] = {
            role: self.initial_trust for role in self.roles
        }
        self.last_decision: Optional[PolicyDecision] = None
        self.last_observation: Dict[str, Any] | None = None

    def state(self) -> Dict[str, float]:
        return dict(self._scores)

    def plan_run(
        self,
        case_id: str,
        question: str,
        telemetry: Dict[str, Any],
    ) -> PolicyDecision:
        if not self.enabled:
            decision = PolicyDecision(
                enabled=False,
                trust_snapshot=self.state(),
                suppressed_roles=[],
                elevated_roles=[],
                graph_overrides={},
                exploration=False,
                seed=self._seed,
            )
            telemetry.setdefault("policy", decision.to_dict())
            self.last_decision = decision
            return decision

        trust_snapshot = self.state()
        suppressed_roles = [
            role
            for role in self.suppressible_roles
            if trust_snapshot.get(role, self.initial_trust) < self.trust_threshold
        ]
        exploration = False
        elevated_roles: List[str] = []
        if self.exploration_probability > 0 and self._rng.random() < self.exploration_probability:
            exploration = True
            eligible = [role for role in self.roles if role not in suppressed_roles]
            if eligible:
                choice = self._rng.choice(eligible)
                elevated_roles.append(choice)
                if choice in suppressed_roles:
                    suppressed_roles.remove(choice)

        graph_overrides: Dict[str, List[str]] = {}
        if "cocounsel" in suppressed_roles:
            graph_overrides["research"] = ["qa"]
        if "ingestion" in suppressed_roles:
            graph_overrides.setdefault("strategy", ["research"])

        decision = PolicyDecision(
            enabled=True,
            trust_snapshot=trust_snapshot,
            suppressed_roles=suppressed_roles,
            elevated_roles=elevated_roles,
            graph_overrides=graph_overrides,
            exploration=exploration,
            seed=self._seed,
        )
        telemetry.setdefault("policy", {}).update(decision.to_dict())
        _agents_policy_decisions_counter.add(
            1,
            attributes={
                "suppressed_count": len(suppressed_roles),
                "exploration": exploration,
            },
        )
        self.last_decision = decision
        return decision

    def observe_run(self, thread: AgentThread) -> Dict[str, Any]:
        if not self.enabled:
            snapshot = {role: self.initial_trust for role in self.roles}
            self.last_observation = {"trust": snapshot, "rewards": {}}
            return self.last_observation

        rewards: Dict[str, float] = {}
        failures = {
            _COMPONENT_TO_ROLE.get(error.component)
            for error in thread.errors
            if _COMPONENT_TO_ROLE.get(error.component)
        }
        seen: set[str] = set()
        for turn in thread.turns:
            role = turn.role
            if role not in self.roles or role in seen:
                continue
            seen.add(role)
            outcome = "failed" if role in failures or turn.annotations.get("status") == "failed" else "success"
            reward = self.success_reward if outcome == "success" else -self.failure_penalty
            current = self._scores.get(role, self.initial_trust)
            updated = max(0.0, (1.0 - self.decay) * current + reward)
            self._scores[role] = updated
            rewards[role] = reward
            _agents_policy_reward_histogram.record(
                reward,
                attributes={"role": role, "outcome": outcome},
            )

        snapshot = self.state()
        observation = {"trust": snapshot, "rewards": rewards}
        self.last_observation = observation
        return observation

    def observe_failure(self, thread: AgentThread, error: WorkflowError) -> Dict[str, Any]:
        if not self.enabled:
            snapshot = {role: self.initial_trust for role in self.roles}
            self.last_observation = {"trust": snapshot, "rewards": {}}
            return self.last_observation
        role = _COMPONENT_TO_ROLE.get(error.component)
        rewards: Dict[str, float] = {}
        if role:
            current = self._scores.get(role, self.initial_trust)
            reward = -self.failure_penalty
            updated = max(0.0, (1.0 - self.decay) * current + reward)
            self._scores[role] = updated
            rewards[role] = reward
            _agents_policy_reward_histogram.record(
                reward,
                attributes={"role": role, "outcome": "failed"},
            )
        snapshot = self.state()
        observation = {"trust": snapshot, "rewards": rewards, "last_failure": error.code}
        self.last_observation = observation
        return observation


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CircuitBreaker:
    """Lightweight rolling-window circuit breaker for agent components."""

    def __init__(
        self,
        component: WorkflowComponent,
        *,
        threshold: int,
        window_seconds: float,
        cooldown_seconds: float,
    ) -> None:
        self.component = component
        self.threshold = max(1, threshold)
        self.window_seconds = max(1.0, window_seconds)
        self.cooldown_seconds = max(1.0, cooldown_seconds)
        self._failures: deque[datetime] = deque()
        self._opened_at: datetime | None = None

    def ensure_can_execute(self) -> None:
        now = _now()
        if self._opened_at is not None:
            elapsed = (now - self._opened_at).total_seconds()
            if elapsed < self.cooldown_seconds:
                raise CircuitOpenError(
                    WorkflowError(
                        component=self.component,
                        code=f"{self.component.value.upper()}_CIRCUIT_OPEN",
                        message=f"Circuit breaker open for {self.component.value} component",
                        severity=WorkflowSeverity.ERROR,
                        retryable=True,
                        context={
                            "opened_at": self._opened_at.isoformat(),
                            "cooldown_seconds": self.cooldown_seconds,
                        },
                    ),
                    status_code=503,
                )
            self._opened_at = None
            self._failures.clear()
        self._prune(now)

    def record_failure(self) -> None:
        now = _now()
        self._failures.append(now)
        self._prune(now)
        if len(self._failures) >= self.threshold:
            self._opened_at = now

    def record_success(self) -> None:
        self._failures.clear()
        self._opened_at = None

    def _prune(self, now: datetime) -> None:
        boundary = now
        while self._failures and (boundary - self._failures[0]).total_seconds() > self.window_seconds:
            self._failures.popleft()


class AgentsService:
    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        forensics_service: ForensicsService | None = None,
        memory_store: AgentMemoryStore | None = None,
        document_store: DocumentStore | None = None,
        qa_agent: QAAgent | None = None,
        orchestrator: MicrosoftAgentsOrchestrator | None = None,
        graph_service: GraphService | None = None,
        timeline_store: TimelineStore | None = None,
        graph_agent: GraphManagerAgent | None = None,
        policy_engine: AdaptivePolicyEngine | None = None,
    ) -> None:
        self.settings = get_settings()
        self.retrieval_service = retrieval_service or get_retrieval_service()
        self.forensics_service = forensics_service or get_forensics_service()
        self.document_store = document_store or DocumentStore(self.settings.document_store_dir)
        self.memory_store = memory_store or AgentMemoryStore(self.settings.agent_threads_dir)
        self.qa_agent = qa_agent or QAAgent()
        self.graph_service = graph_service or get_graph_service()
        self.timeline_store = timeline_store or TimelineStore(self.settings.timeline_path)
        self.graph_agent = graph_agent or GraphManagerAgent(
            graph_service=self.graph_service,
            timeline_store=self.timeline_store,
        )
        self.orchestrator = orchestrator or get_orchestrator(
            self.retrieval_service,
            self.forensics_service,
            self.document_store,
            self.qa_agent,
            self.memory_store,
            self.graph_agent,
        )
        self.policy_engine = policy_engine or AdaptivePolicyEngine(self.settings)
        self.audit = get_audit_trail()
        self.retry_attempts = max(1, self.settings.agent_retry_attempts)
        self.retry_backoff_ms = max(0, self.settings.agent_retry_backoff_ms)
        self.default_autonomy_level = getattr(self.settings, "agent_default_autonomy", "balanced")
        self.default_max_turns = getattr(self.settings, "agent_max_turns", 12)
        breaker_config = {
            "threshold": self.settings.agent_circuit_threshold,
            "window_seconds": self.settings.agent_circuit_window_seconds,
            "cooldown_seconds": self.settings.agent_circuit_cooldown_seconds,
        }
        self.circuit_breakers = {
            WorkflowComponent.STRATEGY: CircuitBreaker(WorkflowComponent.STRATEGY, **breaker_config),
            WorkflowComponent.INGESTION: CircuitBreaker(WorkflowComponent.INGESTION, **breaker_config),
            WorkflowComponent.RETRIEVAL: CircuitBreaker(WorkflowComponent.RETRIEVAL, **breaker_config),
            WorkflowComponent.GRAPH: CircuitBreaker(WorkflowComponent.GRAPH, **breaker_config),
            WorkflowComponent.FORENSICS: CircuitBreaker(WorkflowComponent.FORENSICS, **breaker_config),
            WorkflowComponent.QA: CircuitBreaker(WorkflowComponent.QA, **breaker_config),
        }

    def run_case(
        self,
        case_id: str,
        question: str,
        *,
        top_k: int = 5,
        principal: Principal | None = None,
        autonomy_level: str | None = None,
        max_turns: int | None = None,
    ) -> Dict[str, Any]:
        actor = self._actor_from_principal(principal)
        thread = AgentThread(
            thread_id=str(uuid4()),
            case_id=case_id,
            question=question,
            created_at=_now(),
            updated_at=_now(),
        )
        telemetry_context = self._initial_telemetry()
        if autonomy_level:
            telemetry_context["autonomy_level"] = autonomy_level
        else:
            telemetry_context["autonomy_level"] = self.default_autonomy_level
        policy_decision: PolicyDecision | None = None
        policy_decision = self.policy_engine.plan_run(case_id, question, telemetry_context)
        self._audit_agents_event(
            action="agents.thread.created",
            outcome="accepted",
            subject={"thread_id": thread.thread_id, "case_id": case_id},
            metadata={"question_length": len(question), "top_k": top_k},
            actor=actor,
            correlation_id=thread.thread_id,
        )

        run_started = time.perf_counter()
        with _tracer.start_as_current_span("agents.run_case") as span:
            span.set_attribute("agents.case_id", case_id)
            span.set_attribute("agents.top_k", top_k)
            span.set_attribute("agents.question_length", len(question))
            if principal is not None and principal.tenant_id:
                span.set_attribute("agents.tenant_id", principal.tenant_id)

            def execute_with_resilience(
                component: WorkflowComponent,
                operation: Callable[[], Tuple[AgentTurn, Dict[str, Any]]],
                allow_partial: bool = False,
                partial_factory: Callable[[WorkflowError], Tuple[AgentTurn, Dict[str, Any]]] | None = None,
            ) -> Tuple[AgentTurn, Dict[str, Any]]:
                turn, payload = self._run_with_resilience(
                    thread,
                    component,
                    operation,
                    telemetry_context,
                    allow_partial=allow_partial,
                    partial_factory=partial_factory,
                )
                self._audit_turn(thread, turn, actor)
                return turn, payload

            try:
                result_thread = self.orchestrator.run(
                    case_id=case_id,
                    question=question,
                    top_k=top_k,
                    actor=actor,
                    component_executor=execute_with_resilience,
                    thread_id=thread.thread_id,
                    thread=thread,
                    telemetry=telemetry_context,
                    autonomy_level=telemetry_context["autonomy_level"],
                    max_turns=max_turns or self.default_max_turns,
                    policy_state=policy_decision.to_dict() if policy_decision else None,
                )
                if result_thread.status in {"", "pending"}:
                    if result_thread.errors:
                        result_thread.status = "degraded"
                        result_thread.telemetry["status"] = "degraded"
                    else:
                        result_thread.status = "succeeded"
                elif result_thread.errors and result_thread.status == "succeeded":
                    notes = result_thread.telemetry.setdefault("notes", [])
                    notes.append("Recovered from intermediate agent failures during execution.")
                result_thread.updated_at = _now()
                policy_updates = self.policy_engine.observe_run(result_thread)
                policy_payload = telemetry_context.setdefault("policy", {})
                self._merge_policy_updates(policy_payload, policy_decision.to_dict() if policy_decision else {})
                self._merge_policy_updates(policy_payload, policy_updates)
                self._merge_policy_updates(result_thread.telemetry.setdefault("policy", {}), policy_payload)
                duration_ms = (time.perf_counter() - run_started) * 1000.0
                attributes = {"status": result_thread.status}
                attributes.update(self._policy_metric_attributes(policy_decision))
                _agents_run_duration.record(duration_ms, attributes=attributes)
                _agents_runs_counter.add(1, attributes=attributes)
                _agents_turn_counter.add(len(result_thread.turns), attributes=attributes)
                span.set_attribute("agents.status", result_thread.status)
                span.set_attribute("agents.turns", len(result_thread.turns))
                span.set_attribute("agents.errors", len(result_thread.errors))
                span.set_status(Status(StatusCode.OK))
                self._audit_agents_event(
                    action="agents.thread.completed",
                    outcome="success",
                    subject={"thread_id": result_thread.thread_id, "case_id": case_id},
                    metadata={
                        "final_answer_length": len(result_thread.final_answer),
                        "qa_average": result_thread.telemetry.get("qa_average"),
                        "turn_count": len(result_thread.turns),
                        "error_count": len(result_thread.errors),
                        "retry_components": sorted(telemetry_context.get("retries", {}).keys()),
                    },
                    actor=actor,
                    correlation_id=result_thread.thread_id,
                )
                payload = self._normalise_thread_payload(result_thread.to_payload())
                record = AgentThreadRecord(thread_id=result_thread.thread_id, payload=payload)
                self.memory_store.write(record)
                return payload
            except WorkflowException as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc.error.message)))
                policy_updates = self.policy_engine.observe_failure(thread, exc.error)
                policy_payload = telemetry_context.setdefault("policy", {})
                self._merge_policy_updates(policy_payload, policy_decision.to_dict() if policy_decision else {})
                self._merge_policy_updates(policy_payload, policy_updates)
                attributes = {"status": "failed", "component": exc.error.component.value}
                attributes.update(self._policy_metric_attributes(policy_decision))
                _agents_runs_counter.add(1, attributes=attributes)
                _agents_failure_counter.add(1, attributes={"component": exc.error.component.value})
                self._handle_failure(thread, actor, telemetry_context, exc.error)
                raise
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                component = WorkflowComponent.ORCHESTRATOR
                attributes = {"status": "failed", "component": component.value}
                attributes.update(self._policy_metric_attributes(policy_decision))
                _agents_runs_counter.add(1, attributes=attributes)
                _agents_failure_counter.add(1, attributes={"component": component.value})
                error = self._classify_exception(component, exc, 1)
                if error not in thread.errors:
                    thread.errors.append(error)
                telemetry_context.setdefault("errors", []).append(error.to_dict())
                policy_updates = self.policy_engine.observe_failure(thread, error)
                policy_payload = telemetry_context.setdefault("policy", {})
                self._merge_policy_updates(policy_payload, policy_decision.to_dict() if policy_decision else {})
                self._merge_policy_updates(policy_payload, policy_updates)
                self._handle_failure(thread, actor, telemetry_context, error)
                raise WorkflowAbort(error, status_code=http_status_for_error(error)) from exc

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        payload = self.memory_store.read(thread_id)
        return self._normalise_thread_payload(payload)

    def list_threads(self) -> List[str]:
        return self.memory_store.list_threads()

    def _initial_telemetry(self) -> Dict[str, Any]:
        return {
            "turn_roles": [],
            "durations_ms": [],
            "retries": {},
            "backoff_ms": {},
            "errors": [],
            "notes": [],
            "status": "pending",
            "sequence_valid": False,
            "hand_offs": [],
            "autonomy_level": self.default_autonomy_level,
            "policy": {
                "enabled": self.policy_engine.enabled,
                "trust": self.policy_engine.state() if self.policy_engine.enabled else {},
                "suppressed_roles": [],
                "elevated_roles": [],
                "graph_overrides": {},
                "exploration": False,
            },
        }

    def _normalise_thread_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        errors = payload.setdefault("errors", [])
        status = payload.get("status") or ("succeeded" if not errors else "degraded")
        payload["status"] = status
        telemetry = payload.setdefault("telemetry", {})
        telemetry.setdefault("status", status)
        telemetry.setdefault("errors", [])
        telemetry.setdefault("retries", {})
        telemetry.setdefault("backoff_ms", {})
        telemetry.setdefault("policy", {"enabled": self.policy_engine.enabled})
        return payload

    def _policy_metric_attributes(self, decision: PolicyDecision | None) -> Dict[str, Any]:
        if decision is None or not decision.enabled:
            return {"policy_enabled": False}
        suppressed = ",".join(sorted(decision.suppressed_roles)) if decision.suppressed_roles else "none"
        return {
            "policy_enabled": True,
            "policy_suppressed": suppressed,
            "policy_exploration": decision.exploration,
        }

    @staticmethod
    def _merge_policy_updates(target: Dict[str, Any], updates: Dict[str, Any] | None) -> None:
        if not updates:
            return
        rewards = updates.get("rewards")
        if isinstance(rewards, dict):
            target.setdefault("rewards", {}).update(rewards)
        for key, value in updates.items():
            if key == "rewards":
                continue
            target[key] = value

    def _run_with_resilience(
        self,
        thread: AgentThread,
        component: WorkflowComponent,
        operation: Callable[[], Tuple[AgentTurn, Dict[str, Any]]],
        telemetry: Dict[str, Any],
        *,
        allow_partial: bool = False,
        partial_factory: Callable[[WorkflowError], Tuple[AgentTurn, Dict[str, Any]]] | None = None,
    ) -> Tuple[AgentTurn, Dict[str, Any]]:
        breaker = self.circuit_breakers[component]
        attempts = 0
        last_error: WorkflowError | None = None
        while attempts < self.retry_attempts:
            attempts += 1
            breaker.ensure_can_execute()
            try:
                turn, payload = operation()
            except WorkflowException as exc:
                error = exc.error
                error.attempt = attempts
                if error not in thread.errors:
                    thread.errors.append(error)
                telemetry.setdefault("errors", []).append(error.to_dict())
                breaker.record_failure()
                last_error = error
                if error.retryable and attempts < self.retry_attempts:
                    self._record_retry(telemetry, component, attempts)
                    self._backoff(component, attempts, telemetry)
                    continue
                if allow_partial and partial_factory is not None:
                    turn, payload = partial_factory(error)
                    breaker.record_success()
                    return turn, payload
                raise
            except Exception as exc:
                error = self._classify_exception(component, exc, attempts)
                if error not in thread.errors:
                    thread.errors.append(error)
                telemetry.setdefault("errors", []).append(error.to_dict())
                breaker.record_failure()
                last_error = error
                if error.retryable and attempts < self.retry_attempts:
                    self._record_retry(telemetry, component, attempts)
                    self._backoff(component, attempts, telemetry)
                    continue
                if allow_partial and partial_factory is not None:
                    turn, payload = partial_factory(error)
                    breaker.record_success()
                    return turn, payload
                raise WorkflowAbort(error, status_code=http_status_for_error(error)) from exc
            else:
                breaker.record_success()
                if attempts > 1:
                    telemetry.setdefault("retries", {})[component.value] = attempts - 1
                return turn, payload
        assert last_error is not None
        raise WorkflowAbort(last_error, status_code=http_status_for_error(last_error))

    def _record_retry(
        self,
        telemetry: Dict[str, Any],
        component: WorkflowComponent,
        attempt: int,
    ) -> None:
        retries = telemetry.setdefault("retries", {})
        retries[component.value] = attempt
        _agents_retry_counter.add(1, attributes={"component": component.value})

    def _backoff(
        self,
        component: WorkflowComponent,
        attempt: int,
        telemetry: Dict[str, Any],
    ) -> None:
        delay_ms = (2 ** (attempt - 1)) * self.retry_backoff_ms
        if delay_ms <= 0:
            return
        telemetry.setdefault("backoff_ms", {})[component.value] = delay_ms
        time.sleep(delay_ms / 1000.0)

    def _classify_exception(
        self, component: WorkflowComponent, exc: Exception, attempt: int
    ) -> WorkflowError:
        if isinstance(exc, ValueError):
            code = f"{component.value.upper()}_INVALID_INPUT"
            severity = WorkflowSeverity.ERROR
            retryable = False
        elif isinstance(exc, TimeoutError):
            code = f"{component.value.upper()}_TIMEOUT"
            severity = WorkflowSeverity.ERROR
            retryable = True
        elif isinstance(exc, ConnectionError):
            code = f"{component.value.upper()}_CONNECTION_ERROR"
            severity = WorkflowSeverity.ERROR
            retryable = True
        elif isinstance(exc, RuntimeError):
            code = f"{component.value.upper()}_RUNTIME_ERROR"
            severity = WorkflowSeverity.ERROR
            retryable = True
        elif isinstance(exc, PermissionError):
            code = f"{component.value.upper()}_PERMISSION_DENIED"
            severity = WorkflowSeverity.ERROR
            retryable = False
        else:
            code = f"{component.value.upper()}_UNHANDLED_ERROR"
            severity = WorkflowSeverity.CRITICAL
            retryable = False
        message = str(exc) or code.replace("_", " ").title()
        return WorkflowError(
            component=component,
            code=code,
            message=message,
            severity=severity,
            retryable=retryable,
            attempt=attempt,
            context={"exception": exc.__class__.__name__},
        )

    def _handle_failure(
        self,
        thread: AgentThread,
        actor: Dict[str, Any],
        telemetry: Dict[str, Any],
        error: WorkflowError,
        *,
        audit_action: str = "agents.thread.failed",
    ) -> None:
        if error not in thread.errors:
            thread.errors.append(error)
        errors = telemetry.setdefault("errors", [])
        payload = error.to_dict()
        if not errors or errors[-1] != payload:
            errors.append(payload)
        telemetry["status"] = "failed"
        thread.status = "failed"
        thread.updated_at = _now()
        thread.telemetry = telemetry
        _agents_failure_counter.add(
            1,
            attributes={"component": error.component.value, "severity": error.severity.value},
        )
        self._audit_agents_event(
            action=audit_action,
            outcome="error",
            subject={"thread_id": thread.thread_id, "case_id": thread.case_id},
            metadata={**error.to_dict(), "turn_count": len(thread.turns)},
            actor=actor,
            correlation_id=thread.thread_id,
            severity=error.severity.value,
        )
        record = AgentThreadRecord(thread_id=thread.thread_id, payload=thread.to_payload())
        self.memory_store.write(record)

    def _actor_from_principal(self, principal: Principal | None) -> Dict[str, Any]:
        if principal is None:
            return {"id": "agents-orchestrator", "type": "system", "roles": ["System"]}
        actor = {
            "id": principal.client_id,
            "subject": principal.subject,
            "tenant_id": principal.tenant_id,
            "roles": sorted(principal.roles),
            "scopes": sorted(principal.scopes),
            "case_admin": principal.case_admin,
            "token_roles": sorted(principal.token_roles),
            "certificate_roles": sorted(principal.certificate_roles),
        }
        fingerprint = principal.attributes.get("fingerprint") or principal.attributes.get(
            "certificate_fingerprint"
        )
        if fingerprint:
            actor["fingerprint"] = fingerprint
        return actor

    def _audit_agents_event(
        self,
        *,
        action: str,
        outcome: str,
        subject: Dict[str, Any],
        metadata: Dict[str, Any] | None,
        actor: Dict[str, Any],
        correlation_id: str,
        severity: str = "info",
    ) -> None:
        event = AuditEvent(
            category="agents",
            action=action,
            actor=actor,
            subject=subject,
            outcome=outcome,
            severity=severity,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._safe_audit(event)
        
        # Broadcast event to real-time stream
        try:
            from .event_bus import get_agent_event_broadcaster
            broadcaster = get_agent_event_broadcaster()
            # We need to schedule this on the loop since publish is async
            # and this method is sync (or at least called from sync contexts often)
            # However, AgentsService methods are generally async or run in async context.
            # If this method is called synchronously, we might need a background task.
            # Given the codebase uses asyncio, let's try to get the running loop.
            
            payload = {
                "timestamp": _now().isoformat(),
                "type": "agent_activity",
                "agent": actor.get("id", "system"),
                "action": action,
                "target": subject.get("turn_role") or subject.get("case_id"),
                "message": f"{action} - {outcome}",
                "metadata": metadata
            }
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broadcaster.publish(payload))
            except RuntimeError:
                # No running loop (e.g. during tests or sync execution), skip broadcast
                pass
        except Exception as e:
            # Don't fail the main flow if broadcasting fails
            logging.warning(f"Failed to broadcast agent event: {e}")

    def _audit_turn(self, thread: AgentThread, turn: AgentTurn, actor: Dict[str, Any]) -> None:
        metadata = {
            "role": turn.role,
            "action": turn.action,
            "duration_ms": round(turn.duration_ms(), 2),
            "metrics": dict(turn.metrics),
        }
        subject = {"thread_id": thread.thread_id, "case_id": thread.case_id, "turn_role": turn.role}
        self._audit_agents_event(
            action=f"agents.turn.{turn.role}",
            outcome="success",
            subject=subject,
            metadata=metadata,
            actor=actor,
            correlation_id=thread.thread_id,
        )

    def _safe_audit(self, event: AuditEvent) -> None:
        try:
            self.audit.append(event)
        except Exception:  # pragma: no cover - guard rail for audit persistence
            logging.getLogger("backend.services.agents").exception(
                "Failed to append agents audit event",
                extra={"category": event.category, "action": event.action},
            )


_AGENTS_SERVICE: AgentsService | None = None


def get_agents_service() -> AgentsService:
    global _AGENTS_SERVICE  # noqa: PLW0603
    if _AGENTS_SERVICE is None:
        _AGENTS_SERVICE = AgentsService()
    return _AGENTS_SERVICE


def reset_agents_service() -> None:
    global _AGENTS_SERVICE  # noqa: PLW0603
    _AGENTS_SERVICE = None
