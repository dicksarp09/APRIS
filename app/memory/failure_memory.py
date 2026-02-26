import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.memory.chroma_store import get_chroma_store


SIMILARITY_THRESHOLD = 0.85


def _compute_stack_hash(stack_trace: str) -> str:
    return hashlib.sha256(stack_trace.encode()).hexdigest()[:16]


def _classify_error(error_type: str, error_message: str) -> str:
    error_lower = (error_type + " " + error_message).lower()
    if "timeout" in error_lower:
        return "timeout"
    elif "memory" in error_lower or "oom" in error_lower:
        return "memory"
    elif "clone" in error_lower or "git" in error_lower:
        return "git_error"
    elif "parse" in error_lower or "syntax" in error_lower:
        return "parse_error"
    elif "network" in error_lower or "connection" in error_lower:
        return "network"
    elif "auth" in error_lower or "permission" in error_lower:
        return "auth"
    elif "safety" in error_lower or "security" in error_lower:
        return "safety"
    return "unknown"


def extract_failure_signature(
    failed_node: str,
    error_type: str,
    error_message: str,
    stack_trace: Optional[str] = None,
) -> Dict[str, Any]:
    stack_hash = (
        _compute_stack_hash(stack_trace or error_message) if stack_trace else ""
    )
    failure_class = _classify_error(error_type, error_message)

    return {
        "error_signature": f"{failed_node}:{error_type}:{failure_class}",
        "failed_step": failed_node,
        "error_type": error_type,
        "error_message": error_message,
        "failure_class": failure_class,
        "stack_trace_hash": stack_hash,
        "timestamp": datetime.utcnow().isoformat(),
    }


def query_failure_memory(
    error_signature: str, threshold: float = SIMILARITY_THRESHOLD
) -> Optional[Dict[str, Any]]:
    chroma = get_chroma_store()
    matches = chroma.query_failure_memory(error_signature, threshold=threshold)

    if matches:
        return {
            "strategy": matches[0].get("metadata", {}).get("strategy", ""),
            "confidence": matches[0].get("confidence", 0),
            "match_id": matches[0].get("id", ""),
            "metadata": matches[0].get("metadata", {}),
        }
    return None


def store_successful_strategy(
    error_signature: str, strategy: str, repo_type: str, language: str, failed_step: str
) -> str:
    chroma = get_chroma_store()
    failure_class = _classify_error("", error_signature)
    return chroma.store_successful_strategy(
        error_signature=error_signature,
        strategy=strategy,
        repo_type=repo_type,
        language=language,
        failure_class=failure_class,
        metadata={"failed_step": failed_step, "recovery_successful": True},
    )


def store_failure_permanently(
    error_signature: str,
    failed_step: str,
    repo_type: str,
    language: str,
    stack_trace: Optional[str] = None,
) -> str:
    chroma = get_chroma_store()
    stack_hash = _compute_stack_hash(stack_trace or error_signature)
    failure_class = _classify_error("", error_signature)
    return chroma.store_failure_memory(
        error_signature=error_signature,
        failed_step=failed_step,
        repo_type=repo_type,
        language=language,
        failure_class=failure_class,
        stack_trace_hash=stack_hash,
    )


class FailureMemorySystem:
    def __init__(self, threshold: float = SIMILARITY_THRESHOLD):
        self.threshold = threshold

    def process_failure(self, state: Dict[str, Any]) -> Dict[str, Any]:
        error_state = state.get("error_state", {})
        failed_node = error_state.get("node", "unknown")
        error_type = error_state.get("error_type", "unknown")
        error_message = error_state.get("message", "")

        signature = extract_failure_signature(
            failed_node=failed_node,
            error_type=error_type,
            error_message=error_message,
            stack_trace=error_state.get("stack_trace"),
        )

        if "failure_context" not in state:
            state["failure_context"] = {
                "error_signatures": [],
                "failed_steps": [],
                "retry_history": [],
            }

        state["failure_context"]["error_signatures"].append(signature)
        state["failure_context"]["failed_steps"].append(failed_node)

        match = query_failure_memory(signature["error_signature"], self.threshold)

        if match:
            state["_strategy_found"] = True
            state["_retrieved_strategy"] = match["strategy"]
            state["_strategy_confidence"] = match["confidence"]
        else:
            state["_strategy_found"] = False

        return state

    def on_recovery_success(self, state: Dict[str, Any], applied_strategy: str) -> None:
        if not state.get("_strategy_found"):
            return

        repo_type = state.get("classification", "unknown")
        language = state.get("classification", "unknown")
        failed_node = state.get("error_state", {}).get("node", "unknown")
        error_sig = state.get("failure_context", {}).get("error_signatures", [])

        if error_sig:
            last_sig = error_sig[-1].get("error_signature", "")
            store_successful_strategy(
                error_signature=last_sig,
                strategy=applied_strategy,
                repo_type=repo_type,
                language=language,
                failed_step=failed_node,
            )

    def on_final_failure(self, state: Dict[str, Any]) -> None:
        repo_type = state.get("classification", "unknown")
        language = state.get("classification", "unknown")
        error_state = state.get("error_state", {})
        failed_node = error_state.get("node", "unknown")

        error_sigs = state.get("failure_context", {}).get("error_signatures", [])
        if error_sigs:
            last_sig = error_sigs[-1]
            store_failure_permanently(
                error_signature=last_sig.get("error_signature", ""),
                failed_step=failed_node,
                repo_type=repo_type,
                language=language,
                stack_trace=error_state.get("stack_trace"),
            )
