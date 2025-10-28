from __future__ import annotations

from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse

from .config import get_settings
from .telemetry import setup_telemetry
from .models.api import (
    AgentRunRequest,
    AgentRunResponse,
    AgentThreadListResponse,
    ForensicsResponse,
    GraphEdgeModel,
    GraphNeighborResponse,
    GraphNodeModel,
    IngestionRequest,
    IngestionResponse,
    IngestionStatusResponse,
    QueryResponse,
    TimelineEventModel,
    TimelinePaginationModel,
    TimelineResponse,
)
from .services.agents import AgentsService, get_agents_service
from .services.forensics import ForensicsService, get_forensics_service
from .services.graph import GraphService, get_graph_service
from .services.ingestion import (
    IngestionService,
    get_ingestion_service,
    get_ingestion_worker,
    shutdown_ingestion_worker,
)
from .services.retrieval import RetrievalService, get_retrieval_service
from .services.timeline import TimelineService, get_timeline_service
from .security.authz import Principal
from .security.dependencies import (
    authorize_agents_read,
    authorize_agents_run,
    authorize_forensics_document,
    authorize_forensics_financial,
    authorize_forensics_image,
    authorize_graph_read,
    authorize_ingest_enqueue,
    authorize_ingest_status,
    authorize_query,
    authorize_timeline,
    create_mtls_config,
)
from .security.mtls import MTLSMiddleware

settings = get_settings()
setup_telemetry(settings)
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(MTLSMiddleware, config=create_mtls_config())


@app.on_event("startup")
def start_background_workers() -> None:
    get_ingestion_worker()


@app.on_event("shutdown")
def stop_background_workers() -> None:
    shutdown_ingestion_worker(timeout=5.0)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest(
    payload: IngestionRequest,
    service: IngestionService = Depends(get_ingestion_service),
    principal: Principal = Depends(authorize_ingest_enqueue),
) -> JSONResponse:
    job_id = service.ingest(payload)
    job_record = service.get_job(job_id)
    response = IngestionResponse(job_id=job_id, status=job_record.get("status", "queued"))
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(mode="json"),
    )


@app.get("/ingest/{job_id}", response_model=IngestionStatusResponse)
def ingest_status(
    job_id: str,
    service: IngestionService = Depends(get_ingestion_service),
    principal: Principal = Depends(authorize_ingest_status),
) -> JSONResponse:
    try:
        record = service.get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found") from exc
    response = IngestionStatusResponse(**record)
    if "ResearchAnalyst" in principal.roles and response.status not in {"succeeded", "failed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Research analysts may only access completed ingestion runs",
        )
    terminal_statuses = {"succeeded", "failed", "cancelled"}
    status_code = status.HTTP_200_OK if response.status in terminal_statuses else status.HTTP_202_ACCEPTED
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))


@app.get("/query", response_model=QueryResponse)
def query(
    q: str = Query(..., min_length=3, description="Natural language query"),
    page: int = Query(1, ge=1, description="Page number for vector results"),
    page_size: int = Query(10, ge=1, le=50, description="Vector results per page"),
    filters_source: str | None = Query(
        default=None,
        alias="filters[source]",
        description="Restrict results to an ingestion source type (local, s3, sharepoint)",
    ),
    filters_entity: str | None = Query(
        default=None,
        alias="filters[entity]",
        description="Restrict results to documents mentioning an entity label or ID",
    ),
    rerank: bool = Query(
        default=False, description="Enable deterministic reranking heuristics"
    ),
    service: RetrievalService = Depends(get_retrieval_service),
    principal: Principal = Depends(authorize_query),
) -> Response:
    filters: dict[str, str] = {}
    if filters_source:
        filters["source"] = filters_source
    if filters_entity:
        filters["entity"] = filters_entity
    try:
        result = service.query(
            q,
            page=page,
            page_size=page_size,
            filters=filters or None,
            rerank=rerank,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not result.has_evidence:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    payload = result.to_dict()
    if "CaseCoordinator" in principal.roles and "query:trace" not in principal.scopes:
        payload["traces"] = {"vector": [], "graph": {"nodes": [], "edges": []}, "forensics": []}
    return JSONResponse(content=payload)


@app.get("/timeline", response_model=TimelineResponse)
def timeline(
    service: TimelineService = Depends(get_timeline_service),
    principal: Principal = Depends(authorize_timeline),
    cursor: str | None = Query(default=None, description="Opaque pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of events to return"),
    from_ts: datetime | None = Query(default=None, description="Return events on/after this timestamp"),
    to_ts: datetime | None = Query(default=None, description="Return events on/before this timestamp"),
    entity: str | None = Query(default=None, description="Filter events by entity identifier or label"),
) -> TimelineResponse:
    try:
        result = service.list_events(cursor=cursor, limit=limit, from_ts=from_ts, to_ts=to_ts, entity=entity)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    meta = TimelinePaginationModel(cursor=result.next_cursor, limit=result.limit, has_more=result.has_more)
    return TimelineResponse(
        events=[
            TimelineEventModel(
                id=event.id,
                ts=event.ts,
                title=event.title,
                summary=event.summary,
                citations=event.citations,
                entity_highlights=event.entity_highlights,
                relation_tags=event.relation_tags,
                confidence=event.confidence,
            )
            for event in result.events
        ],
        meta=meta,
    )


@app.get("/graph/neighbor", response_model=GraphNeighborResponse)
def graph_neighbor(
    id: str,
    service: GraphService = Depends(get_graph_service),
    principal: Principal = Depends(authorize_graph_read),
) -> GraphNeighborResponse:
    try:
        nodes, edges = service.neighbors(id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Node {id} not found") from exc
    return GraphNeighborResponse(
        nodes=[GraphNodeModel(id=node.id, type=node.type, properties=node.properties) for node in nodes],
        edges=[
            GraphEdgeModel(
                source=edge.source,
                target=edge.target,
                type=edge.type,
                properties=edge.properties,
            )
            for edge in edges
        ],
    )


def _load_forensics(
    service: ForensicsService,
    file_id: str,
    artifact: str,
    principal: Principal,
) -> ForensicsResponse:
    try:
        payload = service.load_artifact(file_id, artifact)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if payload.get("fallback_applied") and not payload.get("data"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Forensics analyzer unavailable for artifact {artifact}",
        )
    response = ForensicsResponse(
        summary=payload.get("summary", ""),
        data=payload.get("data", {}),
        metadata=payload.get("metadata", {}),
        signals=payload.get("signals", []),
        stages=payload.get("stages", []),
        fallback_applied=payload.get("fallback_applied", False),
        schema_version=payload.get("schema_version", "unknown"),
        generated_at=payload.get("generated_at"),
    )
    return response


@app.get("/forensics/document", response_model=ForensicsResponse)
def forensics_document(
    id: str,
    service: ForensicsService = Depends(get_forensics_service),
    principal: Principal = Depends(authorize_forensics_document),
) -> ForensicsResponse:
    return _load_forensics(service, id, "document", principal)


@app.get("/forensics/image", response_model=ForensicsResponse)
def forensics_image(
    id: str,
    service: ForensicsService = Depends(get_forensics_service),
    principal: Principal = Depends(authorize_forensics_image),
) -> ForensicsResponse:
    return _load_forensics(service, id, "image", principal)


@app.get("/forensics/financial", response_model=ForensicsResponse)
def forensics_financial(
    id: str,
    service: ForensicsService = Depends(get_forensics_service),
    principal: Principal = Depends(authorize_forensics_financial),
) -> ForensicsResponse:
    return _load_forensics(service, id, "financial", principal)


@app.post("/agents/run", response_model=AgentRunResponse)
def agents_run(
    payload: AgentRunRequest,
    service: AgentsService = Depends(get_agents_service),
    principal: Principal = Depends(authorize_agents_run),
) -> AgentRunResponse:
    top_k = payload.top_k or 5
    response = service.run_case(payload.case_id, payload.question, top_k=top_k)
    return AgentRunResponse(**response)


@app.get("/agents/threads/{thread_id}", response_model=AgentRunResponse)
def agents_thread(
    thread_id: str,
    service: AgentsService = Depends(get_agents_service),
    principal: Principal = Depends(authorize_agents_read),
) -> AgentRunResponse:
    try:
        payload = service.get_thread(thread_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AgentRunResponse(**payload)


@app.get("/agents/threads", response_model=AgentThreadListResponse)
def agents_threads(
    service: AgentsService = Depends(get_agents_service),
    principal: Principal = Depends(authorize_agents_read),
) -> AgentThreadListResponse:
    threads = service.list_threads()
    return AgentThreadListResponse(threads=threads)

