from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

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
        cursor: Optional[str] = None,
        limit: int = 20,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        entity: Optional[str] = None,
    ) -> TimelineQueryResult:
        from_ts = self._ensure_naive_timestamp(from_ts, "from_ts")
        to_ts = self._ensure_naive_timestamp(to_ts, "to_ts")
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

        events = self._filter_by_time(events, from_ts, to_ts)
        if entity:
            events = self._filter_by_entity(events, entity)
        if cursor:
            cursor_ts, cursor_id = self._decode_cursor(cursor)
            events = [event for event in events if self._after_cursor(event, cursor_ts, cursor_id)]

        limited = events[:bounded_limit]
        has_more = len(events) > bounded_limit
        next_cursor = self._encode_cursor(limited[-1]) if has_more and limited else None

        attributes = {
            "entity_filter": bool(entity),
            "range_filter": bool(from_ts or to_ts),
        }
        _timeline_query_counter.add(1, attributes=attributes)
        if attributes["entity_filter"] or attributes["range_filter"]:
            _timeline_filter_counter.add(1, attributes=attributes)
        if stats.highlights:
            _timeline_enrichment_counter.add(
                stats.highlights,
                attributes={"documents": stats.documents, "relations": stats.relations},
            )

        return TimelineQueryResult(events=limited, next_cursor=next_cursor, limit=bounded_limit, has_more=has_more)

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
            if (
                event.entity_highlights != highlights
                or event.relation_tags != relations
                or (event.confidence or 0.0) != (confidence or 0.0)
            ):
                mutated = True
                enriched.append(
                    replace(
                        event,
                        entity_highlights=highlights,
                        relation_tags=relations,
                        confidence=confidence,
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


def get_timeline_service() -> TimelineService:
    return TimelineService()
