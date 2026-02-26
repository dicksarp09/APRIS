from typing import Dict, Any, Optional
from app.nodes.base import BaseNode, NodeResult
from app.graph.state import WorkflowState
from app.governance.budget_manager import get_budget_manager
from app.governance.audit_logger import get_audit_logger


MAX_REFLECTION_COUNT = 2


class FailureRouterNode(BaseNode):
    def __init__(self):
        super().__init__("FailureRouter", cost=0.1)
        self._budget_manager = get_budget_manager()
        self._audit_logger = get_audit_logger()

    def execute(self, state: WorkflowState) -> NodeResult:
        error_state = state.get("error_state", {})
        reflection_count = state.get("reflection_count", 0)

        self._budget_manager.initialize_budget(state)

        if not error_state:
            return NodeResult(
                status="success",
                confidence=1.0,
                retryable=False,
                updates={"_routing": "continue"},
            )

        retryable = error_state.get("retryable", False)

        self._audit_logger.log_node_execution(
            state=state,
            node_name="FailureRouter",
            inputs={"error_state": error_state, "reflection_count": reflection_count},
            outputs={"routing": "circuit_breaker" if not retryable else "retry"},
            status="success",
        )

        if not retryable:
            return NodeResult(
                status="success",
                confidence=1.0,
                retryable=False,
                updates={"_routing": "circuit_breaker"},
            )

        budget_check = self._budget_manager.check_reflection_limit(state)
        if (
            not budget_check.get("allowed")
            and budget_check.get("action") == "circuit_breaker"
        ):
            return NodeResult(
                status="success",
                confidence=1.0,
                retryable=False,
                updates={"_routing": "circuit_breaker"},
            )

        if reflection_count >= MAX_REFLECTION_COUNT:
            return NodeResult(
                status="success",
                confidence=1.0,
                retryable=False,
                updates={"_routing": "circuit_breaker"},
            )

        from app.memory.failure_memory import FailureMemorySystem

        failure_memory = FailureMemorySystem()
        failure_memory.process_failure(state)

        return NodeResult(
            status="success",
            confidence=1.0,
            retryable=False,
            updates={"_routing": "retry"},
        )


class ReflectionNode(BaseNode):
    def __init__(self):
        super().__init__("ReflectionNode", cost=0.5)
        self._budget_manager = get_budget_manager()
        self._audit_logger = get_audit_logger()

    def execute(self, state: WorkflowState) -> NodeResult:
        error_state = state.get("error_state", {})
        reflection_count = state.get("reflection_count", 0)
        failed_node = error_state.get("node", "unknown")
        error_type = error_state.get("error_type", "unknown")
        error_message = error_state.get("message", "")

        strategy_found = state.get("_strategy_found", False)
        retrieved_strategy = state.get("_retrieved_strategy", "")
        strategy_confidence = state.get("_strategy_confidence", 0.0)

        if strategy_found and retrieved_strategy:
            applied_strategies = state.get("applied_strategies", [])
            applied_strategies.append(
                {
                    "strategy": retrieved_strategy,
                    "confidence": strategy_confidence,
                    "retry_number": reflection_count + 1,
                }
            )
            state["applied_strategies"] = applied_strategies

            self._audit_logger.log_strategy_application(
                state=state, strategy=retrieved_strategy, success=True
            )

            reflection = {
                "analyzing_node": failed_node,
                "error_type": error_type,
                "strategy_found": True,
                "applied_strategy": retrieved_strategy,
                "confidence": strategy_confidence,
                "suggestion": f"Apply strategy: {retrieved_strategy}",
            }
        else:
            budget_check = self._budget_manager.check_llm_budget(
                state, estimated_tokens=500
            )

            if budget_check.get("allowed"):
                reflection = self._analyze_failure_with_llm(
                    failed_node, error_type, error_message, state
                )
                state["reflection_count"] = reflection_count + 1
            else:
                reflection = {
                    "analyzing_node": failed_node,
                    "error_type": error_type,
                    "suggestion": f"Retry {failed_node} - LLM budget exceeded",
                    "budget_exceeded": True,
                }
                state["reflection_count"] = reflection_count + 1

        self._audit_logger.log_reflection(state, reflection)

        return NodeResult(
            status="success",
            confidence=0.7 if not strategy_found else 0.85,
            retryable=False,
            updates={
                "reflection_count": state["reflection_count"],
                "_reflection": reflection,
                "_retry_node": failed_node,
            },
        )

    def _analyze_failure_with_llm(
        self, node: str, error_type: str, error_message: str, state: WorkflowState
    ) -> dict:
        from app.agents.analysis_agent import get_analysis_agent
        import time

        start_time = time.time()

        analysis_agent = get_analysis_agent()

        result = analysis_agent.run_analysis(
            task_type="root_cause",
            input_data={
                "failed_node": node,
                "error_type": error_type,
                "error_message": error_message,
                "classification": state.get("classification", "unknown"),
            },
            state=state,
        )

        latency = time.time() - start_time

        self._audit_logger.log_node_execution(
            state=state,
            node_name="AnalysisAgent",
            inputs={"task": "root_cause", "failed_node": node},
            outputs=result,
            latency=latency,
            status=result.get("status", "failure"),
        )

        if result.get("status") == "success":
            return {
                "analyzing_node": node,
                "error_type": error_type,
                "llm_analysis": result.get("analysis", ""),
                "suggestion": "Retry after analysis",
            }

        return {
            "analyzing_node": node,
            "error_type": error_type,
            "suggestion": f"Retry {node} after reflection",
        }


class StrategyApplyNode(BaseNode):
    def __init__(self):
        super().__init__("StrategyApplyNode", cost=0.3)
        self._audit_logger = get_audit_logger()

    def execute(self, state: WorkflowState) -> NodeResult:
        strategy = state.get("_retrieved_strategy", "")

        if not strategy:
            return NodeResult(
                status="success", confidence=1.0, retryable=False, updates={}
            )

        state["_strategy_applied"] = True

        modifications = self._apply_strategy(strategy, state)

        self._audit_logger.log_strategy_application(
            state=state, strategy=strategy, success=True
        )

        return NodeResult(
            status="success", confidence=0.9, retryable=False, updates=modifications
        )

    def _apply_strategy(self, strategy: str, state: WorkflowState) -> dict:
        updates = {}

        if "increase_timeout" in strategy.lower():
            state["_timeout_increased"] = True
            updates["_timeout_increased"] = True

        if "reduce_scope" in strategy.lower():
            file_index = state.get("file_index", [])
            state["file_index"] = (
                file_index[: len(file_index) // 2] if file_index else []
            )
            updates["_scope_reduced"] = True

        if "skip_safety" in strategy.lower():
            state["_skip_safety"] = True
            updates["_safety_skipped"] = True

        if "fallback" in strategy.lower():
            state["_fallback_mode"] = True
            updates["_fallback_enabled"] = True

        if "retry_node" in strategy.lower():
            updates["_retry_with_fallback"] = True

        return updates


class RetryNode(BaseNode):
    def __init__(self):
        super().__init__("RetryNode", cost=0.1)
        self._audit_logger = get_audit_logger()

    def execute(self, state: WorkflowState) -> NodeResult:
        retry_node = state.get("_retry_node", "")
        reflection = state.get("_reflection", {})

        applied_strategy = reflection.get("applied_strategy", "")
        if applied_strategy:
            state["_last_strategy"] = applied_strategy

        self._audit_logger.log_node_execution(
            state=state,
            node_name="RetryNode",
            inputs={"retry_node": retry_node, "reflection": reflection},
            outputs={"target": retry_node},
            status="success",
        )

        return NodeResult(
            status="success",
            confidence=0.8,
            retryable=False,
            updates={"_target_node": retry_node, "status": "retrying"},
        )


class RecoverySuccessNode(BaseNode):
    def __init__(self):
        super().__init__("RecoverySuccessNode", cost=0.2)
        self._audit_logger = get_audit_logger()

    def execute(self, state: WorkflowState) -> NodeResult:
        applied_strategy = state.get("_last_strategy", "")

        if applied_strategy:
            from app.memory.failure_memory import FailureMemorySystem

            failure_memory = FailureMemorySystem()
            failure_memory.on_recovery_success(state, applied_strategy)

            self._audit_logger.log_strategy_application(
                state=state, strategy=applied_strategy, success=True
            )

        state["_strategy_applied"] = False
        state["_last_strategy"] = ""

        return NodeResult(status="success", confidence=1.0, retryable=False, updates={})


class CircuitBreakerNode(BaseNode):
    def __init__(self):
        super().__init__("CircuitBreaker", cost=0.1)
        self._audit_logger = get_audit_logger()

    def execute(self, state: WorkflowState) -> NodeResult:
        error_state = state.get("error_state", {})
        reflection_count = state.get("reflection_count", 0)

        from app.memory.failure_memory import FailureMemorySystem

        failure_memory = FailureMemorySystem()
        failure_memory.on_final_failure(state)

        self._audit_logger.log_node_execution(
            state=state,
            node_name="CircuitBreaker",
            inputs={"error_state": error_state, "reflection_count": reflection_count},
            outputs={"status": "failed"},
            status="failure",
        )

        final_error = {
            "error_type": "circuit_breaker_triggered",
            "failed_node": error_state.get("node", "unknown"),
            "total_retries": reflection_count,
            "message": f"Max retries ({MAX_REFLECTION_COUNT}) exceeded",
        }

        return NodeResult(
            status="failure",
            confidence=1.0,
            error_type="circuit_breaker",
            retryable=False,
            updates={"status": "failed", "error_state": final_error, "confidence": 0.0},
        )


class AuditPersistNode(BaseNode):
    def __init__(self):
        super().__init__("AuditPersist", cost=0.5)

    def execute(self, state: WorkflowState) -> NodeResult:
        from app.db.persistence import get_database
        import json

        db = get_database()
        db.update_workflow_state(
            workflow_id=state["workflow_id"],
            state_json=json.dumps(state),
            status=state.get("status", "completed"),
            confidence=state.get("confidence", 0.0),
            current_node=self.node_name,
        )

        return NodeResult(
            status="success",
            confidence=1.0,
            retryable=False,
            updates={"status": "completed"},
        )
