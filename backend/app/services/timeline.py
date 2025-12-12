from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from math import exp
from typing import Dict, Iterable, List, Optional, Tuple, Any
import json

from opentelemetry import metrics

from ..config import get_settings
from ..storage.timeline_store import TimelineStore, TimelineEvent
from ..utils.triples import normalise_entity_id
from .errors import WorkflowAbort, WorkflowComponent, WorkflowError, WorkflowSeverity
from .graph import GraphNode, GraphService, get_graph_service

_meter = metrics.get_meter(__name__)
_timeline_query_counter = _meter.create_counter(
    "timeline_queries_total",
    unit="1",
    description="Total number of timeline queries served",
)
_timeline_filter_counter = _meter.create_counter(
    "timeline_filter_applications_total",
    unit="1",
    description="Number of timeline queries with filters applied",
)
_timeline_enrichment_counter = _meter.create_counter(
    "timeline_enrichment_entities_total",
    unit="1",
    description="Entity highlights generated for timeline events",
)


@dataclass
class TimelineQueryResult:
    events: List[TimelineEvent]
    next_cursor: Optional[str]
    limit: int
    has_more: bool


@dataclass
class EnrichmentStats:
    mutated: bool
    documents: int
    highlights: int
    relations: int


class TimelineService:
    def __init__(
        self,
        *,
        store: TimelineStore | None = None,
        graph_service: GraphService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.store = store or TimelineStore(self.settings.timeline_path)
        self.graph_service = graph_service or get_graph_service()

    def refresh_enrichments(self) -> EnrichmentStats:
        events = self.store.read_all()
        enriched, stats = self._enrich_events(events)
        if stats.mutated:
            self.store.write_all(enriched)
        return stats

    def list_events(
        self,
        *,
        case_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 20,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        entity: Optional[str] = None,
        risk_band: Optional[str] = None,
        motion_due_before: Optional[datetime] = None,
        motion_due_after: Optional[datetime] = None,
    ) -> TimelineQueryResult:

        from_ts = self._ensure_naive_timestamp(from_ts, "from_ts")
        to_ts = self._ensure_naive_timestamp(to_ts, "to_ts")
        motion_due_before = self._ensure_naive_timestamp(motion_due_before, "motion_due_before")
        motion_due_after = self._ensure_naive_timestamp(motion_due_after, "motion_due_after")
        bounded_limit = self._bounded_limit(limit)
        if from_ts and to_ts and from_ts > to_ts:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.TIMELINE,
                    code="TIMELINE_INVALID_RANGE",
                    message="from_ts must be earlier than to_ts",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                    context={"from_ts": from_ts.isoformat(), "to_ts": to_ts.isoformat()},
                ),
                status_code=400,
            )

        events = self.store.read_all()
        enriched_events, stats = self._enrich_events(events)
        events = enriched_events
        if stats.mutated:
            self.store.write_all(events)

        if case_id:
            events = self._filter_by_case_id(events, case_id)

        events = self._filter_by_time(events, from_ts, to_ts)
        if entity:
            events = self._filter_by_entity(events, entity)
        if risk_band:
            events = self._filter_by_risk_band(events, risk_band)
        if motion_due_before or motion_due_after:
            events = self._filter_by_motion_deadline(
                events,
                due_before=motion_due_before,
                due_after=motion_due_after,
            )
        if cursor:
            cursor_ts, cursor_id = self._decode_cursor(cursor)
            events = [event for event in events if self._after_cursor(event, cursor_ts, cursor_id)]

        limited = events[:bounded_limit]
        has_more = len(events) > bounded_limit
        next_cursor = self._encode_cursor(limited[-1]) if has_more and limited else None

        attributes = {
            "entity_filter": bool(entity),
            "range_filter": bool(from_ts or to_ts),
            "risk_filter": bool(risk_band),
            "deadline_filter": bool(motion_due_before or motion_due_after),
        }
        _timeline_query_counter.add(1, attributes=attributes)
        if any(attributes.values()):
            _timeline_filter_counter.add(1, attributes=attributes)
        if stats.highlights:
            _timeline_enrichment_counter.add(
                stats.highlights,
                attributes={"documents": stats.documents, "relations": stats.relations},
            )

        return TimelineQueryResult(events=limited, next_cursor=next_cursor, limit=bounded_limit, has_more=has_more)

    def create_event(self, text: str, case_id: str, event_type: str = "fact") -> TimelineEvent:
        """
        Creates a new timeline event from text.
        """
        from uuid import uuid4
        
        # Simple parsing or just use text as description/title
        # In a real system, we might use an LLM here to extract date/title/summary
        # For now, we'll create a basic event at current time
        
        event = TimelineEvent(
            id=str(uuid4()),
            case_id=case_id,
            ts=datetime.now(timezone.utc),
            title="Manual Event",
            summary=text,
            citations=[],
            risk_score=0.0,
            risk_band="low",
            event_type=event_type,
            related_event_ids=[]
        )
        
        # Enrich the event immediately?
        # For now just save it
        self.store.append([event])
        return event

    @staticmethod
    def _filter_by_case_id(events: Iterable[TimelineEvent], case_id: str) -> List[TimelineEvent]:
        return [e for e in events if e.case_id == case_id]


    @staticmethod
    def _bounded_limit(limit: int) -> int:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        return limit

    @staticmethod
    def _filter_by_time(
        events: Iterable[TimelineEvent],
        from_ts: Optional[datetime],
        to_ts: Optional[datetime],
    ) -> List[TimelineEvent]:
        result: List[TimelineEvent] = []
        for event in events:
            if from_ts and event.ts < from_ts:
                continue
            if to_ts and event.ts > to_ts:
                continue
            result.append(event)
        return result

    @staticmethod
    def _ensure_naive_timestamp(value: Optional[datetime], label: str) -> Optional[datetime]:
        if value is None:
            return None
        tzinfo = value.tzinfo
        if tzinfo is None or tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=None)
        raise WorkflowAbort(
            WorkflowError(
                component=WorkflowComponent.TIMELINE,
                code="TIMELINE_TIMEZONE_AWARE",
                message=f"{label} must be timezone-naive",
                severity=WorkflowSeverity.ERROR,
                retryable=False,
                context={"label": label},
            ),
            status_code=400,
        )

    def _filter_by_entity(self, events: Iterable[TimelineEvent], entity: str) -> List[TimelineEvent]:
        doc_ids = self._collect_citations(events)
        if not doc_ids:
            return []

        target_id = normalise_entity_id(entity)
        target_label = entity.lower()
        filtered: List[TimelineEvent] = []

        for event in events:
            if any(
                highlight.get("id") == target_id
                or target_label in str(highlight.get("label", "")).lower()
                for highlight in event.entity_highlights
            ):
                filtered.append(event)

        if filtered:
            return filtered

        mapping = self.graph_service.document_entities(doc_ids)
        if not mapping:
            return []

        allowed_docs: set[str] = set()
        for doc_id, nodes in mapping.items():
            for node in nodes:
                node_label = str(node.properties.get("label", "")).lower()
                if node.id == target_id or target_label in node_label:
                    allowed_docs.add(doc_id)
                    break

        if not allowed_docs:
            return []

        return [event for event in events if any(citation in allowed_docs for citation in event.citations)]

    @staticmethod
    def _collect_citations(events: Iterable[TimelineEvent]) -> List[str]:
        seen: dict[str, None] = {}
        for event in events:
            for citation in event.citations:
                if citation not in seen:
                    seen[citation] = None
        return list(seen.keys())

    @staticmethod
    def _encode_cursor(event: TimelineEvent) -> str:
        payload = f"{event.ts.isoformat()}|{event.id}"
        encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
        return encoded.rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> Tuple[datetime, str]:
        padded = cursor + "=" * (-len(cursor) % 4)
        try:
            raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            ts_str, event_id = raw.split("|", 1)
            timestamp = datetime.fromisoformat(ts_str)
        except (ValueError, binascii.Error) as exc:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.TIMELINE,
                    code="TIMELINE_CURSOR_INVALID",
                    message="Invalid cursor",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                    context={"cursor": cursor},
                ),
                status_code=400,
            ) from exc
        return timestamp, event_id

    @staticmethod
    def _after_cursor(event: TimelineEvent, cursor_ts: datetime, cursor_id: str) -> bool:
        if event.ts > cursor_ts:
            return True
        if event.ts < cursor_ts:
            return False
        return event.id > cursor_id

    def _enrich_events(self, events: List[TimelineEvent]) -> Tuple[List[TimelineEvent], EnrichmentStats]:
        if not events:
            return events, EnrichmentStats(mutated=False, documents=0, highlights=0, relations=0)
        doc_ids = self._collect_citations(events)
        if not doc_ids:
            return events, EnrichmentStats(mutated=False, documents=0, highlights=0, relations=0)

        mapping = self.graph_service.document_entities(doc_ids)
        if not mapping:
            return events, EnrichmentStats(mutated=False, documents=len(doc_ids), highlights=0, relations=0)

        relation_cache: Dict[str, List[Dict[str, str]]] = {}
        mutated = False
        highlight_count = 0
        relation_count = 0
        enriched: List[TimelineEvent] = []

        for event in events:
            highlights = self._build_highlights(event, mapping)
            relations = self._build_relations(event, highlights, relation_cache)
            highlight_count += len(highlights)
            relation_count += len(relations)
            confidence = self._compute_confidence(len(highlights), len(relations))
            (
                risk_score,
                risk_band,
                outcome_probabilities,
                recommended_actions,
                motion_deadline,
            ) = self._forecast_risk(event, highlights, relations)
            if (
                event.entity_highlights != highlights
                or event.relation_tags != relations
                or (event.confidence or 0.0) != (confidence or 0.0)
                or (event.risk_score or 0.0) != (risk_score or 0.0)
                or (event.risk_band or "") != (risk_band or "")
                or event.outcome_probabilities != outcome_probabilities
                or event.recommended_actions != recommended_actions
                or self._deadline_changed(event.motion_deadline, motion_deadline)
            ):
                mutated = True
                enriched.append(
                    replace(
                        event,
                        entity_highlights=highlights,
                        relation_tags=relations,
                        confidence=confidence,
                        risk_score=risk_score,
                        risk_band=risk_band,
                        outcome_probabilities=outcome_probabilities,
                        recommended_actions=recommended_actions,
                        motion_deadline=motion_deadline,
                    )
                )
            else:
                enriched.append(event)

        return enriched, EnrichmentStats(
            mutated=mutated,
            documents=len(mapping),
            highlights=highlight_count,
            relations=relation_count,
        )

    def _build_highlights(
        self, event: TimelineEvent, mapping: Dict[str, List[GraphNode]]
    ) -> List[Dict[str, str]]:
        highlights: Dict[str, Dict[str, str]] = {}
        for doc_id in event.citations:
            for node in mapping.get(doc_id, []):
                label = str(node.properties.get("label") or node.properties.get("name") or node.id)
                key = f"{node.id}:{doc_id}"
                highlights[key] = {
                    "id": node.id,
                    "label": label,
                    "type": node.type,
                    "doc": doc_id,
                }
        return list(highlights.values())

    def _build_relations(
        self,
        event: TimelineEvent,
        highlights: List[Dict[str, str]],
        cache: Dict[str, List[Dict[str, str]]],
    ) -> List[Dict[str, str]]:
        relations: List[Dict[str, str]] = []
        citation_scope = set(event.citations)
        for highlight in highlights:
            entity_id = highlight["id"]
            if entity_id not in cache:
                cache[entity_id] = self._load_entity_relations(entity_id, citation_scope)
            relations.extend(cache.get(entity_id, []))
        dedup: Dict[Tuple[str, str, str, Optional[str]], Dict[str, str]] = {}
        for relation in relations:
            key = (
                relation.get("source", ""),
                relation.get("target", ""),
                relation.get("type", ""),
                relation.get("doc"),
            )
            dedup[key] = relation
        return list(dedup.values())

    def _load_entity_relations(
        self, entity_id: str, citation_scope: set[str]
    ) -> List[Dict[str, str]]:
        relations: List[Dict[str, str]] = []
        try:
            _, edges = self.graph_service.neighbors(entity_id)
        except KeyError:
            return relations
        for edge in edges:
            doc_id = edge.properties.get("doc_id")
            if doc_id and doc_id not in citation_scope:
                continue
            label = str(edge.properties.get("predicate") or edge.properties.get("label") or edge.type)
            relations.append(
                {
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.type,
                    "label": label,
                    "doc": str(doc_id) if doc_id is not None else None,
                }
            )
        return relations

    @staticmethod
    def _compute_confidence(entities: int, relations: int) -> float | None:
        if entities == 0 and relations == 0:
            return None
        base = 0.45 if entities else 0.25
        base += min(entities * 0.08, 0.25)
        base += min(relations * 0.05, 0.2)
        return round(min(base, 0.99), 2)

    @staticmethod
    def _deadline_changed(left: Optional[datetime], right: Optional[datetime]) -> bool:
        if left is None and right is None:
            return False
        if left is None or right is None:
            return True
        return left != right

    def _filter_by_risk_band(
        self, events: Iterable[TimelineEvent], risk_band: str
    ) -> List[TimelineEvent]:
        normalized = risk_band.lower()
        if normalized not in {"low", "medium", "high"}:
            raise WorkflowAbort(
                WorkflowError(
                    component=WorkflowComponent.TIMELINE,
                    code="TIMELINE_RISK_BAND_INVALID",
                    message="Unsupported risk band",
                    severity=WorkflowSeverity.ERROR,
                    retryable=False,
                    context={"risk_band": risk_band},
                ),
                status_code=400,
            )
        return [event for event in events if (event.risk_band or "").lower() == normalized]

    @staticmethod
    def _filter_by_motion_deadline(
        events: Iterable[TimelineEvent],
        *,
        due_before: Optional[datetime],
        due_after: Optional[datetime],
    ) -> List[TimelineEvent]:
        filtered: List[TimelineEvent] = []
        for event in events:
            if not event.motion_deadline:
                continue
            if due_before and event.motion_deadline >= due_before:
                continue
            if due_after and event.motion_deadline <= due_after:
                continue
            filtered.append(event)
        return filtered

    def _forecast_risk(
        self,
        event: TimelineEvent,
        highlights: List[Dict[str, str]],
        relations: List[Dict[str, str]],
    ) -> Tuple[
        Optional[float],
        Optional[str],
        List[Dict[str, object]],
        List[str],
        Optional[datetime],
    ]:
        text = f"{event.title} {event.summary}".lower()
        severity_feature = 1.0 if any(
            token in text
            for token in (
                "investigation",
                "fraud",
                "penalty",
                "violation",
                "sanction",
                "breach",
            )
        ) else 0.0
        motion_feature = 1.0 if "motion" in text else 0.0
        deadline_feature = 1.0 if any(token in text for token in ("deadline", "due", "hearing")) else 0.0
        highlight_feature = min(len(highlights) / 5.0, 1.0)
        relation_feature = min(len(relations) / 5.0, 1.0)
        citation_feature = min(len(event.citations) / 5.0, 1.0)
        now = datetime.now(timezone.utc)
        event_ts = event.ts
        if event_ts.tzinfo is None:
            event_ts = event_ts.replace(tzinfo=timezone.utc)
        else:
            event_ts = event_ts.astimezone(timezone.utc)
        recency_days = max((now - event_ts).days, 0)
        recency_feature = 1.0 - min(recency_days / 365.0, 1.0)

        logit = (
            -1.0
            + 1.6 * severity_feature
            + 1.2 * motion_feature
            + 0.9 * deadline_feature
            + 0.7 * highlight_feature
            + 0.5 * relation_feature
            + 0.45 * citation_feature
            + 0.8 * recency_feature
        )
        risk_score = round(1.0 / (1.0 + exp(-logit)), 2)
        if risk_score < 0.0:
            risk_score = 0.0
        if risk_score > 1.0:
            risk_score = 1.0
        if risk_score < 0.33:
            risk_band = "low"
        elif risk_score < 0.66:
            risk_band = "medium"
        else:
            risk_band = "high"

        adverse_raw = 0.4 + risk_score
        favorable_raw = 0.3 + (1.0 - risk_score)
        settlement_raw = 0.2 + (1.0 - abs(0.5 - risk_score))
        total = adverse_raw + favorable_raw + settlement_raw
        outcome_probabilities = [
            {
                "label": "Adverse outcome",
                "probability": round(adverse_raw / total, 2),
            },
            {
                "label": "Favorable outcome",
                "probability": round(favorable_raw / total, 2),
            },
            {
                "label": "Settlement",
                "probability": round(settlement_raw / total, 2),
            },
        ]

        recommended_actions: List[str] = []
        if risk_band == "high":
            recommended_actions.append("Escalate to lead counsel for immediate review.")
            recommended_actions.append("Prepare contingency brief addressing adverse arguments.")
        elif risk_band == "medium":
            recommended_actions.append("Schedule strategy check-in with litigation team.")
        else:
            recommended_actions.append("Monitor for new evidence and maintain current course.")

        motion_deadline: Optional[datetime] = None
        if motion_feature:
            base_days = 21
            if "summary judgment" in text or "dismiss" in text:
                base_days = 28
            if "emergency" in text or "expedited" in text:
                base_days = 7
            if "hearing" in text or "oral argument" in text:
                base_days = min(base_days, 14)
            motion_deadline = event.ts + timedelta(days=base_days)

        if motion_deadline:
            days_remaining = (motion_deadline - now).days
            if days_remaining <= 10:
                recommended_actions.append(
                    "Prioritize filings before motion deadline."
                )

        return risk_score, risk_band, outcome_probabilities, recommended_actions, motion_deadline


    def generate_timeline_from_prompt(self, prompt: str, case_id: str) -> List[TimelineEvent]:
        """
        Generates timeline events by querying the knowledge graph using the provided prompt.
        """
        # 1. Initialize LLM Service
        from backend.ingestion.llama_index_factory import create_llm_service
        from backend.ingestion.settings import build_runtime_config
        
        settings = get_settings()
        runtime_config = build_runtime_config(settings)
        llm_service = create_llm_service(runtime_config.llm)

        # 2. Initialize GraphManagerAgent
        from backend.app.agents.graph_manager import GraphManagerAgent
        from backend.app.agents.context import AgentContext
        from backend.app.agents.memory import CaseThreadMemory
        from backend.app.agents.types import AgentThread
        from backend.app.storage.agent_memory_store import AgentMemoryStore
        from backend.app.services.graph import get_graph_service
        from uuid import uuid4
        
        graph_service = get_graph_service()
        agent = GraphManagerAgent(
            graph_service=graph_service,
            timeline_store=self.store,
            llm_service=llm_service
        )

        # 3. Create a temporary AgentContext
        # We need to construct a real-ish memory structure because the agent interacts with it.
        # We'll use a temporary memory store location or just the default one but with a temp thread ID.
        memory_store = AgentMemoryStore(settings.agent_threads_dir)
        thread_id = f"timeline-gen-{uuid4()}"
        
        thread = AgentThread(
            thread_id=thread_id,
            case_id=case_id,
            question=prompt,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        memory = CaseThreadMemory(
            thread=thread,
            store=memory_store
        )

        context = AgentContext(
            case_id=case_id,
            question=prompt,
            top_k=5, # Default
            actor={"id": "timeline-api", "roles": ["user"]},
            memory=memory,
            telemetry={}
        )

        # 4. Generate Insight
        try:
            insight = agent.ensure_insight(context, question=prompt, reuse_existing=False)
            
            # 5. Retrieve the generated event
            if insight.timeline_event_id:
                return [TimelineEvent(
                    id=insight.timeline_event_id,
                    ts=datetime.now(timezone.utc),
                    title=f"Graph Insight: {prompt}",
                    summary=insight.execution.summary.get("text") or "Generated graph insight.",
                    citations=list(insight.execution.documents),
                    risk_score=0.0,
                    risk_band="low"
                )]
            else:
                return []

        except Exception as e:
            print(f"Error generating timeline from prompt: {e}")
            raise e

    def weave_narrative(self, case_id: str) -> List[TimelineEvent]:
        """
        Auto-generates a master timeline from all case documents using the Knowledge Graph.
        """
        # 1. Initialize LLM Service & Graph Agent
        from backend.ingestion.llama_index_factory import create_llm_service
        from backend.ingestion.settings import build_runtime_config
        from backend.app.agents.graph_manager import GraphManagerAgent
        from backend.app.agents.context import AgentContext
        from backend.app.agents.memory import CaseThreadMemory
        from backend.app.agents.types import AgentThread
        from backend.app.storage.agent_memory_store import AgentMemoryStore
        from backend.app.services.graph import get_graph_service
        from uuid import uuid4
        
        settings = get_settings()
        runtime_config = build_runtime_config(settings)
        llm_service = create_llm_service(runtime_config.llm)
        graph_service = get_graph_service()
        
        agent = GraphManagerAgent(
            graph_service=graph_service,
            timeline_store=self.store,
            llm_service=llm_service
        )

        # 2. Create Context
        memory_store = AgentMemoryStore(settings.agent_threads_dir)
        thread_id = f"narrative-gen-{uuid4()}"
        thread = AgentThread(
            thread_id=thread_id,
            case_id=case_id,
            question="Weave narrative",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        memory = CaseThreadMemory(thread=thread, store=memory_store)
        context = AgentContext(
            case_id=case_id,
            question="Weave narrative",
            top_k=5,
            actor={"id": "timeline-api", "roles": ["user"]},
            memory=memory,
            telemetry={}
        )

        # 3. Extract Key Events via Graph
        # We ask the graph agent to find significant events first
        prompt_events = "Find all significant events, meetings, and communications in this case, ordered chronologically."
        try:
            insight = agent.ensure_insight(context, question=prompt_events, reuse_existing=False)
            # The insight execution might have records. We can use them.
            # But for a narrative, we want the LLM to synthesize a story.
        except Exception as e:
            print(f"Graph extraction failed: {e}")
            # Continue with empty context if graph fails

        # 4. Generate Narrative Story
        # We'll use the LLM to write a cohesive story based on the graph insight and timeline events
        existing_events = self.list_events(case_id=case_id, limit=100).events
        events_context = "\n".join([f"- {e.date}: {e.title} ({e.summary})" for e in existing_events])
        
        narrative_prompt = f"""
        You are an expert legal storyteller. Based on the following timeline of events, write a cohesive, compelling narrative of the case.
        
        EVENTS:
        {events_context}
        
        INSTRUCTIONS:
        1. Write a chronological story that weaves these facts together.
        2. Highlight the key themes (e.g., "Betrayal", "Negligence").
        3. Identify any missing pieces or gaps in the story.
        4. Return the result as a JSON object with:
           - "narrative_text": The full story.
           - "themes": List of themes.
           - "gaps": List of identified gaps.
        """
        
        try:
            response = llm_service.complete(narrative_prompt)
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            data = json.loads(text.strip())
            
            # Create a special "Narrative Summary" event
            narrative_event = TimelineEvent(
                id=f"narrative::{uuid4()}",
                case_id=case_id,
                ts=datetime.now(timezone.utc),
                title="Case Narrative",
                summary=data.get("narrative_text", "Narrative generation failed."),
                citations=[],
                risk_score=0.0,
                risk_band="low",
                entity_highlights=[],  # Could add themes here
                relation_tags=[]
            )
            
            # We return this event, and maybe persist it?
            # For now, let's just return it as part of the list
            return [narrative_event]
            
        except Exception as e:
            print(f"Narrative generation failed: {e}")
            return []

    def detect_contradictions(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Analyzes the current timeline for contradictions using the LLM.
        """
        events = self.list_events(case_id=case_id).events
        if not events:
            return []
            
        # 1. Initialize LLM Service
        from backend.ingestion.llama_index_factory import create_llm_service
        from backend.ingestion.settings import build_runtime_config
        
        settings = get_settings()
        runtime_config = build_runtime_config(settings)
        llm_service = create_llm_service(runtime_config.llm)
        
        # 2. Format events for analysis
        # Limit to last 50 events to fit in context for this prototype
        recent_events = sorted(events, key=lambda e: e.ts)[-50:]
        events_text = "\n".join([
            f"ID: {e.id}\nTime: {e.ts}\nTitle: {e.title}\nSummary: {e.summary}\nSources: {e.citations}\n---" 
            for e in recent_events
        ])
        
        prompt = f"""
        You are a meticulous legal analyst. Your job is to find CONTRADICTIONS in the case timeline.
        
        TIMELINE:
        {events_text}
        
        TASK:
        Identify any inconsistencies where:
        1. Two events claim mutually exclusive facts (e.g., Person A was in two places at once).
        2. A witness statement contradicts physical evidence (e.g., timestamps, logs).
        3. The sequence of events is logically impossible.
        
        OUTPUT FORMAT (JSON):
        {{
            "contradictions": [
                {{
                    "title": "Short headline",
                    "description": "Detailed explanation of the conflict.",
                    "event_ids": ["id1", "id2"],
                    "confidence": 0.9,
                    "severity": "high" | "medium" | "low"
                }}
            ]
        }}
        
        If no contradictions are found, return {{"contradictions": []}}.
        """
        
        try:
            response = llm_service.complete(prompt)
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            data = json.loads(text.strip())
            return data.get("contradictions", [])
        except Exception as e:
            print(f"Error detecting contradictions: {e}")
            return []


def get_timeline_service() -> TimelineService:
    return TimelineService()
