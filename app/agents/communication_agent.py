import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.graph.state import WorkflowState
from app.db.persistence import get_database


class CommunicationAgent:
    def __init__(self):
        self._github_token = None
        self._initialized = False

    def _initialize(self):
        if self._initialized:
            return
        self._github_token = os.environ.get("GITHUB_TOKEN")
        self._initialized = True

    def _validate_token(self) -> bool:
        self._initialize()
        return bool(self._github_token)

    def _append_audit(
        self, state: WorkflowState, action: str, result: Dict[str, Any]
    ) -> None:
        entry = {
            "node_name": f"CommunicationAgent:{action}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": result.get("status", "unknown"),
            "confidence": 1.0,
            "action": action,
            "authorized": result.get("authorized", False),
        }
        if "audit_log" not in state:
            state["audit_log"] = []
        state["audit_log"].append(entry)

        db = get_database()
        db.append_audit_log(
            workflow_id=state["workflow_id"],
            node_name=f"CommunicationAgent:{action}",
            status=entry["status"],
            confidence=entry["confidence"],
            details={"action": action, "authorized": entry["authorized"]},
        )

    def post_github_comment(
        self,
        repo_url: str,
        body: str,
        state: WorkflowState,
        pr_number: Optional[int] = None,
        issue_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not self._validate_token():
            result = {
                "status": "failure",
                "error_type": "unauthorized",
                "message": "GitHub token not configured",
                "authorized": False,
            }
            self._append_audit(state, "post_comment", result)
            return result

        if not state.get("_require_approval", False):
            result = {
                "status": "failure",
                "error_type": "not_authorized",
                "message": "Workflow not in approval-required state",
                "authorized": False,
            }
            self._append_audit(state, "post_comment", result)
            return result

        try:
            import requests

            headers = {
                "Authorization": f"token {self._github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")

            if pr_number:
                url = f"https://api.github.com/repos/{repo_path}/issues/{pr_number}/comments"
            elif issue_number:
                url = f"https://api.github.com/repos/{repo_path}/issues/{issue_number}/comments"
            else:
                url = f"https://api.github.com/repos/{repo_path}/contents"

            response = requests.post(
                url, headers=headers, json={"body": body}, timeout=30
            )

            if response.status_code in (200, 201):
                result = {
                    "status": "success",
                    "authorized": True,
                    "comment_url": response.json().get("html_url", ""),
                    "message": "Comment posted successfully",
                }
            else:
                result = {
                    "status": "failure",
                    "error_type": "api_error",
                    "message": f"GitHub API returned {response.status_code}",
                    "authorized": True,
                }

        except Exception as e:
            result = {
                "status": "failure",
                "error_type": "execution_error",
                "message": str(e),
                "authorized": True,
            }

        self._append_audit(state, "post_comment", result)
        return result

    def log_approval(
        self, approver: str, state: WorkflowState, notes: str = ""
    ) -> Dict[str, Any]:
        if "short_term_memory" not in state:
            state["short_term_memory"] = {}

        approvals = state["short_term_memory"].get("approvals", [])
        approvals.append(
            {
                "approver": approver,
                "timestamp": datetime.utcnow().isoformat(),
                "notes": notes,
            }
        )
        state["short_term_memory"]["approvals"] = approvals

        result = {"status": "success", "authorized": True, "approver": approver}

        self._append_audit(state, "log_approval", result)
        return result

    def record_authorization(
        self,
        action: str,
        authorized_by: str,
        state: WorkflowState,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if "short_term_memory" not in state:
            state["short_term_memory"] = {}

        auth_records = state["short_term_memory"].get("authorizations", [])
        auth_records.append(
            {
                "action": action,
                "authorized_by": authorized_by,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {},
            }
        )
        state["short_term_memory"]["authorizations"] = auth_records

        result = {"status": "success", "action": action, "authorized_by": authorized_by}

        self._append_audit(state, "record_authorization", result)
        return result

    def request_human_approval(
        self, state: WorkflowState, reason: str
    ) -> Dict[str, Any]:
        state["_require_approval"] = True

        if "short_term_memory" not in state:
            state["short_term_memory"] = {}

        state["short_term_memory"]["pending_approvals"] = state[
            "short_term_memory"
        ].get("pending_approvals", [])
        state["short_term_memory"]["pending_approvals"].append(
            {"reason": reason, "timestamp": datetime.utcnow().isoformat()}
        )

        result = {"status": "success", "pending": True, "reason": reason}

        self._append_audit(state, "request_approval", result)
        return result


_communication_agent: Optional[CommunicationAgent] = None


def get_communication_agent() -> CommunicationAgent:
    global _communication_agent
    if _communication_agent is None:
        _communication_agent = CommunicationAgent()
    return _communication_agent
