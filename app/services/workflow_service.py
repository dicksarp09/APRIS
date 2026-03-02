import json
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.security.database import get_database
from app.graph.state import WorkflowState, create_initial_state


class WorkflowService:
    def __init__(self):
        self._db = None
        self._workflow_engine = None

    def _get_db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    def _get_workflow_engine(self):
        if self._workflow_engine is None:
            from app.graph.workflow import get_workflow_engine

            self._workflow_engine = get_workflow_engine()
        return self._workflow_engine

    def start_workflow(
        self, repo_url: str, user_id: str, mode: str = "deterministic"
    ) -> Dict[str, Any]:
        workflow_id = str(uuid.uuid4())

        initial_state = create_initial_state(workflow_id, repo_url)
        initial_state["status"] = "started"
        initial_state["user_id"] = user_id
        initial_state["mode"] = mode

        state_json = json.dumps(initial_state)

        self._get_db().create_workflow(
            workflow_id=workflow_id,
            repo_url=repo_url,
            state_json=state_json,
            user_id=user_id,
        )

        asyncio.create_task(self._execute_workflow_async(workflow_id))

        return {"workflow_id": workflow_id, "status": "started"}

    async def _execute_workflow_async(self, workflow_id: str):
        try:
            engine = self._get_workflow_engine()
            engine.run_workflow(workflow_id)
        except Exception as e:
            state = self.get_workflow_state(workflow_id)
            if state:
                state["status"] = "failed"
                state["error_state"] = {
                    "error_type": "execution_error",
                    "message": str(e),
                }
                self._get_db().update_workflow_state(
                    workflow_id=workflow_id,
                    state_json=json.dumps(state),
                    status="failed",
                    confidence=state.get("confidence", 0.0),
                )

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        workflow_data = db.get_workflow_state(workflow_id)

        if not workflow_data:
            return None

        state = (
            json.loads(workflow_data["state_json"])
            if workflow_data.get("state_json")
            else {}
        )

        return {
            "workflow_id": workflow_id,
            "status": workflow_data.get("status", "unknown"),
            "current_step": workflow_data.get("current_node", ""),
            "confidence": workflow_data.get("confidence", 0.0),
            "budget_used": state.get("budget_state", {}),
            "reflection_count": workflow_data.get("reflection_count", 0),
        }

    def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        workflow_data = db.get_workflow_state(workflow_id)

        if not workflow_data or not workflow_data.get("state_json"):
            return None

        return json.loads(workflow_data["state_json"])

    def get_audit_log(self, workflow_id: str) -> List[Dict[str, Any]]:
        db = self._get_db()
        return db.get_audit_log(workflow_id)

    def approve_workflow(
        self, workflow_id: str, approver_id: str, notes: str = ""
    ) -> Dict[str, Any]:
        db = self._get_db()
        current_status = db.get_workflow_status(workflow_id)

        if current_status != "awaiting_approval":
            return {
                "success": False,
                "error": f"Workflow not awaiting approval (status: {current_status})",
            }

        state = self.get_workflow_state(workflow_id)
        if not state:
            return {"success": False, "error": "Workflow not found"}

        state["status"] = "approved"
        state["_approval"] = {
            "approver_id": approver_id,
            "timestamp": datetime.utcnow().isoformat(),
            "notes": notes,
        }

        db.update_workflow_state(
            workflow_id=workflow_id,
            state_json=json.dumps(state),
            status="approved",
            confidence=state.get("confidence", 0.0),
        )

        asyncio.create_task(self._execute_workflow_async(workflow_id))

        return {"success": True, "status": "approved"}

    def get_workflow_results(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        status = db.get_workflow_status(workflow_id)

        if status != "completed":
            return None

        state = self.get_workflow_state(workflow_id)
        if not state:
            return None

        architecture_analysis = self._get_architecture_analysis(state)

        return {
            "architecture_summary": state.get("architecture_summary", ""),
            "documentation": state.get("documentation", ""),
            "dependency_graph": state.get("dependency_graph", {}),
            "classification": state.get("classification", ""),
            "file_count": len(state.get("file_index", [])),
            "confidence": state.get("confidence", 0.0),
            "primary_language": state.get("primary_language", ""),
            "architecture_score": architecture_analysis.get("architecture_score", 0.0),
            "maturity_score": architecture_analysis.get("maturity_score", {}),
            "complexity_profile": architecture_analysis.get("complexity_profile", {}),
            "risk_profile": architecture_analysis.get("risk_profile", {}),
        }

    def _get_architecture_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from app.nodes.advanced_analysis import analyze_architecture

            return analyze_architecture(state)
        except Exception as e:
            return {"error": str(e)}

    def validate_repo_access(self, repo_url: str) -> Dict[str, Any]:
        import requests

        path = repo_url.replace("https://github.com/", "").rstrip("/")
        github_api_url = f"https://api.github.com/repos/{path}"

        try:
            response = requests.get(github_api_url, timeout=10)
            if response.status_code == 200:
                repo_data = response.json()
                return {
                    "accessible": True,
                    "size": repo_data.get("size", 0),
                    "language": repo_data.get("language", ""),
                    "stars": repo_data.get("stargazers_count", 0),
                    "private": repo_data.get("private", False),
                }
            else:
                return {
                    "accessible": False,
                    "error": f"GitHub API returned {response.status_code}",
                }
        except Exception as e:
            return {"accessible": False, "error": str(e)}

    def check_size_threshold(self, repo_size_kb: int, max_size_mb: int = 100) -> bool:
        max_size_kb = max_size_mb * 1024
        return repo_size_kb <= max_size_kb

    def export_to_json(self, workflow_id: str) -> Optional[str]:
        """Export workflow results to JSON format"""
        state = self.get_workflow_state(workflow_id)
        if not state:
            return None

        export_data = {
            "workflow_id": workflow_id,
            "repo_url": state.get("repo_url", ""),
            "classification": state.get("classification", ""),
            "primary_language": state.get("primary_language", ""),
            "file_count": len(state.get("file_index", [])),
            "project_description": state.get("project_description", {}),
            "dependencies": state.get("dependencies", {}),
            "config_info": state.get("config_info", {}),
            "file_summaries": state.get("file_summaries", {}),
            "documentation": state.get("documentation", ""),
            "architecture_summary": state.get("architecture_summary", ""),
            "confidence": state.get("confidence", 0.0),
        }

        return json.dumps(export_data, indent=2)

    def export_to_html(self, workflow_id: str) -> Optional[str]:
        """Export workflow results to HTML format"""
        state = self.get_workflow_state(workflow_id)
        if not state:
            return None

        project_desc = state.get("project_description", {})
        llm_summary = project_desc.get("llm_summary", "")
        primary_lang = state.get("primary_language", "Unknown")
        file_count = len(state.get("file_index", []))
        dependencies = state.get("dependencies", {})
        doc = state.get("documentation", "")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repository Analysis - {state.get("repo_url", "").split("/")[-1]}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        .card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
        .tag {{ display: inline-block; background: #e0e0e0; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; margin: 2px; }}
        .code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 8px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{state.get("repo_url", "").split("/")[-1]}</h1>
        <p class="meta">URL: {state.get("repo_url", "")}</p>
        <p class="meta">Language: {primary_lang} | Files: {file_count} | Confidence: {state.get("confidence", 0.0):.1%}</p>
    </div>
"""

        if llm_summary:
            html += f"""
    <div class="card">
        <h2>AI Summary</h2>
        <p>{llm_summary}</p>
    </div>
"""

        all_deps = []
        for lang, deps in dependencies.items():
            if deps:
                all_deps.extend(deps[:8])

        if all_deps:
            html += f"""
    <div class="card">
        <h2>Dependencies</h2>
        <div>{"".join(f'<span class="tag">{d}</span>' for d in all_deps[:20])}</div>
    </div>
"""

        html += f"""
    <div class="card">
        <h2>Analysis</h2>
        <pre>{doc[:5000]}</pre>
    </div>
</body>
</html>"""

        return html


_workflow_service: Optional[WorkflowService] = None


def get_workflow_service() -> WorkflowService:
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowService()
    return _workflow_service
