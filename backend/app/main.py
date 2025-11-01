from __future__ import annotations

import base64
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    WebSocket,
    Request,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse

from agents.toolkit.sandbox import SandboxExecutionResult

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
    DevAgentApplyRequest,
    DevAgentApplyResponse,
    DevAgentProposalListResponse,
    DevAgentProposalModel,
    DevAgentTaskModel,
    CostEventModel,
    CostSummaryMetricModel,
    CostSummaryResponse,
    ForensicsResponse,
    GraphEdgeModel,
    GraphNeighborResponse,
    GraphNodeModel,
    IngestionRequest,
    IngestionResponse,
    IngestionStatusResponse,
    KnowledgeBookmarkRequest,
    KnowledgeBookmarkResponse,
    KnowledgeLessonDetailResponse,
    KnowledgeLessonListResponse,
    KnowledgeProgressUpdateRequest,
    KnowledgeProgressUpdateResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    OnboardingSubmission,
    OnboardingSubmissionResponse,
    QueryResponse,
    SandboxCommandResultModel,
    SandboxExecutionModel,
    TimelineEventModel,
    TimelinePaginationModel,
    TimelineResponse,
    ScenarioBeatSpecModel,
    ScenarioDefinitionModel,
    ScenarioEvidenceBindingModel,
    ScenarioEvidenceSpecModel,
    ScenarioListResponse,
    ScenarioMetadataModel,
    ScenarioParticipantModel,
    ScenarioRunAudioModel,
    ScenarioRunRequestModel,
    ScenarioRunResponseModel,
    ScenarioRunTurnModel,
    ScenarioVariableModel,
    TextToSpeechRequest,
    TextToSpeechResponse,
    VoicePersonaListResponse,
    VoiceSessionCreateResponse,
    VoiceSessionDetailResponse,
)
from .scenarios.schema import ScenarioDefinition, ScenarioEvidenceRequirement, ScenarioMetadata, ScenarioParticipant, ScenarioVariable
from .services.agents import AgentsService, get_agents_service
from .services.costs import CostEventCategory, CostTrackingService, get_cost_tracking_service
from .services.dev_agent import DevAgentService, get_dev_agent_service
from .services.errors import WorkflowAbort, WorkflowException, http_status_for_error
from .services.forensics import ForensicsService, get_forensics_service
from .services.graph import GraphService, get_graph_service
from .services.ingestion import (
    IngestionService,
    get_ingestion_service,
    get_ingestion_worker,
    shutdown_ingestion_worker,
)
from .services.knowledge import KnowledgeService, get_knowledge_service
from .services.retrieval import RetrievalMode, RetrievalService, get_retrieval_service
from .services.scenarios import (
    ScenarioEvidenceBinding,
    ScenarioRunOptions,
    get_scenario_engine,
)
from .services.timeline import TimelineService, get_timeline_service
from .graphql import graphql_app
from .services.tts import TextToSpeechService, get_tts_service
from .services.voice import VoiceService, VoiceServiceError, VoiceSessionOutcome, get_voice_service
from .security.authz import Principal
from .security.dependencies import (
    authorize_agents_read,
    authorize_agents_run,
    authorize_dev_agent_admin,
    authorize_billing_admin,
    authorize_forensics_document,
    authorize_forensics_financial,
    authorize_forensics_image,
    authorize_graph_read,
    authorize_ingest_enqueue,
    authorize_ingest_status,
    authorize_knowledge_read,
    authorize_knowledge_write,
    authorize_query,
    authorize_timeline,
    create_mtls_config,
)
from .security.mtls import MTLSMiddleware
from .storage.agent_memory_store import ImprovementTaskRecord, PatchProposalRecord

settings = get_settings()
setup_telemetry(settings)
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(MTLSMiddleware, config=create_mtls_config())


@app.options("/graphql", include_in_schema=False)
async def graphql_http_options() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.api_route("/graphql", methods=["GET", "POST"])
async def graphql_http(
    request: Request,
    principal: Principal = Depends(authorize_timeline),
) -> Response:
    request.state.principal = principal
    record_billing_event(
        principal,
        BillingEventType.TIMELINE,
        attributes={
            "endpoint": "/graphql",
            "method": request.method,
        },
    )
    return await graphql_app.handle_request(request)


@app.websocket("/graphql")
async def graphql_websocket(
    websocket: WebSocket,
    principal: Principal = Depends(authorize_timeline),
) -> None:
    websocket.state.principal = principal
    record_billing_event(
        principal,
        BillingEventType.TIMELINE,
        attributes={
            "endpoint": "/graphql",
            "method": "WEBSOCKET",
        },
    )
    await graphql_app.handle_websocket(websocket)


def _raise_workflow_exception(exc: WorkflowException) -> None:
    status_code = exc.status_code or http_status_for_error(exc.error)
    raise HTTPException(status_code=status_code, detail=exc.error.to_dict()) from exc


def _proposal_from_record(
    task: ImprovementTaskRecord,
    proposal: PatchProposalRecord,
) -> DevAgentProposalModel:
    return DevAgentProposalModel(
        proposal_id=proposal.proposal_id,
        task_id=proposal.task_id,
        feature_request_id=task.feature_request_id,
        title=proposal.title,
        summary=proposal.summary,
        diff=proposal.diff,
        status=proposal.status,
        created_at=proposal.created_at,
        created_by=dict(proposal.created_by),
        validation=dict(proposal.validation),
        approvals=[dict(entry) for entry in proposal.approvals],
        rationale=list(proposal.rationale),
    )


def _task_from_record(task: ImprovementTaskRecord) -> DevAgentTaskModel:
    proposals = [_proposal_from_record(task, proposal) for proposal in task.proposals]
    return DevAgentTaskModel(
        task_id=task.task_id,
        feature_request_id=task.feature_request_id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        planner_notes=list(task.planner_notes),
        risk_score=task.risk_score,
        metadata=dict(task.metadata),
        proposals=proposals,
    )


def _execution_from_result(result: SandboxExecutionResult) -> SandboxExecutionModel:
    return SandboxExecutionModel(
        success=result.success,
        workspace_id=result.workspace_id,
        commands=[
            SandboxCommandResultModel(
                command=list(command.command),
                return_code=command.return_code,
                stdout=command.stdout,
                stderr=command.stderr,
                duration_ms=command.duration_ms,
            )
            for command in result.commands
        ],
    )


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


def _build_voice_session_response(
    session_outcome,
    request: Request,
) -> VoiceSessionCreateResponse:
    session = session_outcome.session
    sentiment = session_outcome.sentiment
    segments = [
        {
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
            "confidence": segment["confidence"],
        }
        for segment in session.segments
    ]
    audio_url = request.url_for("stream_voice_response", session_id=session.session_id)
    return VoiceSessionCreateResponse(
        session_id=session.session_id,
        thread_id=session.thread_id,
        case_id=session.case_id,
        persona_id=session.persona_id,
        transcript=session.transcript,
        sentiment={
            "label": sentiment.label,
            "score": sentiment.score,
            "pace": sentiment.pace,
        },
        segments=segments,
        created_at=session.created_at,
        updated_at=session.updated_at,
        assistant_text=session_outcome.assistant_text,
        audio_url=str(audio_url),
    )


@app.get("/voice/personas", response_model=VoicePersonaListResponse)
def list_voice_personas(
    service: VoiceService = Depends(get_voice_service),
    principal: Principal = Depends(authorize_agents_run),
) -> VoicePersonaListResponse:
    personas = list(service.list_personas())
    return VoicePersonaListResponse(personas=personas)


@app.post(
    "/voice/sessions",
    response_model=VoiceSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_voice_session(
    request: Request,
    audio: UploadFile = File(...),
    case_id: str = Form(...),
    persona_id: str = Form(...),
    thread_id: str | None = Form(default=None),
    service: VoiceService = Depends(get_voice_service),
    principal: Principal = Depends(authorize_agents_run),
) -> VoiceSessionCreateResponse:
    payload = await audio.read()
    await audio.close()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio is empty")
    try:
        outcome = service.create_session(
            case_id=case_id,
            audio_payload=payload,
            persona_id=persona_id,
            principal=principal,
            thread_id=thread_id,
        )
    except VoiceServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WorkflowAbort as exc:
        _raise_workflow_exception(exc)
    return _build_voice_session_response(outcome, request)


@app.get("/voice/sessions/{session_id}", response_model=VoiceSessionDetailResponse)
def get_voice_session(
    session_id: str,
    service: VoiceService = Depends(get_voice_service),
    principal: Principal = Depends(authorize_agents_read),
) -> VoiceSessionDetailResponse:
    try:
        session = service.get_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Voice session {session_id} not found") from exc
    voice_memory: Dict[str, Any] = {}
    try:
        thread_payload = service.agents_service.get_thread(session.thread_id)
    except FileNotFoundError:
        thread_payload = {}
    memory_block = thread_payload.get("memory", {}).get("voice_sessions", {})
    if isinstance(memory_block, dict):
        stored = memory_block.get(session_id)
        if isinstance(stored, dict):
            voice_memory = stored
    return VoiceSessionDetailResponse(
        session_id=session.session_id,
        thread_id=session.thread_id,
        case_id=session.case_id,
        persona_id=session.persona_id,
        transcript=session.transcript,
        sentiment={
            "label": session.sentiment_label,
            "score": session.sentiment_score,
            "pace": session.pace,
        },
        segments=session.segments,
        created_at=session.created_at,
        updated_at=session.updated_at,
        voice_memory=voice_memory,
    )


@app.get(
    "/voice/sessions/{session_id}/response",
    name="stream_voice_response",
)
def stream_voice_response(
    session_id: str,
    service: VoiceService = Depends(get_voice_service),
    principal: Principal = Depends(authorize_agents_read),
) -> StreamingResponse:
    try:
        stream = service.stream_response_audio(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Voice session {session_id} not found") from exc
    headers = {"Content-Disposition": f"inline; filename={session_id}.wav"}
    return StreamingResponse(stream, media_type="audio/wav", headers=headers)


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
            "endpoint": "/ingest",
            "method": "POST",
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


@app.post(
    "/knowledge/search",
    response_model=KnowledgeSearchResponse,
)
def knowledge_search(
    payload: KnowledgeSearchRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
    principal: Principal = Depends(authorize_knowledge_read),
) -> JSONResponse:
    filters = payload.filters.model_dump(exclude_none=True) if payload.filters else None
    result = service.search(
        payload.query,
        limit=payload.limit,
        filters=filters,
        principal=principal,
    )
    response = KnowledgeSearchResponse(**result)
    return JSONResponse(content=response.model_dump(mode="json"))


@app.get(
    "/knowledge/lessons",
    response_model=KnowledgeLessonListResponse,
)
def knowledge_lessons(
    service: KnowledgeService = Depends(get_knowledge_service),
    principal: Principal = Depends(authorize_knowledge_read),
) -> JSONResponse:
    payload = service.list_lessons(principal)
    response = KnowledgeLessonListResponse(**payload)
    return JSONResponse(content=response.model_dump(mode="json"))


@app.get(
    "/knowledge/lessons/{lesson_id}",
    response_model=KnowledgeLessonDetailResponse,
)
def knowledge_lesson_detail(
    lesson_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
    principal: Principal = Depends(authorize_knowledge_read),
) -> JSONResponse:
    try:
        payload = service.get_lesson(lesson_id, principal)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    response = KnowledgeLessonDetailResponse(**payload)
    return JSONResponse(content=response.model_dump(mode="json"))


@app.post(
    "/knowledge/lessons/{lesson_id}/progress",
    response_model=KnowledgeProgressUpdateResponse,
)
def knowledge_progress_update(
    lesson_id: str,
    payload: KnowledgeProgressUpdateRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
    principal: Principal = Depends(authorize_knowledge_write),
) -> JSONResponse:
    try:
        result = service.record_progress(
            lesson_id,
            payload.section_id,
            payload.completed,
            principal,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    response = KnowledgeProgressUpdateResponse(**result)
    return JSONResponse(content=response.model_dump(mode="json"))


@app.post(
    "/knowledge/lessons/{lesson_id}/bookmark",
    response_model=KnowledgeBookmarkResponse,
)
def knowledge_toggle_bookmark(
    lesson_id: str,
    payload: KnowledgeBookmarkRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
    principal: Principal = Depends(authorize_knowledge_write),
) -> JSONResponse:
    try:
        result = service.set_bookmark(lesson_id, payload.bookmarked, principal)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    response = KnowledgeBookmarkResponse(**result)
    return JSONResponse(content=response.model_dump(mode="json"))


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
    mode: str = Query(
        default="precision", description="Retrieval operating mode: precision or recall"
    ),
    stream: bool = Query(default=False, description="Stream partial answers as JSON lines"),
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
        mode_value = RetrievalMode(mode.lower())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid mode") from exc
    try:
        result = service.query(
            q,
            page=page,
            page_size=page_size,
            filters=filters or None,
            rerank=rerank,
            mode=mode_value,
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
    billing_attrs = {
        "endpoint": "/query",
        "method": "GET",
        "latency_ms": latency_ms,
        "page": page,
        "page_size": page_size,
        "filters": bool(filters),
        "rerank": rerank,
        "has_evidence": result.has_evidence,
        "mode": mode_value.value,
        "stream": stream,
    }
    record_billing_event(
        principal,
        BillingEventType.QUERY,
        attributes=billing_attrs,
    )
    if stream:
        stream_attributes = {
            "mode": mode_value.value,
            "reranker": result.meta.reranker,
            "stream": True,
        }
        events = service.stream_result(result, attributes=stream_attributes)
        return StreamingResponse((event + "\n" for event in events), media_type="application/jsonl")
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
    risk_band: str | None = Query(
        default=None,
        description="Filter events by machine-learned risk band (low, medium, high)",
    ),
    motion_due_before: datetime | None = Query(
        default=None,
        description="Return motion events with deadlines strictly before this timestamp",
    ),
    motion_due_after: datetime | None = Query(
        default=None,
        description="Return motion events with deadlines strictly after this timestamp",
    ),
) -> TimelineResponse:
    try:
        result = service.list_events(
            cursor=cursor,
            limit=limit,
            from_ts=from_ts,
            to_ts=to_ts,
            entity=entity,
            risk_band=risk_band,
            motion_due_before=motion_due_before,
            motion_due_after=motion_due_after,
        )
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    meta = TimelinePaginationModel(cursor=result.next_cursor, limit=result.limit, has_more=result.has_more)
    record_billing_event(
        principal,
        BillingEventType.TIMELINE,
        attributes={
            "endpoint": "/timeline",
            "method": "GET",
            "limit": limit,
            "cursor": bool(cursor),
            "entity": bool(entity),
            "from_ts": bool(from_ts),
            "to_ts": bool(to_ts),
            "risk_band": bool(risk_band),
            "motion_due_before": bool(motion_due_before),
            "motion_due_after": bool(motion_due_after),
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
                risk_score=event.risk_score,
                risk_band=event.risk_band,
                outcome_probabilities=event.outcome_probabilities,
                recommended_actions=event.recommended_actions,
                motion_deadline=event.motion_deadline,
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
    response = service.run_case(
        payload.case_id,
        payload.question,
        top_k=top_k,
        principal=principal,
        autonomy_level=payload.autonomy_level,
        max_turns=payload.max_turns,
    )
    payload_model = AgentRunResponse(**response)
    record_billing_event(
        principal,
        BillingEventType.AGENT,
        attributes={
            "endpoint": "/agents/run",
            "method": "POST",
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


@app.get("/scenarios", response_model=ScenarioListResponse)
def scenarios_list(
    engine = Depends(get_scenario_engine),
    principal: Principal = Depends(authorize_agents_read),
) -> ScenarioListResponse:
    _ = principal
    metadata = engine.list_metadata()
    return ScenarioListResponse(scenarios=[_scenario_metadata_model(item) for item in metadata])


@app.get("/scenarios/{scenario_id}", response_model=ScenarioDefinitionModel)
def scenarios_detail(
    scenario_id: str,
    engine = Depends(get_scenario_engine),
    principal: Principal = Depends(authorize_agents_read),
) -> ScenarioDefinitionModel:
    _ = principal
    try:
        definition = engine.get(scenario_id)
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    return _scenario_definition_model(definition)


@app.post("/scenarios/run", response_model=ScenarioRunResponseModel)
def scenarios_run(
    payload: ScenarioRunRequestModel,
    engine = Depends(get_scenario_engine),
    principal: Principal = Depends(authorize_agents_run),
) -> ScenarioRunResponseModel:
    options = _scenario_run_options(payload)
    try:
        definition = engine.get(options.scenario_id)
        result = engine.run(options, principal=principal)
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    transcript_models = [ScenarioRunTurnModel.model_validate(turn) for turn in result.get("transcript", [])]
    definition_model = _scenario_definition_model(definition)
    telemetry = dict(result.get("telemetry", {}))
    return ScenarioRunResponseModel(
        run_id=str(result.get("run_id")),
        scenario=definition_model,
        transcript=transcript_models,
        telemetry=telemetry,
    )


def _tts_service_dependency() -> TextToSpeechService:
    service = get_tts_service(optional=True)
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS service not configured")
    return service


@app.post("/tts/speak", response_model=TextToSpeechResponse)
def tts_speak(
    payload: TextToSpeechRequest,
    service: TextToSpeechService = Depends(_tts_service_dependency),
    principal: Principal = Depends(authorize_agents_run),
) -> TextToSpeechResponse:
    _ = principal
    try:
        result = service.synthesise(text=payload.text, voice=payload.voice)
    except WorkflowException as exc:
        _raise_workflow_exception(exc)
    return TextToSpeechResponse(
        voice=result.voice,
        mime_type=result.content_type,
        base64=base64.b64encode(result.audio_bytes).decode("ascii"),
        cache_hit=result.cache_hit,
        sha256=result.sha256,
    )


@app.get("/dev-agent/proposals", response_model=DevAgentProposalListResponse)
def dev_agent_proposals(
    service: DevAgentService = Depends(get_dev_agent_service),
    principal: Principal = Depends(authorize_dev_agent_admin),
) -> DevAgentProposalListResponse:
    _ = principal
    backlog_models = [_task_from_record(task) for task in service.list_backlog()]
    return DevAgentProposalListResponse(backlog=backlog_models)


@app.post("/dev-agent/apply", response_model=DevAgentApplyResponse)
def dev_agent_apply(
    payload: DevAgentApplyRequest,
    service: DevAgentService = Depends(get_dev_agent_service),
    principal: Principal = Depends(authorize_dev_agent_admin),
) -> DevAgentApplyResponse:
    result = service.apply_proposal(payload.proposal_id, principal)
    task_model = _task_from_record(result.task)
    proposal_model = _proposal_from_record(result.task, result.proposal)
    execution_model = _execution_from_result(result.execution)
    return DevAgentApplyResponse(
        proposal=proposal_model,
        task=task_model,
        execution=execution_model,
    )


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


@app.get("/costs/summary", response_model=CostSummaryResponse)
def cost_summary(
    window_hours: float = Query(24.0, ge=0.5, le=720.0, description="Lookback window in hours"),
    tenant_id: str | None = Query(default=None, description="Tenant identifier to filter summary"),
    service: CostTrackingService = Depends(get_cost_tracking_service),
    principal: Principal = Depends(authorize_billing_admin),
) -> JSONResponse:
    _ = principal
    summary = service.summarise(window_hours=window_hours, tenant_id=tenant_id)
    response = CostSummaryResponse(
        generated_at=summary.generated_at,
        window_hours=summary.window_hours,
        tenant_id=summary.tenant_id,
        api_calls=CostSummaryMetricModel(**asdict(summary.api_calls)),
        model_loads=CostSummaryMetricModel(**asdict(summary.model_loads)),
        gpu_utilisation=CostSummaryMetricModel(**asdict(summary.gpu_utilisation)),
    )
    return JSONResponse(content=response.model_dump(mode="json"))


@app.get("/costs/events", response_model=List[CostEventModel])
def cost_events(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of events to return"),
    tenant_id: str | None = Query(default=None, description="Filter events by tenant"),
    category: str | None = Query(default=None, description="Filter by category: api, model, gpu"),
    service: CostTrackingService = Depends(get_cost_tracking_service),
    principal: Principal = Depends(authorize_billing_admin),
) -> JSONResponse:
    _ = principal
    category_value = None
    if category:
        try:
            category_value = CostEventCategory(category)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category") from exc
    records = service.list_events(limit=limit, tenant_id=tenant_id, category=category_value)
    events = [
        CostEventModel(
            event_id=record.event_id,
            timestamp=record.timestamp,
            tenant_id=record.tenant_id,
            category=record.category,  # type: ignore[arg-type]
            name=record.name,
            amount=record.amount,
            unit=record.unit,
            metadata=record.metadata,
        )
        for record in records
    ]
    payload = [event.model_dump(mode="json") for event in events]
    return JSONResponse(content=payload)


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
            "endpoint": "/onboarding",
            "method": "POST",
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

def _scenario_participant_model(participant: ScenarioParticipant) -> ScenarioParticipantModel:
    return ScenarioParticipantModel(
        id=participant.id,
        name=participant.name,
        role=participant.role,
        description=participant.description,
        sprite=str(participant.sprite),
        accent_color=participant.accent_color,
        voice=participant.voice,
        default=participant.default,
        optional=participant.optional,
    )


def _scenario_variable_model(variable: ScenarioVariable) -> ScenarioVariableModel:
    return ScenarioVariableModel(
        name=variable.name,
        description=variable.description,
        required=variable.required,
        default=variable.default,
    )


def _scenario_evidence_model(spec: ScenarioEvidenceRequirement) -> ScenarioEvidenceSpecModel:
    return ScenarioEvidenceSpecModel(
        id=spec.id,
        label=spec.label,
        description=spec.description,
        required=spec.required,
        type=spec.type,
        document_id=spec.document_id,
    )


def _scenario_definition_model(definition: ScenarioDefinition) -> ScenarioDefinitionModel:
    beats: List[ScenarioBeatSpecModel] = []
    for beat in definition.beats:
        if beat.kind == "dynamic":
            dynamic = beat  # type: ignore[assignment]
            beats.append(
                ScenarioBeatSpecModel(
                    id=dynamic.id,
                    kind=dynamic.kind,
                    speaker=dynamic.speaker,
                    stage_direction=dynamic.stage_direction,
                    emphasis=dynamic.emphasis,
                    duration_ms=dynamic.duration_ms,
                    fallback_text=dynamic.fallback_text,
                    delegate=dynamic.delegate,
                    top_k=dynamic.top_k,
                )
            )
        else:
            scripted = beat  # type: ignore[assignment]
            beats.append(
                ScenarioBeatSpecModel(
                    id=scripted.id,
                    kind=scripted.kind,
                    speaker=scripted.speaker,
                    stage_direction=scripted.stage_direction,
                    emphasis=scripted.emphasis,
                    duration_ms=scripted.duration_ms,
                )
            )
    return ScenarioDefinitionModel(
        scenario_id=definition.id,
        title=definition.title,
        description=definition.description,
        category=definition.category,
        difficulty=definition.difficulty,
        tags=list(definition.tags),
        participants=[_scenario_participant_model(p) for p in definition.participants],
        variables={name: _scenario_variable_model(variable) for name, variable in definition.variables.items()},
        evidence=[_scenario_evidence_model(spec) for spec in definition.evidence],
        beats=beats,
    )


def _scenario_metadata_model(metadata: ScenarioMetadata) -> ScenarioMetadataModel:
    return ScenarioMetadataModel(
        scenario_id=metadata.id,
        title=metadata.title,
        description=metadata.description,
        category=metadata.category,
        difficulty=metadata.difficulty,
        tags=list(metadata.tags),
        participants=list(metadata.participants),
    )


def _scenario_run_options(payload: ScenarioRunRequestModel) -> ScenarioRunOptions:
    evidence_bindings = {
        slot: ScenarioEvidenceBinding(slot_id=slot, value=binding.value, document_id=binding.document_id, type=binding.type)
        for slot, binding in payload.evidence.items()
    }
    return ScenarioRunOptions(
        scenario_id=payload.scenario_id,
        case_id=payload.case_id,
        variables=payload.variables,
        evidence=evidence_bindings,
        participants=payload.participants,
        use_tts=payload.enable_tts,
    )
