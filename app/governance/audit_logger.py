import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime
from app.graph.state import WorkflowState
from app.db.persistence import get_database


def compute_deterministic_hash(data: Any) -> str:
    if isinstance(data, dict):
        serialized = json.dumps(data, sort_keys=True)
    elif isinstance(data, list):
        serialized = json.dumps(data, sort_keys=True)
    else:
        serialized = str(data)
    return hashlib.sha256(serialized.encode()).hexdigest()


def compute_state_hash(state: WorkflowState) -> str:
    relevant_fields = {
        "workflow_id": state.get("workflow_id"),
        "repo_url": state.get("repo_url"),
        "classification": state.get("classification"),
        "status": state.get("status"),
        "reflection_count": state.get("reflection_count"),
        "confidence": state.get("confidence"),
    }
    return compute_deterministic_hash(relevant_fields)


class AuditLogger:
    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    def log_step(
        self,
        state: WorkflowState,
        agent_name: str,
        step_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        reasoning_summary: Optional[str] = None,
        latency: float = 0.0,
        token_usage: int = 0,
        cost: float = 0.0,
        status: str = "success",
    ) -> None:
        workflow_id = state.get("workflow_id", "")

        inputs_hash = compute_deterministic_hash(inputs)
        outputs_hash = compute_deterministic_hash(outputs)

        self._get_db().append_workflow_step(
            workflow_id=workflow_id,
            step_id=step_id,
            agent_name=agent_name,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            reasoning_summary=reasoning_summary,
            latency=latency,
            token_usage=token_usage,
            cost=cost,
            status=status,
        )

    def log_node_execution(
        self,
        state: WorkflowState,
        node_name: str,
        inputs: Dict[str, Any],
        result: Dict[str, Any],
        latency: float = 0.0,
        status: str = "success",
    ) -> None:
        self.log_step(
            state=state,
            agent_name=node_name,
            step_id=f"{node_name}_{datetime.utcnow().isoformat()}",
            inputs=inputs,
            outputs=result,
            reasoning_summary=result.get("reasoning_summary"),
            latency=latency,
            token_usage=result.get("tokens_used", 0),
            cost=result.get("cost", 0.0),
            status=status,
        )

    def log_strategy_application(
        self, state: WorkflowState, strategy: str, success: bool
    ) -> None:
        workflow_id = state.get("workflow_id", "")
        self._get_db().append_workflow_step(
            workflow_id=workflow_id,
            step_id=f"strategy_{datetime.utcnow().isoformat()}",
            agent_name="StrategyApplyNode",
            inputs_hash=compute_deterministic_hash({"strategy": strategy}),
            outputs_hash=compute_deterministic_hash({"success": success}),
            reasoning_summary=f"Applied strategy: {strategy}, Success: {success}",
            status="success" if success else "failure",
        )

    def log_reflection(
        self, state: WorkflowState, analysis_result: Optional[Dict[str, Any]] = None
    ) -> None:
        workflow_id = state.get("workflow_id", "")
        reflection_count = state.get("reflection_count", 0)

        self._get_db().append_workflow_step(
            workflow_id=workflow_id,
            step_id=f"reflection_{reflection_count}_{datetime.utcnow().isoformat()}",
            agent_name="ReflectionNode",
            inputs_hash=compute_deterministic_hash(state.get("error_state", {})),
            outputs_hash=compute_deterministic_hash(analysis_result or {}),
            reasoning_summary=analysis_result.get("suggestion")
            if analysis_result
            else "No analysis available",
            status="success",
        )


_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
