from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List

import base64
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
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
    SandboxCommandResultModel,
    SandboxExecutionModel,
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
)
from .scenarios.schema import ScenarioDefinition, ScenarioEvidenceRequirement, ScenarioMetadata, ScenarioParticipant, ScenarioVariable
from .services.agents import AgentsService, get_agents_service
from .services.dev_agent import DevAgentService, get_dev_agent_service
from .services.errors import WorkflowException, http_status_for_error
from .services.forensics import ForensicsService, get_forensics_service
from .services.graph import GraphService, get_graph_service
from .services.ingestion import (
    IngestionService,
    get_ingestion_service,
    get_ingestion_worker,
    shutdown_ingestion_worker,
)
from .services.retrieval import RetrievalMode, RetrievalService, get_retrieval_service
from .services.scenarios import (
    ScenarioEvidenceBinding,
    ScenarioRunOptions,
    get_scenario_engine,
)
from .services.timeline import TimelineService, get_timeline_service
from .services.tts import TextToSpeechService, get_tts_service
from .security.authz import Principal
from .security.dependencies import (
    authorize_agents_read,
    authorize_agents_run,
    authorize_dev_agent_admin,
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
from .storage.agent_memory_store import ImprovementTaskRecord, PatchProposalRecord

settings = get_settings()
setup_telemetry(settings)
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(MTLSMiddleware, config=create_mtls_config())


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


def _tts_service_dependency() -> TextToSpeechService:
    service = get_tts_service(optional=True)
    if service is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TTS service not configured")
    return service
