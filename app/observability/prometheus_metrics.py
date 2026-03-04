from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import APIRouter, Response
from typing import Dict
import time

router = APIRouter(tags=["metrics"])

# HTTP Request Metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# LLM Metrics
llm_calls_total = Counter(
    "llm_calls_total", "Total LLM API calls", ["provider", "model", "status"]
)

llm_tokens_total = Counter(
    "llm_tokens_total", "Total LLM tokens used", ["provider", "model", "token_type"]
)

# Budget Metrics
budget_exceeded_total = Counter(
    "budget_exceeded_total", "Total times budget was exceeded", ["budget_type"]
)

budget_usage = Gauge(
    "budget_usage_percent", "Current budget usage percentage", ["budget_type"]
)

# Workflow Metrics
workflows_active = Gauge("workflows_active", "Number of active workflows")

workflows_completed_total = Counter(
    "workflows_completed_total", "Total completed workflows", ["status"]
)

# File Analysis Metrics
files_analyzed_total = Counter("files_analyzed_total", "Total files analyzed")

analysis_duration_seconds = Histogram(
    "analysis_duration_seconds",
    "Time taken for repository analysis",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)


class MetricsMiddleware:
    def __init__(self):
        self.request_count = 0
        self.start_time = time.time()

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status)
        ).inc()

        request_latency_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )


# Singleton instance
_metrics_middleware = MetricsMiddleware()


def get_metrics_middleware() -> MetricsMiddleware:
    return _metrics_middleware


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/health/metrics")
async def metrics_health():
    """Health check for metrics system"""
    return {
        "status": "healthy",
        "metrics": {
            "http_requests": http_requests_total._value.get(),
            "llm_calls": llm_calls_total._value.get(),
            "llm_tokens": llm_tokens_total._value.get(),
        },
    }
