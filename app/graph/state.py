from typing import TypedDict, Dict, List, Any, Optional
from datetime import datetime


class WorkflowState(TypedDict):
    workflow_id: str
    repo_url: str
    repo_metadata: Dict[str, Any]
    classification: str
    file_index: List[str]
    summaries: Dict[str, str]
    dependency_graph: Dict[str, Any]
    architecture_summary: str
    documentation: str
    audit_log: List[Dict[str, Any]]
    error_state: Dict[str, Any]
    budget_state: Dict[str, Any]
    reflection_count: int
    confidence: float
    status: str
    user_id: str
    mode: str
    file_contents: Dict[str, str]
    project_description: Dict[str, Any]
    file_summaries: Dict[str, Any]
    dependencies: Dict[str, Any]
    config_info: Dict[str, Any]
    primary_language: str

    # Analysis configuration
    analysis_mode: str  # "deep" or "shallow"
    max_files_analyze: int  # Maximum files to analyze in deep mode
    repository_provider: str  # "github_mcp" or "local"

    short_term_memory: Dict[str, Any]
    failure_context: Dict[str, Any]
    applied_strategies: List[str]

    _routing: Optional[str]
    _next_node: Optional[str]
    _target_node: Optional[str]
    _retry_node: Optional[str]
    _reflection: Optional[Dict[str, Any]]
    _strategy_found: bool
    _retrieved_strategy: Optional[str]
    _strategy_confidence: float
    _strategy_applied: bool
    _last_strategy: Optional[str]
    _require_approval: bool
    _timeout_increased: bool
    _scope_reduced: bool
    _skip_safety: bool
    _fallback_mode: bool
    _retry_with_fallback: bool


def create_initial_state(workflow_id: str, repo_url: str) -> WorkflowState:
    now = datetime.utcnow().isoformat()
    return {
        "workflow_id": workflow_id,
        "repo_url": repo_url,
        "repo_metadata": {},
        "classification": "",
        "file_index": [],
        "summaries": {},
        "dependency_graph": {},
        "architecture_summary": "",
        "documentation": "",
        "audit_log": [],
        "error_state": {},
        "budget_state": {
            "total_budget": 100.0,
            "spent": 0.0,
            "node_costs": {},
            "max_tokens": 100000,
            "tokens_used": 0,
            "max_llm_calls": 10,
            "llm_calls_used": 0,
            "max_reflections": 2,
        },
        "reflection_count": 0,
        "confidence": 0.0,
        "status": "pending",
        "user_id": "",
        "mode": "deterministic",
        "file_contents": {},
        "project_description": {},
        "file_summaries": {},
        "dependencies": {},
        "config_info": {},
        "primary_language": "",
        "analysis_mode": "shallow",  # "deep" or "shallow" - deep = analyze all files, shallow = metadata only
        "max_files_analyze": 50,  # Maximum files to analyze in deep mode
        "repository_provider": "github_mcp",  # "github_mcp" or "local"
        "short_term_memory": {
            "conversation_history": [],
            "analysis_results": {},
            "key_findings": [],
            "context_stack": [],
        },
        "failure_context": {
            "error_signatures": [],
            "failed_steps": [],
            "retry_history": [],
        },
        "applied_strategies": [],
        "_routing": None,
        "_next_node": None,
        "_target_node": None,
        "_retry_node": None,
        "_reflection": None,
        "_strategy_found": False,
        "_retrieved_strategy": None,
        "_strategy_confidence": 0.0,
        "_strategy_applied": False,
        "_last_strategy": None,
        "_require_approval": False,
        "_timeout_increased": False,
        "_scope_reduced": False,
        "_skip_safety": False,
        "_fallback_mode": False,
        "_retry_with_fallback": False,
    }


def create_initial_state_from_dict(data: Dict[str, Any]) -> WorkflowState:
    defaults = create_initial_state(
        data.get("workflow_id", ""), data.get("repo_url", "")
    )
    for key, value in data.items():
        if key in defaults:
            defaults[key] = value
    return defaults
