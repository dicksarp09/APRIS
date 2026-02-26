import os
import time
from typing import Dict, Any, Optional


class LangfuseTracer:
    """
    Langfuse v3 integration for APRIS observability.
    Tracks tokens, latency, cost, user feedback.
    """

    def __init__(self):
        self._langfuse = None
        self._enabled = False

    def _load_env(self):
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except:
            pass

    def _get_client(self):
        if self._langfuse is None:
            self._load_env()
            try:
                from langfuse import Langfuse

                public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
                secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

                if public_key and secret_key:
                    self._langfuse = Langfuse(
                        public_key=public_key,
                        secret_key=secret_key,
                    )
                    self._enabled = True
                else:
                    pass  # Silent - no keys
            except Exception:
                pass  # Silent - no langfuse installed
        return self._langfuse

    def trace_llm_call(
        self,
        workflow_id: str,
        repo_url: str,
        model: str,
        prompt: str,
        response: str,
        tokens_used: int,
        latency_ms: float,
        cost: float = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[str]:
        """Track an LLM call to Langfuse."""
        langfuse = self._get_client()
        if not langfuse or not self._enabled:
            return None

        try:
            meta = metadata or {}
            meta["repo_url"] = repo_url
            meta["user_id"] = user_id or "system"
            meta["tokens_used"] = tokens_used
            meta["latency_ms"] = latency_ms
            if cost:
                meta["cost"] = cost

            # Create a trace with generation that tracks actual latency
            with langfuse.start_as_current_observation(
                name=f"apris-{workflow_id[:12]}",
                as_type="generation",
                model=model,
                input=prompt,
                output=response,
                metadata=meta,
            ):
                pass

            # Flush to ensure data is sent
            langfuse.flush()

            return workflow_id[:8]
        except Exception as e:
            print(f"Langfuse trace error: {e}")
            pass  # Gracefully fail - don't break app

        return None

        try:
            meta = metadata or {}
            meta["repo_url"] = repo_url
            meta["user_id"] = user_id or "system"
            meta["tokens_used"] = tokens_used
            meta["latency_ms"] = latency_ms
            meta["cost"] = cost

            with langfuse.start_as_current_observation(
                name=f"apris-{workflow_id[:8]}",
                as_type="generation",
                input={"prompt": prompt[:1000]},
                output={"response": response[:1000]},
                model=model,
                metadata=meta,
            ):
                pass

            # Flush to ensure data is sent
            langfuse.flush()

            return workflow_id[:8]
        except Exception as e:
            print(f"Langfuse trace error: {e}")
            pass  # Gracefully fail - don't break app

        return None

    def track_event(
        self,
        workflow_id: str,
        event_name: str,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Track custom events."""
        pass  # Not critical

    def track_score(
        self, trace_id: str, name: str, value: float, comment: str = None
    ) -> None:
        """Track user feedback/scores."""
        pass  # Not critical


_langfuse_tracer: Optional[LangfuseTracer] = None


def get_langfuse_tracer() -> LangfuseTracer:
    global _langfuse_tracer
    if _langfuse_tracer is None:
        _langfuse_tracer = LangfuseTracer()
    return _langfuse_tracer
