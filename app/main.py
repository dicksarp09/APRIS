from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.workflow import router as workflow_router
from app.security.rbac import get_rbac_enforcer


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
