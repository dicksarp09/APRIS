from fastapi import FastAPI
from app.api.workflow import router as workflow_router
from app.security.rbac import get_rbac_enforcer


app = FastAPI(
    title="APRIS - Autonomous Public Repository Intelligence System",
    description="Enterprise deterministic workflow engine for repository analysis",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    rbac = get_rbac_enforcer()
    from app.security.database import get_database

    db = get_database()

    try:
        rbac.create_user("admin", "admin")
    except:
        pass


app.include_router(workflow_router)


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
