from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


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


class CitationModel(BaseModel):
    docId: str
    span: str
    uri: Optional[HttpUrl | str] = None


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


class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationModel]
    traces: TraceModel
    meta: QueryPaginationModel


class TimelineEventModel(BaseModel):
    id: str
    ts: datetime
    title: str
    summary: str
    citations: List[str]


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


class AgentTurnModel(BaseModel):
    role: str
    action: str
    input: dict
    output: dict
    started_at: datetime
    completed_at: datetime
    metrics: dict


class AgentRunResponse(BaseModel):
    thread_id: str
    case_id: str
    question: str
    created_at: datetime
    updated_at: datetime
    final_answer: str
    citations: List[CitationModel]
    qa_scores: Dict[str, float]
    qa_notes: List[str]
    turns: List[AgentTurnModel]
    telemetry: dict


class AgentThreadListResponse(BaseModel):
    threads: List[str]

