from __future__ import annotations
from fastapi import FastAPI, Request, HTTPException

from .config import get_settings
from .telemetry import setup_telemetry
from .events import register_events

# Routers
from .api import retrieval, graph, agents, scenarios, auth, evidence_binder, predictive_analytics, settings as settings_api, graphql, health, billing, onboarding, legal_research, legal_theory, argument_mapping, strategic_recommendations, timeline, voice, ingestion, knowledge, dev_agent, sandbox, cost, documents, document_drafting, binder_preparation, feedback, mock_trial, forensics, knowledge_graph, service_of_process, users, cases, trial_university, halo, agents_status, agents_stream
from .memory_store import CaseMemoryStore
from .api import memory

settings = get_settings()
setup_telemetry(settings)
app = FastAPI(title=settings.app_name, version=settings.app_version)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8088",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:8088",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [dev] mTLS enabled (production would disable this in prod)
import ssl


@app.middleware("http")
async def mtls_middleware(request: Request, call_next):
    if request.url.scheme == "https" and "ssl_client_cert" not in request.scope:
        raise HTTPException(status_code=403, detail="Client certificate required")
    response = await call_next(request)
    return response

# Include routers (order kept sensible)
app.include_router(retrieval.router)
app.include_router(graph.router)
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(scenarios.router)
app.include_router(auth.router)
app.include_router(evidence_binder.router)
app.include_router(predictive_analytics.router)
app.include_router(settings_api.router, prefix="/api", tags=["Settings"])
app.include_router(graphql.router)
app.include_router(health.router)
register_events(app)
app.include_router(billing.router)
app.include_router(onboarding.router)
app.include_router(legal_research.router)
app.include_router(legal_theory.router)
app.include_router(argument_mapping.router)
app.include_router(strategic_recommendations.router)
app.include_router(timeline.router)
app.include_router(voice.router)
app.include_router(ingestion.router)
app.include_router(knowledge.router)
app.include_router(dev_agent.router)
app.include_router(sandbox.router)
app.include_router(cost.router)
app.include_router(documents.router)
app.include_router(document_drafting.router)
app.include_router(binder_preparation.router)
app.include_router(feedback.router)
app.include_router(mock_trial.router)
app.include_router(forensics.router, prefix="/forensics", tags=["Forensics"])
app.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["Knowledge Graph"])
app.include_router(service_of_process.router, prefix="/api", tags=["Service of Process"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(cases.router, prefix="/api", tags=["Cases"])
app.include_router(trial_university.router)
app.include_router(halo.router, prefix="/api", tags=["Halo"])
app.include_router(agents_status.router, prefix="/api", tags=["Agents Status"])
app.include_router(agents_stream.router, prefix="/api/agents", tags=["Agents Stream"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])

# DB init
from .database import engine, Base
from .models import service_of_process, document, recipient, user, role, user_role, permission, role_permission
Base.metadata.create_all(bind=engine)
