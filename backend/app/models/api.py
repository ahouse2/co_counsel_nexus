from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class IngestionSource(BaseModel):
    type: str = Field(description="Source type identifier")
    path: Optional[str] = Field(default=None, description="Filesystem path for local sources")
    credRef: Optional[str] = Field(default=None, description="Credential reference for remote sources")


class IngestionRequest(BaseModel):
    sources: List[IngestionSource]


class IngestionResponse(BaseModel):
    job_id: str = Field(description="Identifier tracking the ingestion operation")
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"] = Field(
        description="Current job status"
    )


class IngestionDocumentModel(BaseModel):
    id: str
    uri: Optional[HttpUrl | str] = None
    type: str
    title: str
    metadata: dict


class IngestionErrorModel(BaseModel):
    code: str
    message: str
    source: Optional[str] = None


class IngestionIngestionDetailsModel(BaseModel):
    documents: int
    skipped: List[dict] = Field(default_factory=list)


class IngestionTimelineDetailsModel(BaseModel):
    events: int


class IngestionForensicsArtifactModel(BaseModel):
    document_id: str
    type: str
    schema_version: str
    generated_at: datetime | None
    report_path: str
    fallback_applied: bool = False


class IngestionForensicsDetailsModel(BaseModel):
    artifacts: List[IngestionForensicsArtifactModel] = Field(default_factory=list)
    last_run_at: datetime | None = None


class IngestionGraphDetailsModel(BaseModel):
    nodes: int
    edges: int
    triples: int


class IngestionStatusDetailsModel(BaseModel):
    ingestion: IngestionIngestionDetailsModel
    timeline: IngestionTimelineDetailsModel
    forensics: IngestionForensicsDetailsModel
    graph: IngestionGraphDetailsModel


class IngestionStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    submitted_at: datetime
    updated_at: datetime
    documents: List[IngestionDocumentModel]
    errors: List[IngestionErrorModel] = Field(default_factory=list)
    status_details: IngestionStatusDetailsModel


class CitationEntityModel(BaseModel):
    id: str
    label: str
    type: str


class CitationModel(BaseModel):
    docId: str
    span: str
    uri: Optional[HttpUrl | str] = None
    pageLabel: Optional[str] = None
    chunkIndex: Optional[int] = Field(default=None, ge=0)
    pageNumber: Optional[int] = Field(default=None, ge=1)
    title: Optional[str] = None
    sourceType: Optional[str] = None
    retrievers: List[str] = Field(default_factory=list)
    fusionScore: Optional[float] = None
    confidence: Optional[float] = None
    entities: List[CitationEntityModel] = Field(default_factory=list)


class TraceModel(BaseModel):
    vector: List[dict]
    graph: dict
    forensics: List[dict] = Field(default_factory=list)
    privilege: Optional[dict] = None


class QueryPaginationModel(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=50)
    total_items: int = Field(ge=0)
    has_next: bool
    mode: Literal["precision", "recall"]
    reranker: str


class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationModel]
    traces: TraceModel
    meta: QueryPaginationModel


class OutcomeProbabilityModel(BaseModel):
    label: str
    probability: float


class TimelineEventModel(BaseModel):
    id: str
    ts: datetime
    title: str
    summary: str
    citations: List[str]
    entity_highlights: List[dict] = Field(default_factory=list)
    relation_tags: List[dict] = Field(default_factory=list)
    confidence: float | None = None
    risk_score: float | None = None
    risk_band: str | None = None
    outcome_probabilities: List[OutcomeProbabilityModel] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    motion_deadline: Optional[datetime] = None


class TimelineResponse(BaseModel):
    events: List[TimelineEventModel]
    meta: Optional["TimelinePaginationModel"] = None


class TimelinePaginationModel(BaseModel):
    cursor: Optional[str] = None
    limit: int
    has_more: bool


class GraphNodeModel(BaseModel):
    id: str
    type: str
    properties: dict


class GraphEdgeModel(BaseModel):
    source: str
    target: str
    type: str
    properties: dict


class GraphNeighborResponse(BaseModel):
    nodes: List[GraphNodeModel]
    edges: List[GraphEdgeModel]


class ForensicsStageModel(BaseModel):
    name: str
    started_at: datetime
    completed_at: datetime
    status: str
    notes: List[str]


class ForensicsSignalModel(BaseModel):
    type: str
    level: Literal["info", "warning", "error"]
    detail: str
    data: Optional[dict] = None


class ForensicsResponse(BaseModel):
    summary: str
    data: dict
    metadata: dict
    signals: List[ForensicsSignalModel]
    stages: List[ForensicsStageModel]
    fallback_applied: bool
    schema_version: str
    generated_at: Optional[datetime] = None


class AgentRunRequest(BaseModel):
    case_id: str
    question: str
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    autonomy_level: Optional[Literal["low", "balanced", "high"]] = Field(default=None)
    max_turns: Optional[int] = Field(default=None, ge=5, le=40)


class AgentTurnModel(BaseModel):
    role: str
    action: str
    input: dict
    output: dict
    started_at: datetime
    completed_at: datetime
    metrics: dict


class AgentErrorModel(BaseModel):
    component: str
    code: str
    message: str
    severity: Literal["info", "warning", "error", "critical"]
    retryable: bool
    occurred_at: datetime
    attempt: int
    context: dict = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    thread_id: str
    case_id: str
    question: str
    created_at: datetime
    updated_at: datetime
    status: Literal["pending", "succeeded", "failed", "degraded"]
    final_answer: str
    citations: List[CitationModel]
    qa_scores: Dict[str, float]
    qa_notes: List[str]
    turns: List[AgentTurnModel]
    errors: List[AgentErrorModel]
    telemetry: dict
    memory: dict = Field(default_factory=dict)


class AgentThreadListResponse(BaseModel):
    threads: List[str]


class BillingPlanModel(BaseModel):
    plan_id: str
    label: str
    monthly_price_usd: float
    included_queries: int
    included_ingest_gb: float
    included_seats: int
    support_tier: str
    support_response_sla_hours: int
    support_contact: str
    overage_per_query_usd: float
    overage_per_gb_usd: float
    onboarding_sla_hours: int
    description: str


class BillingPlanListResponse(BaseModel):
    generated_at: datetime
    plans: List[BillingPlanModel]


class BillingUsageSnapshotModel(BaseModel):
    tenant_id: str
    plan_id: str
    plan_label: str
    support_tier: str
    support_sla_hours: int
    support_channel: str
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
    metadata: dict


class BillingUsageResponse(BaseModel):
    generated_at: datetime
    tenants: List[BillingUsageSnapshotModel]


class OnboardingSubmission(BaseModel):
    tenant_id: str = Field(min_length=3, description="Unique tenant identifier or slug")
    organization: str = Field(min_length=2, description="Legal name of the organisation")
    contact_name: str = Field(min_length=2)
    contact_email: EmailStr
    seats: int = Field(ge=1, le=500)
    primary_use_case: str = Field(min_length=3)
    departments: List[str] = Field(default_factory=list)
    estimated_matters_per_month: int = Field(ge=0)
    roi_baseline_hours_per_matter: float = Field(ge=0.0)
    automation_target_percent: float = Field(default=0.25, ge=0.0, le=1.0)
    go_live_date: datetime | None = Field(default=None)
    notes: Optional[str] = Field(default=None)
    success_criteria: List[str] = Field(default_factory=list)


class OnboardingSubmissionResponse(BaseModel):
    tenant_id: str
    recommended_plan: str
    message: str
    received_at: datetime


class KnowledgeMediaModel(BaseModel):
    type: str
    title: str
    url: HttpUrl | str
    provider: Optional[str] = None


class KnowledgeProgressModel(BaseModel):
    completed_sections: List[str] = Field(default_factory=list)
    total_sections: int = Field(ge=0)
    percent_complete: float = Field(ge=0.0, le=1.0)
    last_viewed_at: Optional[datetime] = None


class KnowledgeLessonSectionModel(BaseModel):
    id: str
    title: str
    content: str
    completed: bool = False


class KnowledgeLessonSummaryModel(BaseModel):
    lesson_id: str
    title: str
    summary: str
    tags: List[str]
    difficulty: str
    estimated_minutes: int = Field(ge=0)
    jurisdictions: List[str]
    media: List[KnowledgeMediaModel]
    progress: KnowledgeProgressModel
    bookmarked: bool = False


class KnowledgeLessonListResponse(BaseModel):
    lessons: List[KnowledgeLessonSummaryModel]
    filters: Dict[str, List[str]]


class KnowledgeLessonDetailResponse(BaseModel):
    lesson_id: str
    title: str
    summary: str
    tags: List[str]
    difficulty: str
    estimated_minutes: int
    jurisdictions: List[str]
    media: List[KnowledgeMediaModel]
    sections: List[KnowledgeLessonSectionModel]
    progress: KnowledgeProgressModel
    bookmarked: bool


class KnowledgeSearchFiltersModel(BaseModel):
    tags: Optional[List[str]] = None
    difficulty: Optional[List[str]] = None
    media_types: Optional[List[str]] = None


class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=50)
    filters: Optional[KnowledgeSearchFiltersModel] = None


class KnowledgeSearchResultModel(BaseModel):
    lesson_id: str
    lesson_title: str
    section_id: str
    section_title: str
    snippet: str
    score: float
    tags: List[str]
    difficulty: str
    media: List[KnowledgeMediaModel]


class KnowledgeSearchResponse(BaseModel):
    results: List[KnowledgeSearchResultModel]
    elapsed_ms: float
    applied_filters: Dict[str, List[str]] = Field(default_factory=dict)


class KnowledgeProgressUpdateRequest(BaseModel):
    section_id: str
    completed: bool = True


class KnowledgeProgressUpdateResponse(BaseModel):
    lesson_id: str
    section_id: str
    completed_sections: List[str]
    total_sections: int
    percent_complete: float
    last_viewed_at: Optional[datetime] = None


class CostSummaryMetricModel(BaseModel):
    total: float
    unit: str
    breakdown: Dict[str, float]
    average: Optional[float] = None


class CostSummaryResponse(BaseModel):
    generated_at: datetime
    window_hours: float
    tenant_id: Optional[str] = None
    api_calls: CostSummaryMetricModel
    model_loads: CostSummaryMetricModel
    gpu_utilisation: CostSummaryMetricModel


class CostEventModel(BaseModel):
    event_id: str
    timestamp: datetime
    tenant_id: Optional[str]
    category: Literal["api", "model", "gpu"]
    name: str
    amount: float
    unit: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeBookmarkRequest(BaseModel):
    bookmarked: bool = True


class KnowledgeBookmarkResponse(BaseModel):
    lesson_id: str
    bookmarked: bool
    bookmarks: List[str]


class SandboxCommandResultModel(BaseModel):
    command: List[str]
    return_code: int
    stdout: str
    stderr: str
    duration_ms: float


class SandboxExecutionModel(BaseModel):
    success: bool
    workspace_id: str
    commands: List[SandboxCommandResultModel]


class DevAgentProposalModel(BaseModel):
    proposal_id: str
    task_id: str
    feature_request_id: str
    title: str
    summary: str
    diff: str
    status: str
    created_at: datetime
    created_by: Dict[str, Any]
    validation: Dict[str, Any]
    approvals: List[Dict[str, Any]] = Field(default_factory=list)
    rationale: List[str] = Field(default_factory=list)


class DevAgentTaskModel(BaseModel):
    task_id: str
    feature_request_id: str
    title: str
    description: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    planner_notes: List[str] = Field(default_factory=list)
    risk_score: float | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    proposals: List[DevAgentProposalModel] = Field(default_factory=list)


class DevAgentProposalListResponse(BaseModel):
    backlog: List[DevAgentTaskModel]


class DevAgentApplyRequest(BaseModel):
    proposal_id: str


class DevAgentApplyResponse(BaseModel):
    proposal: DevAgentProposalModel
    task: DevAgentTaskModel
    execution: SandboxExecutionModel


class ScenarioParticipantModel(BaseModel):
    id: str
    name: str
    role: str
    description: str
    sprite: str
    accent_color: str
    voice: Optional[str] = None
    default: bool = True
    optional: bool = False


class ScenarioVariableModel(BaseModel):
    name: str
    description: str
    required: bool = False
    default: Optional[str] = None


class ScenarioEvidenceSpecModel(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    required: bool = False
    type: str = "document"
    document_id: Optional[str] = None


class ScenarioDirectorMotionModel(BaseModel):
    direction: Literal["none", "left", "right", "forward", "back"]
    intensity: float
    tempo: float


class ScenarioDirectorLightingModel(BaseModel):
    preset: str
    palette: List[str]
    intensity: float
    focus: float
    ambient: float


class ScenarioDirectorPersonaModel(BaseModel):
    expression: str
    vocal_register: str
    confidence: float


class ScenarioDirectorBeatModel(BaseModel):
    beat_id: str
    emotional_tone: str
    counter_argument: Optional[str] = None
    lighting: ScenarioDirectorLightingModel
    motion: ScenarioDirectorMotionModel
    persona: ScenarioDirectorPersonaModel


class ScenarioDirectorManifestModel(BaseModel):
    version: str
    beats: Dict[str, ScenarioDirectorBeatModel]


class ScenarioBeatSpecModel(BaseModel):
    id: str
    kind: Literal["scripted", "dynamic"]
    speaker: str
    stage_direction: Optional[str] = None
    emphasis: Optional[str] = None
    duration_ms: Optional[int] = None
    fallback_text: Optional[str] = None
    delegate: Optional[str] = None
    top_k: Optional[int] = None


class ScenarioDefinitionModel(BaseModel):
    scenario_id: str
    title: str
    description: str
    category: str
    difficulty: str
    tags: List[str]
    participants: List[ScenarioParticipantModel]
    variables: Dict[str, ScenarioVariableModel]
    evidence: List[ScenarioEvidenceSpecModel]
    beats: List[ScenarioBeatSpecModel]
    director: ScenarioDirectorManifestModel


class ScenarioMetadataModel(BaseModel):
    scenario_id: str
    title: str
    description: str
    category: str
    difficulty: str
    tags: List[str]
    participants: List[str]


class ScenarioListResponse(BaseModel):
    scenarios: List[ScenarioMetadataModel]


class ScenarioEvidenceBindingModel(BaseModel):
    value: str
    document_id: Optional[str] = None
    type: Optional[str] = None


class ScenarioRunRequestModel(BaseModel):
    scenario_id: str
    case_id: str
    participants: List[str] = Field(default_factory=list)
    variables: Dict[str, str] = Field(default_factory=dict)
    evidence: Dict[str, ScenarioEvidenceBindingModel] = Field(default_factory=dict)
    enable_tts: bool = False
    director_overrides: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ScenarioRunAudioModel(BaseModel):
    voice: str
    mime_type: str
    base64: str
    cache_hit: bool
    sha256: str


class ScenarioRunTurnModel(BaseModel):
    beat_id: str
    speaker_id: str
    speaker: ScenarioParticipantModel
    text: str
    kind: str
    stage_direction: Optional[str]
    emphasis: Optional[str]
    duration_ms: Optional[float]
    thread_id: Optional[str]
    audio: Optional[ScenarioRunAudioModel] = None
    director: Optional[ScenarioDirectorBeatModel] = None


class ScenarioRunResponseModel(BaseModel):
    run_id: str
    scenario: ScenarioDefinitionModel
    transcript: List[ScenarioRunTurnModel]
    telemetry: Dict[str, Any]


class TextToSpeechRequest(BaseModel):
    text: str
    voice: Optional[str] = None


class TextToSpeechResponse(BaseModel):
    voice: str
    mime_type: str
    base64: str
    cache_hit: bool
    sha256: str
class VoicePersonaModel(BaseModel):
    persona_id: str
    label: str
    description: str | None = None
    speaker_id: str | None = None


class VoiceSentimentModel(BaseModel):
    label: Literal["positive", "negative", "neutral"]
    score: float = Field(ge=0.0, le=1.0)
    pace: float = Field(gt=0.0, le=2.5)


class VoiceSegmentModel(BaseModel):
    start: float = Field(ge=0.0)
    end: float = Field(ge=0.0)
    text: str
    confidence: float


class VoicePersonaDirectiveModel(BaseModel):
    persona_id: str
    speaker_id: str | None = None
    tone: str
    language: str
    pace: float = Field(gt=0.0, le=2.5)
    glossary: Dict[str, str] = Field(default_factory=dict)
    rationale: str


class VoiceSentimentArcPointModel(BaseModel):
    offset: float = Field(ge=0.0)
    score: float = Field(ge=0.0, le=1.0)
    label: Literal["positive", "negative", "neutral"]


class VoicePersonaShiftModel(BaseModel):
    at: float = Field(ge=0.0)
    persona_id: str
    tone: str
    language: str
    pace: float = Field(gt=0.0, le=2.5)
    trigger: str


class VoiceTranslationModel(BaseModel):
    source_language: str
    target_language: str
    translated_text: str
    bilingual_text: str
    glossary: Dict[str, str] = Field(default_factory=dict)


class VoiceSessionModel(BaseModel):
    session_id: str
    thread_id: str
    case_id: str
    persona_id: str
    transcript: str
    sentiment: VoiceSentimentModel
    persona_directive: VoicePersonaDirectiveModel
    sentiment_arc: List[VoiceSentimentArcPointModel]
    persona_shifts: List[VoicePersonaShiftModel]
    translation: VoiceTranslationModel
    segments: List[VoiceSegmentModel]
    created_at: datetime
    updated_at: datetime


class VoiceSessionCreateResponse(VoiceSessionModel):
    assistant_text: str
    audio_url: str


class VoiceSessionDetailResponse(VoiceSessionModel):
    voice_memory: Dict[str, Any] = Field(default_factory=dict)


class VoicePersonaListResponse(BaseModel):
    personas: List[VoicePersonaModel]

