from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.api.workflow import router as workflow_router
from app.security.rbac import get_rbac_enforcer
import time


app = FastAPI(
    title="APRIS - Autonomous Public Repository Intelligence System",
    description="Enterprise deterministic workflow engine for repository analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Prometheus metrics middleware
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Record metrics
        try:
            from app.observability.prometheus_metrics import (
                http_requests_total,
                request_latency_seconds,
                get_metrics_middleware,
            )

            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=str(response.status_code),
            ).inc()

            request_latency_seconds.labels(
                method=request.method, endpoint=request.url.path
            ).observe(duration)
        except Exception:
            pass

        return response


app.add_middleware(MetricsMiddleware)


@app.on_event("startup")
async def startup_event():
    rbac = get_rbac_enforcer()
    from app.security.database import get_database

    db = get_database()

    try:
        rbac.create_user("admin", "admin")
    except:
        pass

    try:
        rbac.create_user("anonymous", "operator")
    except:
        pass


app.include_router(workflow_router)

# Add metrics router
from app.observability.prometheus_metrics import router as metrics_router

app.include_router(metrics_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {
        "name": "APRIS",
        "version": "1.0.0",
        "description": "Autonomous Public Repository Intelligence System",
    }
