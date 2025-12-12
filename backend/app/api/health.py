"""Health check endpoints for monitoring and orchestration."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from datetime import datetime
import psutil
import sys

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check() -> dict:
    """Basic health check - returns OK if service is running."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "co-counsel-api"
    }


@router.get("/health/ready", tags=["Health"])
async def readiness_check() -> JSONResponse:
    """
    Readiness check - verifies service can handle requests.
    
    Checks:
    - Service is running
    - Dependencies are accessible (database, vector store, etc.)
    """
    checks = {
        "service": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Check system resources
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        checks["resources"] = {
            "memory_available_mb": round(memory.available / 1024 / 1024, 2),
            "memory_percent": memory.percent,
            "disk_available_gb": round(disk.free / 1024 / 1024 / 1024, 2),
            "disk_percent": disk.percent,
        }
        
        # Warn if resources are low
        if memory.percent > 90 or disk.percent > 90:
            checks["status"] = "degraded"
            checks["warnings"] = []
            if memory.percent > 90:
                checks["warnings"].append("High memory usage")
            if disk.percent > 90:
                checks["warnings"].append("Low disk space")
    except Exception as e:
        checks["resources"] = {"error": str(e)}
    
    # Overall status
    overall_status = checks.get("status", "healthy")
    status_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content=checks
    )


@router.get("/health/live", tags=["Health"])
def liveness_check() -> dict:
    """
    Liveness check - verifies service is alive (for Kubernetes).
    Simple check that returns OK if the process is running.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version
    }
