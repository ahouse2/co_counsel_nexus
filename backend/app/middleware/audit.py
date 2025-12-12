"""Audit logging middleware for tracking sensitive operations."""

from fastapi import Request
from datetime import datetime
import json
from pathlib import Path

# Audit log directory
AUDIT_LOG_DIR = Path("var/audit_logs")
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)


class AuditLogger:
    """Audit logger for sensitive operations."""
    
    SENSITIVE_PATHS = [
        "/api/auth/",
        "/api/users/",
        "/api/documents/",
        "/api/cases/",
        "/api/settings/",
    ]
    
    SENSITIVE_METHODS = ["POST", "PUT", "DELETE", "PATCH"]
    
    @staticmethod
    def should_audit(request: Request) -> bool:
        """Determine if request should be audited."""
        # Audit all sensitive methods on sensitive paths
        if request.method in AuditLogger.SENSITIVE_METHODS:
            for path in AuditLogger.SENSITIVE_PATHS:
                if request.url.path.startswith(path):
                    return True
        return False
    
    @staticmethod
    async def log_request(request: Request, user_id: str = None):
        """Log an auditable request."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "user_id": user_id or "anonymous",
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
        
        # Write to daily audit log file
        log_file = AUDIT_LOG_DIR / f"audit_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return log_entry


async def audit_middleware(request: Request, call_next):
    """Middleware to audit sensitive operations."""
    # Check if request should be audited
    if AuditLogger.should_audit(request):
        # Extract user ID from request if available
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
        
        # Log the request
        await AuditLogger.log_request(request, user_id)
    
    # Continue processing request
    response = await call_next(request)
    return response
