from typing import Dict, Any, Optional, List
from app.nodes.base import BaseNode, NodeResult
from app.graph.state import WorkflowState


CONFIDENCE_THRESHOLD_LOW = 0.5
CONFIDENCE_THRESHOLD_MEDIUM = 0.7
MAX_REFLECTION_LOOPS = 3


class DecisionNode(BaseNode):
    def __init__(self):
        super().__init__("DecisionNode", cost=0.2)

    def execute(self, state: WorkflowState) -> NodeResult:
        next_node = self._decide_next_node(state)

        return NodeResult(
            status="success",
            confidence=1.0,
            retryable=False,
            updates={"_next_node": next_node},
        )

    def _decide_next_node(self, state: WorkflowState) -> str:
        error_state = state.get("error_state", {})

        if error_state:
            return "FailureRouter"

        confidence = state.get("confidence", 0.0)
        reflection_count = state.get("reflection_count", 0)
        status = state.get("status", "")

        if status == "failed":
            return "CircuitBreaker"

        if reflection_count >= MAX_REFLECTION_LOOPS:
            return "CircuitBreaker"

        if confidence < CONFIDENCE_THRESHOLD_LOW:
            return "ReflectionNode"

        if confidence < CONFIDENCE_THRESHOLD_MEDIUM and reflection_count < 2:
            return "ReflectionNode"

        current_node = state.get("_next_node", "CloneRepo")
        return self._get_next_workflow_node(current_node)

    def _get_next_workflow_node(self, current_node: str) -> str:
        workflow_sequence = [
            "CloneRepo",
            "ProfileRepo",
            "ClassifyRepo",
            "SafetyScan",
            "ParseFiles",
            "SummarizeFiles",
            "ContentAnalysis",
            "BuildDependencyGraph",
            "ArchitectureSynthesis",
            "DocumentationGeneration",
            "AuditPersist",
        ]

        if current_node not in workflow_sequence:
            return "CloneRepo"

        try:
            current_idx = workflow_sequence.index(current_node)
            next_idx = current_idx + 1

            if next_idx >= len(workflow_sequence):
                return "END"

            return workflow_sequence[next_idx]
        except ValueError:
            return "CloneRepo"


class AutonomousOrchestrator:
    def __init__(self):
        self.decision_node = DecisionNode()
        self.max_iterations = 50

    def run_autonomous_loop(self, state: WorkflowState) -> WorkflowState:
        iteration = 0

        while (
            state.get("status") not in ["failed", "completed"]
            and iteration < self.max_iterations
        ):
            iteration += 1

            if iteration > 1:
                current = state.get("_next_node", "CloneRepo")
            else:
                current = "CloneRepo"

            if current == "END":
                state["status"] = "completed"
                break

            result = self._execute_node(current, state)
            state.update(result.updates)

            if result.status == "failure":
                state["error_state"] = {
                    "error_type": result.error_type,
                    "node": current,
                }

            decision_result = self.decision_node.execute(state)
            state.update(decision_result.updates)

            if state.get("_next_node") == "FailureRouter":
                from app.nodes.failure_handling import (
                    FailureRouterNode,
                    ReflectionNode,
                    RetryNode,
                    CircuitBreakerNode,
                )

                failure_router = FailureRouterNode()
                fr_result = failure_router.execute(state)
                state.update(fr_result.updates)

                routing = state.get("_routing", "continue")

                if routing == "circuit_breaker":
                    cb_node = CircuitBreakerNode()
                    cb_result = cb_node.execute(state)
                    state.update(cb_result.updates)
                    break
                elif routing == "retry":
                    reflection_node = ReflectionNode()
                    ref_result = reflection_node.execute(state)
                    state.update(ref_result.updates)

                    retry_node = RetryNode()
                    retry_result = retry_node.execute(state)
                    state.update(retry_result.updates)

        return state

    def _execute_node(self, node_name: str, state: WorkflowState) -> NodeResult:
        from app.graph.workflow import get_workflow_engine

        engine = get_workflow_engine()
        node_func = engine.nodes.get(node_name)

        if node_func:
            return node_func(state)

        return NodeResult(
            status="failure", confidence=0.0, error_type="node_not_found", updates={}
        )


_orchestrator: Optional[AutonomousOrchestrator] = None


def get_autonomous_orchestrator() -> AutonomousOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AutonomousOrchestrator()
    return _orchestrator
