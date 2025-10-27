from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from .config import get_settings
from .models.api import (
    ForensicsResponse,
    GraphEdgeModel,
    GraphNeighborResponse,
    GraphNodeModel,
    IngestionRequest,
    IngestionResponse,
    IngestionStatusResponse,
    QueryResponse,
    TimelineEventModel,
    TimelineResponse,
)
from .services.forensics import ForensicsService, get_forensics_service
from .services.graph import GraphService, get_graph_service
from .services.ingestion import IngestionService, get_ingestion_service
from .services.retrieval import RetrievalService, get_retrieval_service
from .services.timeline import TimelineService, get_timeline_service

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest(
    payload: IngestionRequest,
    service: IngestionService = Depends(get_ingestion_service),
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
) -> JSONResponse:
    try:
        record = service.get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found") from exc
    response = IngestionStatusResponse(**record)
    terminal_statuses = {"succeeded", "failed", "cancelled"}
    status_code = status.HTTP_200_OK if response.status in terminal_statuses else status.HTTP_202_ACCEPTED
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))


@app.get("/query", response_model=QueryResponse)
def query(
    q: str,
    service: RetrievalService = Depends(get_retrieval_service),
) -> QueryResponse:
    result = service.query(q)
    return QueryResponse(**result)


@app.get("/timeline", response_model=TimelineResponse)
def timeline(
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineResponse:
    events = service.list_events()
    return TimelineResponse(
        events=[
            TimelineEventModel(
                id=event.id,
                ts=event.ts,
                title=event.title,
                summary=event.summary,
                citations=event.citations,
            )
            for event in events
        ]
    )


@app.get("/graph/neighbor", response_model=GraphNeighborResponse)
def graph_neighbor(
    id: str,
    service: GraphService = Depends(get_graph_service),
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
) -> ForensicsResponse:
    try:
        data = service.load_artifact(file_id, artifact)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ForensicsResponse(data=data)


@app.get("/forensics/document", response_model=ForensicsResponse)
def forensics_document(
    id: str,
    service: ForensicsService = Depends(get_forensics_service),
) -> ForensicsResponse:
    return _load_forensics(service, id, "document")


@app.get("/forensics/image", response_model=ForensicsResponse)
def forensics_image(
    id: str,
    service: ForensicsService = Depends(get_forensics_service),
) -> ForensicsResponse:
    return _load_forensics(service, id, "image")


@app.get("/forensics/financial", response_model=ForensicsResponse)
def forensics_financial(
    id: str,
    service: ForensicsService = Depends(get_forensics_service),
) -> ForensicsResponse:
    return _load_forensics(service, id, "financial")

