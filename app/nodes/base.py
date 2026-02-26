from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from app.graph.state import WorkflowState
from app.db.persistence import get_database


class NodeResult:
    def __init__(
        self,
        status: str,
        confidence: float,
        error_type: Optional[str] = None,
        retryable: bool = False,
        updates: Optional[Dict[str, Any]] = None,
    ):
        self.status = status
        self.confidence = confidence
        self.error_type = error_type
        self.retryable = retryable
        self.updates = updates or {}


class BaseNode(ABC):
    def __init__(self, node_name: str, cost: float = 1.0):
        self.node_name = node_name
        self.cost = cost

    def _check_budget(self, state: WorkflowState) -> bool:
        budget = state.get("budget_state", {})
        remaining = budget.get("total_budget", 0) - budget.get("spent", 0)
        return remaining >= self.cost

    def _deduct_budget(self, state: WorkflowState) -> None:
        if "budget_state" not in state:
            state["budget_state"] = {
                "total_budget": 100.0,
                "spent": 0.0,
                "node_costs": {},
            }
        state["budget_state"]["spent"] = (
            state["budget_state"].get("spent", 0) + self.cost
        )
        state["budget_state"]["node_costs"][self.node_name] = self.cost

    def _append_audit(
        self,
        state: WorkflowState,
        status: str,
        confidence: float,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "node_name": self.node_name,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "confidence": confidence,
            "error_type": error_type,
        }
        if details:
            entry["details"] = details

        if "audit_log" not in state:
            state["audit_log"] = []
        state["audit_log"].append(entry)

        db = get_database()
        db.append_audit_log(
            workflow_id=state["workflow_id"],
            node_name=self.node_name,
            status=status,
            confidence=confidence,
            error_type=error_type,
            details=details,
        )

    def _persist_state(self, state: WorkflowState) -> None:
        import json

        db = get_database()
        db.update_workflow_state(
            workflow_id=state["workflow_id"],
            state_json=json.dumps(state),
            status=state.get("status", "in_progress"),
            confidence=state.get("confidence", 0.0),
            current_node=self.node_name,
        )

    @abstractmethod
    def execute(self, state: WorkflowState) -> NodeResult:
        pass

    def run(self, state: WorkflowState) -> WorkflowState:
        if not self._check_budget(state):
            result = NodeResult(
                status="failure",
                confidence=0.0,
                error_type="budget_exceeded",
                retryable=False,
            )
            self._append_audit(
                state, result.status, result.confidence, result.error_type
            )
            state["status"] = "failed"
            state["error_state"] = {
                "error_type": "budget_exceeded",
                "node": self.node_name,
            }
            return state

        result = self.execute(state)

        if result.updates:
            state.update(result.updates)

        self._deduct_budget(state)
        self._append_audit(state, result.status, result.confidence, result.error_type)
        self._persist_state(state)

        state["status"] = "in_progress" if result.status == "success" else result.status
        state["confidence"] = (state.get("confidence", 0.0) + result.confidence) / 2

        if result.status == "failure":
            state["error_state"] = {
                "error_type": result.error_type,
                "node": self.node_name,
                "retryable": result.retryable,
            }

        return state


class SandboxableNode(BaseNode):
    def __init__(
        self, node_name: str, cost: float = 1.0, requires_sandbox: bool = True
    ):
        super().__init__(node_name, cost)
        self.requires_sandbox = requires_sandbox

    @abstractmethod
    def execute_in_sandbox(self, state: WorkflowState) -> NodeResult:
        pass

    def execute(self, state: WorkflowState) -> NodeResult:
        if self.requires_sandbox:
            return self.execute_in_sandbox(state)
        else:
            return self._execute_internal(state)

    @abstractmethod
    def _execute_internal(self, state: WorkflowState) -> NodeResult:
        pass
