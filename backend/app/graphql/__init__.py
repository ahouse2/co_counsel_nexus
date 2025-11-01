from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from ariadne import QueryType, gql, make_executable_schema
from ariadne.asgi import GraphQL

from ..services.errors import WorkflowException
from ..services.timeline import TimelineService, get_timeline_service


type_defs = gql(
    """
    type OutcomeProbability {
        label: String!
        probability: Float!
    }

    type EntityHighlight {
        id: String!
        label: String!
        type: String!
        doc: String
    }

    type RelationTag {
        source: String
        target: String
        type: String
        label: String
        doc: String
    }

    type TimelineEvent {
        id: ID!
        ts: String!
        title: String!
        summary: String!
        citations: [String!]!
        entityHighlights: [EntityHighlight!]!
        relationTags: [RelationTag!]!
        confidence: Float
        riskScore: Float
        riskBand: String
        outcomeProbabilities: [OutcomeProbability!]!
        recommendedActions: [String!]!
        motionDeadline: String
    }

    type TimelineMeta {
        cursor: String
        limit: Int!
        hasMore: Boolean!
    }

    type TimelineConnection {
        events: [TimelineEvent!]!
        meta: TimelineMeta!
    }

    type Query {
        timelineEvents(
            cursor: String
            limit: Int
            fromTs: String
            toTs: String
            entity: String
            riskBand: String
            motionDueBefore: String
            motionDueAfter: String
        ): TimelineConnection!
    }
    """
)


query = QueryType()


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _serialize_event(event) -> Dict[str, Any]:
    return {
        "id": event.id,
        "ts": event.ts.isoformat(),
        "title": event.title,
        "summary": event.summary,
        "citations": list(event.citations),
        "entityHighlights": [
            {
                "id": item.get("id"),
                "label": item.get("label"),
                "type": item.get("type"),
                "doc": item.get("doc"),
            }
            for item in event.entity_highlights
        ],
        "relationTags": [
            {
                "source": item.get("source"),
                "target": item.get("target"),
                "type": item.get("type"),
                "label": item.get("label"),
                "doc": item.get("doc"),
            }
            for item in event.relation_tags
        ],
        "confidence": event.confidence,
        "riskScore": event.risk_score,
        "riskBand": event.risk_band,
        "outcomeProbabilities": list(event.outcome_probabilities),
        "recommendedActions": list(event.recommended_actions),
        "motionDeadline": event.motion_deadline.isoformat()
        if event.motion_deadline
        else None,
    }


@query.field("timelineEvents")
def resolve_timeline_events(*_, **kwargs):
    service: TimelineService = get_timeline_service()
    limit = kwargs.get("limit")
    limit_value = int(limit) if isinstance(limit, int) else None
    try:
        result = service.list_events(
            cursor=kwargs.get("cursor"),
            limit=limit_value or 20,
            from_ts=_parse_datetime(kwargs.get("fromTs")),
            to_ts=_parse_datetime(kwargs.get("toTs")),
            entity=kwargs.get("entity"),
            risk_band=kwargs.get("riskBand"),
            motion_due_before=_parse_datetime(kwargs.get("motionDueBefore")),
            motion_due_after=_parse_datetime(kwargs.get("motionDueAfter")),
        )
    except WorkflowException as exc:
        raise exc

    return {
        "events": [_serialize_event(event) for event in result.events],
        "meta": {
            "cursor": result.next_cursor,
            "limit": result.limit,
            "hasMore": result.has_more,
        },
    }


schema = make_executable_schema(type_defs, query)


def _graphql_context(request: Any) -> Dict[str, Any]:
    principal = getattr(request.state, "principal", None)
    return {"request": request, "principal": principal}


graphql_app = GraphQL(schema, context_value=_graphql_context)
