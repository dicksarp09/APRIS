from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from app.services.workflow_service import get_workflow_service
from app.security.rbac import get_rbac_enforcer, Permission


router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkflowStartRequest(BaseModel):
    repo_url: str
    mode: str = "deterministic"
    analysis_mode: str = "deep"  # "deep" or "shallow"
    max_files_analyze: int = 50  # Maximum files to analyze in deep mode

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

    @validator("analysis_mode")
    def validate_analysis_mode(cls, v):
        if v not in ["deep", "shallow"]:
            raise ValueError("Analysis mode must be 'deep' or 'shallow'")
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
        repo_url=request.repo_url,
        user_id=user_id,
        mode=request.mode,
        analysis_mode=request.analysis_mode,
        max_files_analyze=request.max_files_analyze,
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


@router.get("/compare")
async def compare_workflows(
    workflow_ids: str, user_id: str = Depends(get_current_user_id)
):
    rbac = get_rbac_enforcer()

    role = rbac.get_user_role(user_id)
    if not role:
        raise HTTPException(status_code=403, detail="User not authorized")

    service = get_workflow_service()
    ids = workflow_ids.split(",")

    if len(ids) < 2:
        raise HTTPException(
            status_code=400, detail="Provide at least 2 workflow IDs to compare"
        )

    if len(ids) > 5:
        raise HTTPException(
            status_code=400, detail="Maximum 5 workflows can be compared at once"
        )

    results = {}
    for workflow_id in ids:
        result = service.get_workflow_results(workflow_id)
        if result:
            results[workflow_id] = result
        else:
            results[workflow_id] = {"error": "Workflow not found or not completed"}

    comparison = _generate_comparison(results)

    return {
        "workflows": results,
        "comparison": comparison,
    }


def _generate_comparison(results: Dict[str, Any]) -> Dict[str, Any]:
    metrics = []

    for workflow_id, data in results.items():
        if "error" in data:
            continue

        metrics.append(
            {
                "workflow_id": workflow_id,
                "file_count": data.get("file_count", 0),
                "confidence": data.get("confidence", 0.0),
                "classification": data.get("classification", "unknown"),
                "primary_language": data.get("primary_language", ""),
                "architecture_score": data.get("architecture_score", 0.0),
                "maturity_score": data.get("maturity_score", {}).get("score", 0.0),
                "risk_level": data.get("risk_profile", {}).get(
                    "overall_risk", "unknown"
                ),
                "has_cycles": data.get("dependency_graph", {}).get("has_cycles", False),
                "complexity_avg": data.get("complexity_profile", {}).get(
                    "avg_complexity", 0.0
                ),
                "layer_violations": len(
                    data.get("dependency_graph", {}).get("layer_violations", [])
                ),
            }
        )

    if not metrics:
        return {"error": "No valid metrics to compare"}

    comparison_table = []
    metric_names = [
        ("file_count", "Files"),
        ("confidence", "Confidence"),
        ("maturity_score", "Maturity"),
        ("architecture_score", "Architecture"),
        ("complexity_avg", "Avg Complexity"),
        ("layer_violations", "Layer Violations"),
    ]

    for metric_key, metric_label in metric_names:
        row = {"metric": metric_label}
        values = []
        for m in metrics:
            row[m["workflow_id"]] = m.get(metric_key, "N/A")
            values.append(m.get(metric_key, 0))

        if values and not isinstance(values[0], str):
            best_idx = (
                values.index(max(values))
                if metric_key in ["confidence", "maturity_score", "architecture_score"]
                else values.index(min(values))
            )
            row["_best"] = metrics[best_idx]["workflow_id"]

        comparison_table.append(row)

    risk_row = {"metric": "Risk Level"}
    for m in metrics:
        risk_row[m["workflow_id"]] = m.get("risk_level", "unknown")
    comparison_table.append(risk_row)

    cycle_row = {"metric": "Circular Deps"}
    for m in metrics:
        cycle_row[m["workflow_id"]] = "Yes" if m.get("has_cycles") else "No"
    comparison_table.append(cycle_row)

    return {
        "table": comparison_table,
        "summary": {
            "total_workflows": len(metrics),
            "best_architecture": max(
                metrics, key=lambda x: x.get("architecture_score", 0)
            )["workflow_id"]
            if metrics
            else None,
            "highest_maturity": max(metrics, key=lambda x: x.get("maturity_score", 0))[
                "workflow_id"
            ]
            if metrics
            else None,
        },
    }
