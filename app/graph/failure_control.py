from typing import Dict, Any, Optional
from enum import Enum


class FailureType(str, Enum):
    TRANSIENT = "transient"
    PARSING = "parsing"
    SYSTEMIC = "systemic"
    FATAL = "fatal"


class FailureControl:
    REPEAT_THRESHOLD = 3
    SYSTEMIC_THRESHOLD = 5

    def __init__(self):
        self._error_counts: Dict[str, int] = {}

    def classify_failure(
        self, error_type: str, error_message: str, retry_count: int
    ) -> FailureType:
        error_lower = (error_type + " " + error_message).lower()

        if "timeout" in error_lower or "connection" in error_lower:
            return FailureType.TRANSIENT
        elif "network" in error_lower or "temporary" in error_lower:
            return FailureType.TRANSIENT
        elif (
            "parse" in error_lower
            or "syntax" in error_lower
            or "invalid" in error_lower
        ):
            return FailureType.PARSING
        elif (
            "safety" in error_lower
            or "security" in error_lower
            or "unauthorized" in error_lower
        ):
            return FailureType.FATAL
        elif retry_count >= self.REPEAT_THRESHOLD:
            return FailureType.SYSTEMIC

        return FailureType.TRANSIENT

    def is_repeated_failure(self, error_signature: str) -> bool:
        count = self._error_counts.get(error_signature, 0)
        return count >= self.REPEAT_THRESHOLD

    def record_failure(self, error_signature: str) -> None:
        self._error_counts[error_signature] = (
            self._error_counts.get(error_signature, 0) + 1
        )

    def get_retry_decision(
        self,
        failure_type: FailureType,
        error_signature: str,
        reflection_count: int,
        max_reflections: int = 2,
    ) -> Dict[str, Any]:
        if failure_type == FailureType.FATAL:
            return {
                "action": "circuit_breaker",
                "reason": "fatal_error",
                "retry_allowed": False,
                "backoff": 0,
            }

        if failure_type == FailureType.SYSTEMIC or self.is_repeated_failure(
            error_signature
        ):
            return {
                "action": "circuit_breaker",
                "reason": "repeated_failure",
                "retry_allowed": False,
                "backoff": 0,
            }

        if reflection_count >= max_reflections:
            return {
                "action": "circuit_breaker",
                "reason": "max_reflections_exceeded",
                "retry_allowed": False,
                "backoff": 0,
            }

        if failure_type == FailureType.TRANSIENT:
            backoff = min(2**reflection_count, 30)
            return {
                "action": "retry",
                "reason": "transient_error",
                "retry_allowed": True,
                "backoff": backoff,
            }

        if failure_type == FailureType.PARSING:
            return {
                "action": "reflection",
                "reason": "parsing_error",
                "retry_allowed": True,
                "backoff": 0,
            }

        return {
            "action": "retry",
            "reason": "unknown",
            "retry_allowed": True,
            "backoff": 1,
        }

    def detect_systemic_issue(self, error_signature: str, total_count: int) -> bool:
        return total_count >= self.SYSTEMIC_THRESHOLD

    def reset_error_count(self, error_signature: str) -> None:
        self._error_counts.pop(error_signature, None)


_failure_control: Optional[FailureControl] = None


def get_failure_control() -> FailureControl:
    global _failure_control
    if _failure_control is None:
        _failure_control = FailureControl()
    return _failure_control
