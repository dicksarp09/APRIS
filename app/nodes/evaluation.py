from typing import Dict, Any, List
from app.nodes.base import BaseNode, NodeResult
from app.graph.state import WorkflowState
from app.memory.chroma_store import get_chroma_store


class EvaluationNode(BaseNode):
    def __init__(self):
        super().__init__("EvaluationNode", cost=0.5)
        self._chroma = get_chroma_store()

    def execute(self, state: WorkflowState) -> NodeResult:
        learning_record = self._create_learning_record(state)

        self._store_learning_record(learning_record)

        outcome_quality = self._calculate_outcome_quality(state)

        return NodeResult(
            status="success",
            confidence=outcome_quality,
            retryable=False,
            updates={
                "_evaluation_complete": True,
                "outcome_quality": outcome_quality,
                "learning_record": learning_record,
            },
        )

    def _create_learning_record(self, state: WorkflowState) -> Dict[str, Any]:
        repo_class = state.get("classification", "unknown")

        strategies_used = []
        applied_strategies = state.get("applied_strategies", [])
        if isinstance(applied_strategies, list):
            for s in applied_strategies:
                if isinstance(s, dict):
                    strategies_used.append(s.get("strategy", ""))
                elif isinstance(s, str):
                    strategies_used.append(s)

        budget = state.get("budget_state", {})
        cost = budget.get("estimated_cost", 0.0)

        failure_context = state.get("failure_context", {})
        failure_patterns = []
        for sig in failure_context.get("error_signatures", []):
            if isinstance(sig, dict):
                failure_patterns.append(sig.get("failure_class", "unknown"))
            else:
                failure_patterns.append(str(sig))

        reflection_triggered = state.get("reflection_count", 0) > 0

        confidence_delta = state.get("confidence", 0.0) - 0.0

        return {
            "repo_class": repo_class,
            "strategies_used": strategies_used,
            "cost": cost,
            "failure_patterns": failure_patterns,
            "outcome_quality": 0.0,
            "reflection_triggered": reflection_triggered,
            "reflection_count": state.get("reflection_count", 0),
            "confidence_delta": confidence_delta,
            "workflow_id": state.get("workflow_id", ""),
            "status": state.get("status", "unknown"),
        }

    def _store_learning_record(self, record: Dict[str, Any]) -> None:
        repo_class = record.get("repo_class", "unknown")
        strategies = record.get("strategies_used", [])
        cost = record.get("cost", 0.0)

        pattern_text = f"Repository class: {repo_class}, Strategies: {', '.join(strategies)}, Cost: {cost}"

        self._chroma.store_repo_pattern(
            repo_type=repo_class,
            language=repo_class,
            size_bucket=self._categorize_size(cost),
            pattern_text=pattern_text,
            metadata={
                "learning_record": True,
                "strategies_count": len(strategies),
                "cost_bucket": self._categorize_cost(cost),
                "reflection_triggered": record.get("reflection_triggered", False),
            },
        )

    def _calculate_outcome_quality(self, state: WorkflowState) -> float:
        status = state.get("status", "unknown")

        if status == "completed":
            base_score = 1.0
        elif status == "failed":
            base_score = 0.0
        else:
            base_score = 0.5

        confidence = state.get("confidence", 0.0)

        reflection_count = state.get("reflection_count", 0)
        reflection_penalty = reflection_count * 0.1

        quality = (base_score * 0.6) + (confidence * 0.4) - reflection_penalty

        return max(0.0, min(1.0, quality))

    def _categorize_size(self, cost: float) -> str:
        if cost < 1.0:
            return "small"
        elif cost < 3.0:
            return "medium"
        else:
            return "large"

    def _categorize_cost(self, cost: float) -> str:
        if cost < 0.5:
            return "low"
        elif cost < 2.0:
            return "medium"
        else:
            return "high"


class PauseDecisionNode(BaseNode):
    def __init__(self, thresholds: Dict[str, Any] = None):
        super().__init__("PauseDecisionNode", cost=0.1)
        self._thresholds = thresholds or {
            "max_repo_size_mb": 100,
            "min_confidence": 0.6,
            "max_budget_estimate": 5.0,
            "high_risk_score": 0.7,
        }

    def execute(self, state: WorkflowState) -> NodeResult:
        should_pause = self._check_pause_conditions(state)

        if should_pause:
            pause_info = self._create_pause_info(state)
            return NodeResult(
                status="success",
                confidence=1.0,
                retryable=False,
                updates={
                    "_should_pause": True,
                    "_pause_reason": pause_info["reasons"],
                    "status": "awaiting_approval",
                    "_pause_info": pause_info,
                },
            )

        return NodeResult(
            status="success",
            confidence=1.0,
            retryable=False,
            updates={"_should_pause": False, "status": "in_progress"},
        )

    def _check_pause_conditions(self, state: WorkflowState) -> bool:
        repo_metadata = state.get("repo_metadata", {})
        repo_size_mb = repo_metadata.get("total_size", 0) / (1024 * 1024)

        if repo_size_mb > self._thresholds.get("max_repo_size_mb", 100):
            return True

        confidence = state.get("confidence", 0.0)
        if confidence < self._thresholds.get("min_confidence", 0.6):
            return True

        budget = state.get("budget_state", {})
        estimated_cost = budget.get("estimated_cost", 0.0)
        if estimated_cost > self._thresholds.get("max_budget_estimate", 5.0):
            return True

        risk_score = self._calculate_risk_score(state)
        if risk_score > self._thresholds.get("high_risk_score", 0.7):
            return True

        return False

    def _calculate_risk_score(self, state: WorkflowState) -> float:
        score = 0.0

        repo_metadata = state.get("repo_metadata", {})
        if repo_metadata.get("safety_passed", True) is False:
            score += 0.3

        classification = state.get("classification", "")
        if classification in ["unknown", "mixed"]:
            score += 0.2

        file_count = len(state.get("file_index", []))
        if file_count > 1000:
            score += 0.3
        elif file_count > 500:
            score += 0.1

        return min(1.0, score)

    def _create_pause_info(self, state: WorkflowState) -> Dict[str, Any]:
        reasons = []

        repo_metadata = state.get("repo_metadata", {})
        repo_size_mb = repo_metadata.get("total_size", 0) / (1024 * 1024)
        if repo_size_mb > self._thresholds.get("max_repo_size_mb", 100):
            reasons.append(f"Repo size {repo_size_mb:.1f}MB exceeds threshold")

        confidence = state.get("confidence", 0.0)
        if confidence < self._thresholds.get("min_confidence", 0.6):
            reasons.append(f"Confidence {confidence:.2f} below threshold")

        budget = state.get("budget_state", {})
        estimated_cost = budget.get("estimated_cost", 0.0)
        if estimated_cost > self._thresholds.get("max_budget_estimate", 5.0):
            reasons.append(f"Estimated cost ${estimated_cost:.2f} exceeds threshold")

        risk_score = self._calculate_risk_score(state)
        if risk_score > self._thresholds.get("high_risk_score", 0.7):
            reasons.append(f"Risk score {risk_score:.2f} is high")

        return {
            "reasons": reasons,
            "risk_score": risk_score,
            "estimated_cost": estimated_cost,
            "confidence": confidence,
            "reflection_count": state.get("reflection_count", 0),
        }
