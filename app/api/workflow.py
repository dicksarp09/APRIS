from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from app.services.workflow_service import get_workflow_service
from app.security.rbac import get_rbac_enforcer, Permission


router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkflowStartRequest(BaseModel):
    repo_url: str
    mode: str = "deterministic"

    @validator("repo_url")
    def validate_repo_url(cls, v):
        if not v.startswith("https://github.com/"):
            raise ValueError("Invalid GitHub repository URL")
        return v

    @validator("mode")
    def validate_mode(cls, v):
        if v not in ["deterministic", "adaptive"]:
            raise ValueError("Mode must be 'deterministic' or 'adaptive'")
        return v


class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str


class ApprovalRequest(BaseModel):
    notes: str = ""


def get_current_user_id(x_user_id: str = Header(default="anonymous")) -> str:
    return x_user_id


@router.post("/start", response_model=WorkflowResponse)
async def start_workflow(
    request: WorkflowStartRequest, user_id: str = Depends(get_current_user_id)
):
    service = get_workflow_service()
    rbac = get_rbac_enforcer()

    if not rbac.can_generate_docs(user_id):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to start workflow"
        )

    repo_check = service.validate_repo_access(request.repo_url)
    if not repo_check.get("accessible", False):
        raise HTTPException(
            status_code=400,
            detail=f"Repository not accessible: {repo_check.get('error', 'Unknown error')}",
        )

    repo_size = repo_check.get("size", 0)
    if not service.check_size_threshold(repo_size):
        raise HTTPException(
            status_code=400,
            detail=f"Repository size ({repo_size}KB) exceeds maximum threshold",
        )

    result = service.start_workflow(
        repo_url=request.repo_url, user_id=user_id, mode=request.mode
    )

    return WorkflowResponse(**result)


@router.get("/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str, user_id: str = Depends(get_current_user_id)
):
    service = get_workflow_service()
    rbac = get_rbac_enforcer()

    role = rbac.get_user_role(user_id)
    if not role:
        raise HTTPException(status_code=403, detail="User not authorized")

    status = service.get_workflow_status(workflow_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return status


@router.get("/{workflow_id}/audit")
async def get_workflow_audit(
    workflow_id: str, user_id: str = Depends(get_current_user_id)
):
    service = get_workflow_service()
    rbac = get_rbac_enforcer()

    role = rbac.get_user_role(user_id)
    if not role:
        raise HTTPException(status_code=403, detail="User not authorized")

    audit_log = service.get_audit_log(workflow_id)
    if audit_log is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {"workflow_id": workflow_id, "audit_log": audit_log}


@router.post("/{workflow_id}/approve")
async def approve_workflow(
    workflow_id: str,
    request: ApprovalRequest,
    user_id: str = Depends(get_current_user_id),
):
    service = get_workflow_service()
    rbac = get_rbac_enforcer()

    if not rbac.can_generate_docs(user_id):
        raise HTTPException(
            status_code=403, detail="Insufficient permissions to approve workflow"
        )

    result = service.approve_workflow(
        workflow_id=workflow_id, approver_id=user_id, notes=request.notes
    )

    if not result.get("success", False):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Approval failed")
        )

    return result


@router.get("/{workflow_id}/results")
async def get_workflow_results(
    workflow_id: str, user_id: str = Depends(get_current_user_id)
):
    service = get_workflow_service()
    rbac = get_rbac_enforcer()

    role = rbac.get_user_role(user_id)
    if not role:
        raise HTTPException(status_code=403, detail="User not authorized")

    results = service.get_workflow_results(workflow_id)
    if results is None:
        raise HTTPException(
            status_code=404, detail="Workflow not found or not completed"
        )

    return results


@router.get("")
async def list_workflows(user_id: str = Depends(get_current_user_id)):
    rbac = get_rbac_enforcer()

    role = rbac.get_user_role(user_id)
    if not role:
        raise HTTPException(status_code=403, detail="User not authorized")

    from app.security.database import get_database

    db = get_database()
    workflows = db.list_incomplete_workflows()

    return {"workflows": workflows}
