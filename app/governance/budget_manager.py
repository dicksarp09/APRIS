import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.graph.state import WorkflowState


DEFAULT_BUDGET = {
    "max_tokens": 100000,
    "tokens_used": 0,
    "max_llm_calls": 10,
    "llm_calls_used": 0,
    "container_time": 300.0,
    "memory_usage": 0.0,
    "estimated_cost": 0.0,
    "max_cost": 5.0,
    "max_reflections": 2,
}


class BudgetManager:
    def __init__(self):
        self._cost_per_token = 0.0001
        self._cost_per_call = 0.05

    def get_default_budget(self) -> Dict[str, Any]:
        return DEFAULT_BUDGET.copy()

    def initialize_budget(self, state: WorkflowState) -> None:
        if "budget_state" not in state or not state["budget_state"]:
            state["budget_state"] = self.get_default_budget()

    def check_llm_budget(
        self, state: WorkflowState, estimated_tokens: int = 1000
    ) -> Dict[str, Any]:
        budget = state.get("budget_state", self.get_default_budget())

        tokens_used = budget.get("tokens_used", 0)
        max_tokens = budget.get("max_tokens", DEFAULT_BUDGET["max_tokens"])

        llm_calls_used = budget.get("llm_calls_used", 0)
        max_llm_calls = budget.get("max_llm_calls", DEFAULT_BUDGET["max_llm_calls"])

        estimated_cost = budget.get("estimated_cost", 0)
        max_cost = budget.get("max_cost", DEFAULT_BUDGET["max_cost"])

        if llm_calls_used >= max_llm_calls:
            return {
                "allowed": False,
                "reason": "max_llm_calls_exceeded",
                "action": "abort",
            }

        projected_tokens = tokens_used + estimated_tokens
        if projected_tokens > max_tokens:
            remaining_tokens = max_tokens - tokens_used
            if remaining_tokens < 100:
                return {
                    "allowed": False,
                    "reason": "token_limit_exceeded",
                    "action": "abort",
                }
            return {
                "allowed": True,
                "action": "compress_prompt",
                "max_tokens": remaining_tokens,
                "reason": "token_limit_warning",
            }

        projected_cost = (
            estimated_cost
            + (estimated_tokens * self._cost_per_token)
            + self._cost_per_call
        )
        if projected_cost > max_cost:
            return {
                "allowed": False,
                "reason": "cost_limit_exceeded",
                "action": "abort",
            }

        return {
            "allowed": True,
            "action": "proceed",
            "estimated_tokens": estimated_tokens,
        }

    def deduct_llm_cost(self, state: WorkflowState, tokens_used: int) -> None:
        if "budget_state" not in state:
            self.initialize_budget(state)

        state["budget_state"]["tokens_used"] = (
            state["budget_state"].get("tokens_used", 0) + tokens_used
        )
        state["budget_state"]["llm_calls_used"] = (
            state["budget_state"].get("llm_calls_used", 0) + 1
        )

        cost = tokens_used * self._cost_per_token + self._cost_per_call
        state["budget_state"]["estimated_cost"] = (
            state["budget_state"].get("estimated_cost", 0) + cost
        )

    def check_node_budget(
        self, state: WorkflowState, node_cost: float
    ) -> Dict[str, Any]:
        budget = state.get("budget_state", self.get_default_budget())

        total_spent = budget.get("spent", 0)
        total_budget = budget.get("total_budget", 100.0)

        if total_spent + node_cost > total_budget:
            return {"allowed": False, "reason": "budget_exceeded", "action": "abort"}

        return {"allowed": True, "action": "proceed"}

    def deduct_node_cost(
        self, state: WorkflowState, node_name: str, cost: float
    ) -> None:
        if "budget_state" not in state:
            self.initialize_budget(state)

        state["budget_state"]["spent"] = state["budget_state"].get("spent", 0) + cost

        if "node_costs" not in state["budget_state"]:
            state["budget_state"]["node_costs"] = {}
        state["budget_state"]["node_costs"][node_name] = cost

    def check_container_limits(
        self, state: WorkflowState, execution_time: float, memory_peak: float
    ) -> Dict[str, Any]:
        budget = state.get("budget_state", self.get_default_budget())

        max_time = budget.get("container_time", DEFAULT_BUDGET["container_time"])
        if execution_time > max_time:
            return {"allowed": False, "reason": "container_timeout", "action": "abort"}

        max_memory_gb = 1.0
        if memory_peak > max_memory_gb:
            return {"allowed": False, "reason": "memory_exceeded", "action": "abort"}

        return {"allowed": True, "action": "proceed"}

    def check_reflection_limit(self, state: WorkflowState) -> Dict[str, Any]:
        reflection_count = state.get("reflection_count", 0)
        max_reflections = state.get("budget_state", {}).get(
            "max_reflections", DEFAULT_BUDGET["max_reflections"]
        )

        if reflection_count >= max_reflections:
            return {
                "allowed": False,
                "reason": "reflection_limit_exceeded",
                "action": "circuit_breaker",
            }

        return {"allowed": True, "remaining": max_reflections - reflection_count}

    def get_budget_status(self, state: WorkflowState) -> Dict[str, Any]:
        budget = state.get("budget_state", self.get_default_budget())

        return {
            "tokens": {
                "used": budget.get("tokens_used", 0),
                "max": budget.get("max_tokens", DEFAULT_BUDGET["max_tokens"]),
                "remaining": budget.get("max_tokens", DEFAULT_BUDGET["max_tokens"])
                - budget.get("tokens_used", 0),
            },
            "llm_calls": {
                "used": budget.get("llm_calls_used", 0),
                "max": budget.get("max_llm_calls", DEFAULT_BUDGET["max_llm_calls"]),
                "remaining": budget.get(
                    "max_llm_calls", DEFAULT_BUDGET["max_llm_calls"]
                )
                - budget.get("llm_calls_used", 0),
            },
            "cost": {
                "estimated": budget.get("estimated_cost", 0),
                "max": budget.get("max_cost", DEFAULT_BUDGET["max_cost"]),
                "remaining": budget.get("max_cost", DEFAULT_BUDGET["max_cost"])
                - budget.get("estimated_cost", 0),
            },
            "reflections": {
                "used": state.get("reflection_count", 0),
                "max": budget.get("max_reflections", DEFAULT_BUDGET["max_reflections"]),
            },
        }


_budget_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager()
    return _budget_manager
