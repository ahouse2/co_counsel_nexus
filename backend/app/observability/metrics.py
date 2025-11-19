from fastapi import APIRouter

router = APIRouter()

# Very small in-process metrics placeholder. Replace with real metrics in future.
_metrics = {
    "uptime_seconds": 0,
    "agent_tasks_completed": 0,
    "hitl_pending": 0,
}

@router.get('/metrics')
async def get_metrics():
    return _metrics
