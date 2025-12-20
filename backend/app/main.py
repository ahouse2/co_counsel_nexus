from __future__ import annotations
from fastapi import FastAPI, Request, HTTPException

from .config import get_settings
from .telemetry import setup_telemetry
from .events import register_events

# Routers
from .api import retrieval, graph, agents, scenarios, auth, evidence_binder, predictive_analytics, settings as settings_api, graphql, health, billing, onboarding, legal_research, legal_theory, argument_mapping, strategic_recommendations, timeline, voice, ingestion, knowledge, dev_agent, sandbox, cost, documents, document_drafting, binder_preparation, feedback, mock_trial, forensics, knowledge_graph, service_of_process, users, cases, trial_university, halo, agents_status, agents_stream, memory, autonomous_scraping, autonomous_courtlistener, video_generation, narrative, adversarial, evidence_map, simulation, jury_sentiment, metrics, context, intelligence, devils_advocate, financial_forensics, swarms, agent_console
from .memory_store import CaseMemoryStore
from .api import memory

# Configure structured logging
import structlog
import logging

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)

logger = structlog.get_logger()

settings = get_settings()
setup_telemetry(settings)
app = FastAPI(title=settings.app_name, version=settings.app_version)

# Audit Logging
# try:
#     from .middleware.audit import audit_middleware
#     app.middleware("http")(audit_middleware)
# except ImportError:
#     logger.warning("Audit middleware not available")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Development
        "http://localhost:8088",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:8088",
        "http://127.0.0.1:8080",
        # Production - configured via environment variable
        # Set CORS_ORIGINS="https://app.yourdomain.com,https://yourdomain.com" in production
        *([origin.strip() for origin in settings.cors_origins.split(",")] if hasattr(settings, 'cors_origins') and settings.cors_origins else []),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Security headers for production
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute", "1000/hour"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request Size Limit (500MB for large legal documents)
# @app.middleware("http")
# async def limit_request_size(request: Request, call_next):
#     max_size = 500 * 1024 * 1024  # 500MB
#     if request.headers.get("content-length"):
#         content_length = int(request.headers["content-length"])
#         if content_length > max_size:
#             raise HTTPException(
#                 status_code=413,
#                 detail=f"Request body too large. Maximum size is {max_size} bytes (500MB)"
#             )
#     response = await call_next(request)
#     return response

# [dev] mTLS enabled (production would disable this in prod)
import ssl


# @app.middleware("http")
# async def mtls_middleware(request: Request, call_next):
#     if request.url.scheme == "https" and "ssl_client_cert" not in request.scope:
#         raise HTTPException(status_code=403, detail="Client certificate required")
#     response = await call_next(request)
#     return response

# Include routers (order kept sensible)
app.include_router(retrieval.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(scenarios.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(evidence_binder.router, prefix="/api")
app.include_router(predictive_analytics.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api", tags=["Settings"])
app.include_router(graphql.router, prefix="/api")
app.include_router(health.router)
register_events(app)
app.include_router(billing.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(legal_research.router, prefix="/api")
app.include_router(legal_theory.router, prefix="/api")
app.include_router(argument_mapping.router, prefix="/api")
app.include_router(strategic_recommendations.router, prefix="/api")
app.include_router(timeline.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(dev_agent.router, prefix="/api")
app.include_router(sandbox.router, prefix="/api")
app.include_router(cost.router, prefix="/api")
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(document_drafting.router, prefix="/api")
app.include_router(binder_preparation.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(mock_trial.router, prefix="/api")
app.include_router(forensics.router, prefix="/api/forensics", tags=["Forensics"])
app.include_router(knowledge_graph.router, prefix="/api/knowledge-graph", tags=["Knowledge Graph"])
app.include_router(service_of_process.router, prefix="/api", tags=["Service of Process"])

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(trial_university.router, prefix="/api")
app.include_router(halo.router, prefix="/api", tags=["Halo"])
app.include_router(agents_status.router, prefix="/api", tags=["Agents Status"])
app.include_router(agents_stream.router, prefix="/api/agents", tags=["Agents Stream"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(autonomous_scraping.router, prefix="/api", tags=["Autonomous Scraping"])
app.include_router(autonomous_courtlistener.router, prefix="/api", tags=["Autonomous CourtListener"])
app.include_router(video_generation.router, prefix="/api", tags=["Video Generation"])
app.include_router(context.router, prefix="/api/context", tags=["context"]) # Added
app.include_router(simulation.router, prefix="/api", tags=["Simulation"]) # Added

app.include_router(narrative.router, prefix="/api/narrative", tags=["Narrative"])
app.include_router(adversarial.router, prefix="/api/adversarial", tags=["Adversarial"])
app.include_router(evidence_map.router, prefix="/api/evidence-map", tags=["Evidence Map"])
app.include_router(devils_advocate.router, prefix="/api/devils-advocate", tags=["Devil's Advocate"])
app.include_router(financial_forensics.router, prefix="/api/financial", tags=["Financial Forensics"])
app.include_router(jury_sentiment.router, prefix="/api", tags=["Jury Sentiment"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["Intelligence"])
app.include_router(swarms.router, prefix="/api", tags=["Swarms"])
app.include_router(agent_console.router, prefix="/api", tags=["Agent Console"])

# DB init
from .database import engine, Base
from .models import service_of_process, document, recipient, role, user_role, permission, role_permission, case
Base.metadata.create_all(bind=engine)

# ═══════════════════════════════════════════════════════════════════════════
# AUTONOMOUS ORCHESTRATOR LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("Starting AutonomousOrchestrator...")
    from .services.autonomous_orchestrator import startup_orchestrator
    await startup_orchestrator()
    logger.info("AutonomousOrchestrator started successfully")
    
    yield
    
    # Shutdown
    logger.info("Stopping AutonomousOrchestrator...")
    from .services.autonomous_orchestrator import shutdown_orchestrator
    await shutdown_orchestrator()
    logger.info("AutonomousOrchestrator stopped")

# Apply lifespan to app
app.router.lifespan_context = lifespan

