from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from ..config import get_settings
from ..storage.timeline_store import TimelineStore, TimelineEvent
from ..utils.triples import normalise_entity_id
from .graph import GraphService, get_graph_service


@dataclass
class TimelineQueryResult:
    events: List[TimelineEvent]
    next_cursor: Optional[str]
    limit: int
    has_more: bool


class TimelineService:
    def __init__(
        self,
        store: TimelineStore | None = None,
        graph_service: GraphService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.store = store or TimelineStore(self.settings.timeline_path)
        self.graph_service = graph_service or get_graph_service()

    def list_events(
        self,
        *,
        cursor: Optional[str] = None,
        limit: int = 20,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        entity: Optional[str] = None,
    ) -> TimelineQueryResult:
        bounded_limit = self._bounded_limit(limit)
        if from_ts and to_ts and from_ts > to_ts:
            raise ValueError("from_ts must be earlier than to_ts")

        events = self.store.read_all()
        events = self._filter_by_time(events, from_ts, to_ts)
        if entity:
            events = self._filter_by_entity(events, entity)
        if cursor:
            cursor_ts, cursor_id = self._decode_cursor(cursor)
            events = [event for event in events if self._after_cursor(event, cursor_ts, cursor_id)]

        limited = events[:bounded_limit]
        has_more = len(events) > bounded_limit
        next_cursor = self._encode_cursor(limited[-1]) if has_more and limited else None
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

    def _filter_by_entity(self, events: Iterable[TimelineEvent], entity: str) -> List[TimelineEvent]:
        doc_ids = self._collect_citations(events)
        if not doc_ids:
            return []
        mapping = self.graph_service.document_entities(doc_ids)
        if not mapping:
            return []

        target_id = normalise_entity_id(entity)
        target_label = entity.lower()
        allowed_docs: set[str] = set()
        for doc_id, nodes in mapping.items():
            for node in nodes:
                node_label = str(node.properties.get("label", "")).lower()
                if node.id == target_id or target_label in node_label:
                    allowed_docs.add(doc_id)
                    break

        if not allowed_docs:
            return []

        filtered: List[TimelineEvent] = []
        for event in events:
            if any(citation in allowed_docs for citation in event.citations):
                filtered.append(event)
        return filtered

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
            raise ValueError("Invalid cursor") from exc
        return timestamp, event_id

    @staticmethod
    def _after_cursor(event: TimelineEvent, cursor_ts: datetime, cursor_id: str) -> bool:
        if event.ts > cursor_ts:
            return True
        if event.ts < cursor_ts:
            return False
        return event.id > cursor_id


def get_timeline_service() -> TimelineService:
    return TimelineService()

