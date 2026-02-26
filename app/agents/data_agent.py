from typing import Dict, Any, Optional, List
from datetime import datetime
from app.graph.state import WorkflowState
from app.db.persistence import get_database
from app.memory.chroma_store import get_chroma_store


class DataAgent:
    def _append_audit(
        self, state: WorkflowState, query_type: str, result: Dict[str, Any]
    ) -> None:
        entry = {
            "node_name": f"DataAgent:{query_type}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success" if result.get("status") == "success" else "failure",
            "confidence": 1.0,
            "query_type": query_type,
        }
        if "audit_log" not in state:
            state["audit_log"] = []
        state["audit_log"].append(entry)

        db = get_database()
        db.append_audit_log(
            workflow_id=state["workflow_id"],
            node_name=f"DataAgent:{query_type}",
            status=entry["status"],
            confidence=entry["confidence"],
            details={"query_type": query_type},
        )

    def query_memory(
        self, query_type: str, filters: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        if query_type == "failure_history":
            return self._query_failure_history(filters, state)
        elif query_type == "successful_strategies":
            return self._query_successful_strategies(filters, state)
        elif query_type == "workflow_logs":
            return self._query_workflow_logs(filters, state)
        elif query_type == "repo_patterns":
            return self._query_repo_patterns(filters, state)
        else:
            return {
                "status": "failure",
                "error_type": "invalid_query_type",
                "message": f"Unknown query type: {query_type}",
            }

    def _query_failure_history(
        self, filters: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        workflow_id = filters.get("workflow_id")
        if not workflow_id:
            workflow_id = state.get("workflow_id", "")

        db = get_database()
        audit_log = db.get_audit_log(workflow_id)

        failures = [entry for entry in audit_log if entry.get("status") == "failure"]

        result = {
            "status": "success",
            "query_type": "failure_history",
            "failures": failures,
            "count": len(failures),
        }

        self._append_audit(state, "failure_history", result)
        return result

    def _query_successful_strategies(
        self, filters: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        error_signature = filters.get("error_signature", "")
        repo_type = filters.get("repo_type", state.get("classification", ""))

        chroma = get_chroma_store()
        strategies = chroma.query_successful_strategies(
            error_signature=error_signature, n_results=filters.get("n_results", 5)
        )

        result = {
            "status": "success",
            "query_type": "successful_strategies",
            "strategies": strategies,
            "count": len(strategies),
        }

        self._append_audit(state, "successful_strategies", result)
        return result

    def _query_workflow_logs(
        self, filters: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        workflow_id = filters.get("workflow_id", state.get("workflow_id", ""))

        db = get_database()
        audit_log = db.get_audit_log(workflow_id)

        result = {
            "status": "success",
            "query_type": "workflow_logs",
            "logs": audit_log,
            "count": len(audit_log),
        }

        self._append_audit(state, "workflow_logs", result)
        return result

    def _query_repo_patterns(
        self, filters: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        query_text = filters.get("query_text", "")
        repo_type = filters.get("repo_type")
        language = filters.get("language")

        chroma = get_chroma_store()
        patterns = chroma.query_repo_patterns(
            query_text=query_text,
            repo_type=repo_type,
            language=language,
            n_results=filters.get("n_results", 3),
        )

        result = {
            "status": "success",
            "query_type": "repo_patterns",
            "patterns": patterns,
            "count": len(patterns),
        }

        self._append_audit(state, "repo_patterns", result)
        return result


_data_agent: Optional[DataAgent] = None


def get_data_agent() -> DataAgent:
    global _data_agent
    if _data_agent is None:
        _data_agent = DataAgent()
    return _data_agent
