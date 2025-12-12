"""Performance metrics endpoint for monitoring."""

from fastapi import APIRouter
from datetime import datetime
import psutil
import time

router = APIRouter()

# Track request metrics
request_count = 0
request_times = []
start_time = time.time()


@router.get("/metrics", tags=["Monitoring"])
def get_metrics() -> dict:
    """
    Get application performance metrics.
    
    Returns metrics in Prometheus-compatible format.
    """
    uptime = time.time() - start_time
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Calculate average response time
    avg_response_time = sum(request_times) / len(request_times) if request_times else 0
    
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(uptime, 2),
        
        # Application metrics
        "http_requests_total": request_count,
        "http_request_duration_avg_seconds": round(avg_response_time, 4),
        
        # System metrics
        "system_cpu_usage_percent": cpu_percent,
        "system_memory_usage_percent": memory.percent,
        "system_memory_available_bytes": memory.available,
        "system_disk_usage_percent": disk.percent,
        "system_disk_available_bytes": disk.free,
        
        # Process metrics
        "process_cpu_percent": psutil.Process().cpu_percent(),
        "process_memory_bytes": psutil.Process().memory_info().rss,
        "process_threads": psutil.Process().num_threads(),
    }
    
    return metrics


@router.get("/metrics/prometheus", tags=["Monitoring"])
def get_prometheus_metrics() -> str:
    """
    Get metrics in Prometheus text format.
    """
    metrics = get_metrics()
    
    # Convert to Prometheus format
    lines = [
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter",
        f"http_requests_total {metrics['http_requests_total']}",
        "",
        "# HELP system_cpu_usage_percent CPU usage percentage",
        "# TYPE system_cpu_usage_percent gauge",
        f"system_cpu_usage_percent {metrics['system_cpu_usage_percent']}",
        "",
        "# HELP system_memory_usage_percent Memory usage percentage",
        "# TYPE system_memory_usage_percent gauge",
        f"system_memory_usage_percent {metrics['system_memory_usage_percent']}",
        "",
        "# HELP system_disk_usage_percent Disk usage percentage",
        "# TYPE system_disk_usage_percent gauge",
        f"system_disk_usage_percent {metrics['system_disk_usage_percent']}",
        "",
    ]
    
    return "\n".join(lines)


def track_request(duration: float):
    """Track a request for metrics."""
    global request_count, request_times
    request_count += 1
    request_times.append(duration)
    
    # Keep only last 1000 requests
    if len(request_times) > 1000:
        request_times = request_times[-1000:]
