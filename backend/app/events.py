from .services.agents import get_agents_service
from .services.ingestion import (
    get_ingestion_worker,
    shutdown_ingestion_worker,
)

def register_events(app):
    @app.on_event("startup")
    def start_background_workers() -> None:
        get_ingestion_worker()
        get_agents_service()


    @app.on_event("shutdown")
    def stop_background_workers() -> None:
        shutdown_ingestion_worker(timeout=5.0)
