import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
from app.graph.state import WorkflowState
from app.db.persistence import get_database

# Load env vars
from dotenv import load_dotenv

load_dotenv()

# Langfuse LangChain integration
try:
    from langfuse import get_client
    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

    _langfuse_handler = LangfuseCallbackHandler()
    _langfuse_client = get_client()
except Exception:
    _langfuse_handler = None
    _langfuse_client = None

# LangChain GROQ model (for full tracing)
_langchain_model = None
try:
    from langchain_groq import ChatGroq

    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        _langchain_model = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
except Exception:
    pass

PROMPT_VERSION = "v1"


GROQ_PROMPTS = {
    "repo_summary": {
        "version": PROMPT_VERSION,
        "template": """You are analyzing a software repository. Provide a concise summary.

Repository: {repo_name}
Primary Language: {primary_language}
Files: {file_count}
Purpose: {purpose}
Key Features: {features}
Dependencies: {dependencies}
Configuration: {config}

Provide a 2-3 sentence summary of what this repository does and its main purpose.""",
    },
    "ast_reasoning": {
        "version": PROMPT_VERSION,
        "template": """You are analyzing a repository's AST structure.
Repository type: {classification}
File: {filename}
AST excerpt: {ast_excerpt}

Provide a brief analysis of the code structure and dependencies.""",
    },
    "root_cause": {
        "version": PROMPT_VERSION,
        "template": """Analyze the failure to determine root cause.
Failed node: {failed_node}
Error type: {error_type}
Error message: {error_message}
Repository context: {classification}

Provide a root cause hypothesis.""",
    },
    "dependency_explanation": {
        "version": PROMPT_VERSION,
        "template": """Explain the dependency graph.
Dependency graph: {dep_graph}
File: {filename}

Explain how this file depends on others.""",
    },
    "error_analysis": {
        "version": PROMPT_VERSION,
        "template": """Analyze this error for reflection.
Error type: {error_type}
Stack trace: {stack_trace}
Previous strategies attempted: {strategies}

Suggest a recovery strategy.""",
    },
}


class AnalysisAgent:
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None
        self._env_loaded = False

    def _load_env(self):
        if not self._env_loaded:
            try:
                from dotenv import load_dotenv

                load_dotenv()
            except Exception:
                pass
            self._env_loaded = True

    def _get_client(self):
        if self._client is None:
            self._load_env()
            try:
                from groq import Groq

                api_key = os.environ.get("GROQ_API_KEY")
                if api_key:
                    self._client = Groq(api_key=api_key)
            except Exception:
                pass
        return self._client

    def _check_budget(self, state: WorkflowState) -> bool:
        budget = state.get("budget_state", {})
        max_calls = budget.get("max_llm_calls", 10)
        calls_used = budget.get("llm_calls_used", 0)
        return calls_used < max_calls

    def _deduct_budget(self, state: WorkflowState, tokens_used: int) -> None:
        if "budget_state" not in state:
            state["budget_state"] = {}
        state["budget_state"]["llm_calls_used"] = (
            state["budget_state"].get("llm_calls_used", 0) + 1
        )
        state["budget_state"]["tokens_used"] = (
            state["budget_state"].get("tokens_used", 0) + tokens_used
        )

    def _append_audit(
        self,
        state: WorkflowState,
        task_type: str,
        tokens_used: int,
        result: Dict[str, Any],
    ) -> None:
        entry = {
            "node_name": f"AnalysisAgent:{task_type}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success" if result.get("status") == "success" else "failure",
            "confidence": result.get("confidence", 0.0),
            "tokens_used": tokens_used,
            "prompt_version": PROMPT_VERSION,
        }
        if "audit_log" not in state:
            state["audit_log"] = []
        state["audit_log"].append(entry)

        db = get_database()
        db.append_audit_log(
            workflow_id=state["workflow_id"],
            node_name=f"AnalysisAgent:{task_type}",
            status=entry["status"],
            confidence=entry["confidence"],
            details={"tokens_used": tokens_used, "prompt_version": PROMPT_VERSION},
        )

    def run_analysis(
        self, task_type: str, input_data: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        if not self._check_budget(state):
            return {
                "status": "failure",
                "error_type": "budget_exceeded",
                "message": "LLM call budget exceeded",
                "confidence": 0.0,
            }

        prompt_config = GROQ_PROMPTS.get(task_type)
        if not prompt_config:
            return {
                "status": "failure",
                "error_type": "invalid_task_type",
                "message": f"Unknown task type: {task_type}",
                "confidence": 0.0,
            }

        template = prompt_config["template"]
        try:
            prompt = template.format(**input_data)
        except KeyError as e:
            return {
                "status": "failure",
                "error_type": "invalid_input",
                "message": f"Missing required field: {e}",
                "confidence": 0.0,
            }

        client = self._get_client()

        # Try LangChain model first (for full tracing), fall back to direct GROQ
        use_langchain = _langchain_model is not None and _langfuse_handler is not None

        if not client and not use_langchain:
            return {
                "status": "failure",
                "error_type": "client_unavailable",
                "message": "GROQ client not available",
                "confidence": 0.0,
                "fallback": True,
            }

        start_time = time.time()

        try:
            if use_langchain:
                # Use LangChain with Langfuse callback for full tracing
                from langchain_core.messages import HumanMessage

                callbacks = [_langfuse_handler] if _langfuse_handler else []

                response = _langchain_model.invoke(
                    [HumanMessage(content=prompt)], config={"callbacks": callbacks}
                )

                latency_ms = (time.time() - start_time) * 1000
                content = response.content
                # Estimate tokens (LangChain doesn't expose usage from GROQ directly)
                tokens_used = len(content.split()) * 1.3
            else:
                # Fall back to direct GROQ client
                callbacks = [_langfuse_handler] if _langfuse_handler else []

                response = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

                latency_ms = (time.time() - start_time) * 1000

                content = response.choices[0].message.content
                tokens_used = (
                    response.usage.total_tokens
                    if response.usage
                    else len(content.split()) * 1.3
                )

            self._deduct_budget(state, int(tokens_used))

            result = {
                "status": "success",
                "analysis": content,
                "confidence": 0.8,
                "tokens_used": tokens_used,
                "model": self.model,
                "latency_ms": latency_ms,
            }

            # Flush Langfuse to ensure traces are sent
            if _langfuse_client:
                try:
                    _langfuse_client.flush()
                except Exception:
                    pass

            self._append_audit(state, task_type, int(tokens_used), result)

            if "short_term_memory" not in state:
                state["short_term_memory"] = {
                    "analysis_results": {},
                    "conversation_history": [],
                }
            state["short_term_memory"]["analysis_results"][task_type] = content

            return result

        except Exception as e:
            return {
                "status": "failure",
                "error_type": "api_error",
                "message": str(e),
                "confidence": 0.0,
            }


_analysis_agent: Optional[AnalysisAgent] = None


def get_analysis_agent() -> AnalysisAgent:
    global _analysis_agent
    if _analysis_agent is None:
        _analysis_agent = AnalysisAgent()
    return _analysis_agent
