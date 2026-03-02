import json
from typing import Dict, Any, Optional, Callable
from langgraph.graph import StateGraph, END
from app.graph.state import WorkflowState, create_initial_state
from app.nodes.workflow_nodes import (
    CloneRepoNode,
    ProfileRepoNode,
    ClassifyRepoNode,
    SafetyScanNode,
    ParseFilesNode,
    SummarizeFilesNode,
    ContentAnalysisNode,
    BuildDependencyGraphNode,
    ArchitectureSynthesisNode,
    DocumentationGenerationNode,
)
from app.nodes.failure_handling import (
    FailureRouterNode,
    ReflectionNode,
    RetryNode,
    CircuitBreakerNode,
    AuditPersistNode,
)
from app.security.database import get_database


class WorkflowEngine:
    def __init__(self):
        self.graph: Optional[StateGraph] = None
        self.nodes: Dict[str, Callable] = {}
        self._build_static_graph()

    def _build_static_graph(self):
        clone_repo = CloneRepoNode()
        profile_repo = ProfileRepoNode()
        classify_repo = ClassifyRepoNode()
        safety_scan = SafetyScanNode()
        parse_files = ParseFilesNode()
        summarize_files = SummarizeFilesNode()
        content_analysis = ContentAnalysisNode()
        build_dep_graph = BuildDependencyGraphNode()
        arch_synthesis = ArchitectureSynthesisNode()
        doc_generation = DocumentationGenerationNode()
        audit_persist = AuditPersistNode()

        failure_router = FailureRouterNode()
        reflection_node = ReflectionNode()
        retry_node = RetryNode()
        circuit_breaker = CircuitBreakerNode()

        self.nodes = {
            "CloneRepo": clone_repo.run,
            "ProfileRepo": profile_repo.run,
            "ClassifyRepo": classify_repo.run,
            "SafetyScan": safety_scan.run,
            "ParseFiles": parse_files.run,
            "SummarizeFiles": summarize_files.run,
            "ContentAnalysis": content_analysis.run,
            "BuildDependencyGraph": build_dep_graph.run,
            "ArchitectureSynthesis": arch_synthesis.run,
            "DocumentationGeneration": doc_generation.run,
            "AuditPersist": audit_persist.run,
            "FailureRouter": failure_router.run,
            "ReflectionNode": reflection_node.run,
            "RetryNode": retry_node.run,
            "CircuitBreaker": circuit_breaker.run,
        }

        workflow = StateGraph(WorkflowState)

        workflow.add_node("CloneRepo", self._wrap_node("CloneRepo"))
        workflow.add_node("ProfileRepo", self._wrap_node("ProfileRepo"))
        workflow.add_node("ClassifyRepo", self._wrap_node("ClassifyRepo"))
        workflow.add_node("SafetyScan", self._wrap_node("SafetyScan"))
        workflow.add_node("ParseFiles", self._wrap_node("ParseFiles"))
        workflow.add_node("SummarizeFiles", self._wrap_node("SummarizeFiles"))
        workflow.add_node("ContentAnalysis", self._wrap_node("ContentAnalysis"))
        workflow.add_node(
            "BuildDependencyGraph", self._wrap_node("BuildDependencyGraph")
        )
        workflow.add_node(
            "ArchitectureSynthesis", self._wrap_node("ArchitectureSynthesis")
        )
        workflow.add_node(
            "DocumentationGeneration", self._wrap_node("DocumentationGeneration")
        )
        workflow.add_node("AuditPersist", self._wrap_node("AuditPersist"))
        workflow.add_node("FailureRouter", self._wrap_failure_router)
        workflow.add_node("ReflectionNode", self._wrap_reflection)
        workflow.add_node("RetryNode", self._wrap_retry)
        workflow.add_node("CircuitBreaker", self._wrap_circuit_breaker)

        workflow.set_entry_point("CloneRepo")

        workflow.add_edge("CloneRepo", "ProfileRepo")
        workflow.add_edge("ProfileRepo", "ClassifyRepo")
        workflow.add_edge("ClassifyRepo", "SafetyScan")
        workflow.add_edge("SafetyScan", "ParseFiles")
        workflow.add_edge("ParseFiles", "SummarizeFiles")
        workflow.add_edge("SummarizeFiles", "ContentAnalysis")
        workflow.add_edge("ContentAnalysis", "BuildDependencyGraph")
        workflow.add_edge("BuildDependencyGraph", "ArchitectureSynthesis")
        workflow.add_edge("ArchitectureSynthesis", "DocumentationGeneration")
        workflow.add_edge("DocumentationGeneration", "AuditPersist")
        workflow.add_edge("AuditPersist", END)

        self.graph = workflow.compile()

    def _wrap_node(self, node_name: str):
        def wrapper(state: WorkflowState) -> WorkflowState:
            node_func = self.nodes.get(node_name)
            if node_func:
                return node_func(state)
            return state

        return wrapper

    def _wrap_failure_router(self, state: WorkflowState) -> WorkflowState:
        result = FailureRouterNode().run(state)
        routing = result.updates.get("_routing", "continue")
        state.update(result.updates)
        if routing == "circuit_breaker":
            state["_next_node"] = "CircuitBreaker"
        elif routing == "retry":
            state["_next_node"] = "ReflectionNode"
        else:
            state["_next_node"] = None
        return state

    def _wrap_reflection(self, state: WorkflowState) -> WorkflowState:
        result = ReflectionNode().run(state)
        state.update(result.updates)
        state["_next_node"] = state.get("_retry_node", "RetryNode")
        return state

    def _wrap_retry(self, state: WorkflowState) -> WorkflowState:
        target = state.get("_target_node", "CloneRepo")
        state["_next_node"] = target
        state["status"] = "retrying"
        return state

    def _wrap_circuit_breaker(self, state: WorkflowState) -> WorkflowState:
        result = CircuitBreakerNode().run(state)
        state.update(result.updates)
        return state

    def run_workflow(self, workflow_id: str, repo_url: str) -> WorkflowState:
        db = get_database()
        workflow_data = db.get_workflow_state(workflow_id)

        if workflow_data:
            initial_state = json.loads(workflow_data.get("state_json", "{}"))
        else:
            initial_state = create_initial_state(workflow_id, repo_url)
            db.create_workflow(
                workflow_id=workflow_id,
                repo_url=repo_url,
                state_json=json.dumps(initial_state),
            )

        result = self.graph.invoke(initial_state)
        return result

    def resume_workflow(self, workflow_id: str) -> WorkflowState:
        db = get_database()
        workflow_data = db.get_workflow_state(workflow_id)

        if not workflow_data:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow_data["status"] in ("completed", "failed"):
            return json.loads(workflow_data["state_json"])

        current_state = json.loads(workflow_data["state_json"])
        result = self.graph.invoke(current_state)
        return result

    def get_workflow_status(self, workflow_id: str) -> str:
        db = get_database()
        return db.get_workflow_status(workflow_id) or "not_found"


_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
