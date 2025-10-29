from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse

from .config import get_settings
from .telemetry import setup_telemetry
from .telemetry.billing import (
    BILLING_PLANS,
    BillingEventType,
    export_customer_health,
    export_plan_catalogue,
    record_billing_event,
)
from .models.api import (
    AgentRunRequest,
    AgentRunResponse,
    AgentThreadListResponse,
    BillingPlanListResponse,
    BillingUsageResponse,
    ForensicsResponse,
    GraphEdgeModel,
    GraphNeighborResponse,
    GraphNodeModel,
    IngestionRequest,
    IngestionResponse,
    IngestionStatusResponse,
    OnboardingSubmission,
    OnboardingSubmissionResponse,
    QueryResponse,
    TimelineEventModel,
    TimelinePaginationModel,
    TimelineResponse,
)
from .services.agents import AgentsService, get_agents_service
from .services.errors import WorkflowException, http_status_for_error
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
    authorize_billing_admin,
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


def _raise_workflow_exception(exc: WorkflowException) -> None:
    status_code = exc.status_code or http_status_for_error(exc.error)
    raise HTTPException(status_code=status_code, detail=exc.error.to_dict()) from exc


@app.on_event("startup")
def start_background_workers() -> None:
    get_ingestion_worker()
    get_agents_service()


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
    job_id = service.ingest(payload, principal=principal)
    job_record = service.get_job(job_id)
    record_billing_event(
        principal,
        BillingEventType.INGESTION,
        units=float(max(1, len(payload.sources))),
        attributes={
            "job_id": job_id,
            "source_types": sorted({source.type for source in payload.sources}),
        },
    )
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
    if "ResearchAnalyst" in principal.roles:
        privileged_roles = {
            "CaseCoordinator",
            "PlatformEngineer",
            "ForensicsOperator",
            "AutomationService",
            "ComplianceAuditor",
        }
        if set(principal.roles).isdisjoint(privileged_roles) and response.status not in {
            "succeeded",
            "failed",
            "cancelled",
        }:
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
    started = time.perf_counter()
    try:
        result = service.query(
            q,
            page=page,
            page_size=page_size,
            filters=filters or None,
            rerank=rerank,
        )
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    latency_ms = (time.perf_counter() - started) * 1000.0
    if not result.has_evidence:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    payload = result.to_dict()
    if "CaseCoordinator" in principal.roles and "query:trace" not in principal.scopes:
        payload["traces"] = {"vector": [], "graph": {"nodes": [], "edges": []}, "forensics": []}
    record_billing_event(
        principal,
        BillingEventType.QUERY,
        attributes={
            "latency_ms": latency_ms,
            "page": page,
            "page_size": page_size,
            "filters": bool(filters),
            "rerank": rerank,
            "has_evidence": result.has_evidence,
        },
    )
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
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    meta = TimelinePaginationModel(cursor=result.next_cursor, limit=result.limit, has_more=result.has_more)
    record_billing_event(
        principal,
        BillingEventType.TIMELINE,
        attributes={
            "limit": limit,
            "cursor": bool(cursor),
            "entity": bool(entity),
            "from_ts": bool(from_ts),
            "to_ts": bool(to_ts),
        },
    )
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
    response = service.run_case(payload.case_id, payload.question, top_k=top_k, principal=principal)
    payload_model = AgentRunResponse(**response)
    record_billing_event(
        principal,
        BillingEventType.AGENT,
        attributes={
            "case_id": payload.case_id,
            "thread_id": payload_model.thread_id,
            "turns": len(payload_model.turns),
        },
    )
    return payload_model
    try:
        response = service.run_case(payload.case_id, payload.question, top_k=top_k, principal=principal)
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
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


@app.get("/billing/plans", response_model=BillingPlanListResponse)
def billing_plans() -> BillingPlanListResponse:
    plans = export_plan_catalogue()
    return BillingPlanListResponse(
        generated_at=datetime.now(timezone.utc),
        plans=plans,
    )


@app.get("/billing/usage", response_model=BillingUsageResponse)
def billing_usage(
    principal: Principal = Depends(authorize_billing_admin),
) -> BillingUsageResponse:
    _ = principal  # ensure dependency evaluation for auditing
    tenants = export_customer_health()
    return BillingUsageResponse(
        generated_at=datetime.now(timezone.utc),
        tenants=tenants,
    )


def _recommend_plan(submission: OnboardingSubmission) -> str:
    seat_count = submission.seats
    matters = submission.estimated_matters_per_month
    automation_target = submission.automation_target_percent or 0.25
    projected_queries = max(500, seat_count * max(5, matters) * max(0.1, automation_target) * 4)
    if seat_count <= 10 and projected_queries <= BILLING_PLANS["community"].included_queries:
        return "community"
    if seat_count <= 40 and projected_queries <= BILLING_PLANS["professional"].included_queries:
        return "professional"
    return "enterprise"


@app.post("/onboarding", response_model=OnboardingSubmissionResponse, status_code=status.HTTP_201_CREATED)
def onboarding_submission(payload: OnboardingSubmission) -> OnboardingSubmissionResponse:
    recommended_plan = _recommend_plan(payload)
    record_billing_event(
        None,
        BillingEventType.SIGNUP,
        attributes={
            "tenant_id": payload.tenant_id,
            "organization": payload.organization,
            "contact_email": payload.contact_email,
            "contact_name": payload.contact_name,
            "primary_use_case": payload.primary_use_case,
            "departments": payload.departments,
            "roi_hours": payload.roi_baseline_hours_per_matter,
            "matters_per_month": payload.estimated_matters_per_month,
            "automation_target": payload.automation_target_percent,
            "go_live_date": payload.go_live_date.isoformat() if payload.go_live_date else None,
            "notes": payload.notes,
            "success_criteria": payload.success_criteria,
            "seats": payload.seats,
            "completed": True,
            "recommended_plan": recommended_plan,
        },
    )
    return OnboardingSubmissionResponse(
        tenant_id=payload.tenant_id,
        recommended_plan=recommended_plan,
        message="Onboarding submission recorded",
        received_at=datetime.now(timezone.utc),
    )

