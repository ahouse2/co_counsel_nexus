from __future__ import annotations
import os

from fastapi import (
    FastAPI,
)

from .config import get_settings
from .telemetry import setup_telemetry

settings = get_settings()
setup_telemetry(settings)
app = FastAPI(title=settings.app_name, version=settings.app_version)
# [dev] mTLS enabled
import ssl
from fastapi import Request, HTTPException

@app.middleware("http")
async def mtls_middleware(request: Request, call_next):
    if request.url.scheme == "https" and "ssl_client_cert" not in request.scope:
        raise HTTPException(status_code=403, detail="Client certificate required")
    response = await call_next(request)
    return response

from .api import retrieval

app.include_router(retrieval.router)
from .api import graph

app.include_router(graph.router)
from .api import agents

app.include_router(agents.router, prefix="/agents", tags=["Agents"])
from .api import scenarios

app.include_router(scenarios.router)

from .api import auth

app.include_router(auth.router)
from .api import evidence_binder

app.include_router(evidence_binder.router)

from .api import predictive_analytics

app.include_router(predictive_analytics.router)

from .api import settings

app.include_router(settings.router)
from .api import graphql

app.include_router(graphql.router)
from .api import health

app.include_router(health.router)
from .events import register_events

register_events(app)

from .api import billing
app.include_router(billing.router)

from .api import onboarding
app.include_router(onboarding.router)

from .api import legal_research
app.include_router(legal_research.router)

from .api import legal_theory

app.include_router(legal_theory.router)

from .api import argument_mapping

app.include_router(argument_mapping.router)

from .api import strategic_recommendations

app.include_router(strategic_recommendations.router)

from .api import timeline

app.include_router(timeline.router)

from .api import voice

app.include_router(voice.router)

from .api import ingestion

app.include_router(ingestion.router)

from .api import knowledge

app.include_router(knowledge.router)

from .api import dev_agent

app.include_router(dev_agent.router)

from .api import sandbox

app.include_router(sandbox.router)

from .api import cost

app.include_router(cost.router)

from .api import documents

app.include_router(documents.router)

from .api import forensics

app.include_router(forensics.router, prefix="/forensics", tags=["Forensics"])

from .api import knowledge_graph

app.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["Knowledge Graph"])

from .api import service_of_process

app.include_router(service_of_process.router, prefix="/api", tags=["Service of Process"])

from .api import users

app.include_router(users.router, prefix="/api", tags=["Users"])

from .api import cases

app.include_router(cases.router, prefix="/api", tags=["Cases"])

from .database import engine, Base
from .models import service_of_process, document, recipient, user, role, user_role, permission, role_permission

Base.metadata.create_all(bind=engine)
