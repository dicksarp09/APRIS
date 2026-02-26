from typing import Dict, Any, List
from datetime import datetime
from app.graph.state import WorkflowState
from app.db.persistence import get_database

TEMPLATE_VERSION = "v1"


DOCUMENTATION_TEMPLATES = {
    "setup_guide": {
        "version": TEMPLATE_VERSION,
        "template": """# Setup Guide

## Prerequisites
- {prerequisites}

## Installation Steps
1. {step1}
2. {step2}
3. {step3}

## Verification
{verification}
""",
    },
    "architecture_summary": {
        "version": TEMPLATE_VERSION,
        "template": """# Architecture Summary

## Repository Type
{repo_type}

## File Structure
{total_files} files total

## Key Components
{components}

## Dependencies
{dependencies}
""",
    },
    "api_documentation": {
        "version": TEMPLATE_VERSION,
        "template": """# API Documentation

## Overview
{overview}

## Endpoints
{endpoints}

## Data Models
{models}
""",
    },
}


class DocumentationAgent:
    def __init__(self, temperature: float = 0.1):
        self.temperature = temperature

    def _append_audit(
        self, state: WorkflowState, doc_type: str, result: Dict[str, Any]
    ) -> None:
        entry = {
            "node_name": f"DocumentationAgent:{doc_type}",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "confidence": result.get("confidence", 0.0),
            "template_version": TEMPLATE_VERSION,
        }
        if "audit_log" not in state:
            state["audit_log"] = []
        state["audit_log"].append(entry)

        db = get_database()
        db.append_audit_log(
            workflow_id=state["workflow_id"],
            node_name=f"DocumentationAgent:{doc_type}",
            status=entry["status"],
            confidence=entry["confidence"],
            details={"template_version": TEMPLATE_VERSION},
        )

    def generate_setup_guide(
        self,
        state: WorkflowState,
        prerequisites: List[str] = None,
        steps: List[str] = None,
        verification: str = "",
    ) -> str:
        prereqs = prerequisites or ["Python 3.8+", "Git"]
        step_list = steps or ["Clone repository", "Install dependencies", "Run tests"]
        verif = verification or "Run: python -m pytest"

        template = DOCUMENTATION_TEMPLATES["setup_guide"]["template"]
        doc = template.format(
            prerequisites="\n- ".join(prereqs),
            step1=step_list[0] if len(step_list) > 0 else "N/A",
            step2=step_list[1] if len(step_list) > 1 else "N/A",
            step3=step_list[2] if len(step_list) > 2 else "N/A",
            verification=verif,
        )

        self._append_audit(
            state, "setup_guide", {"status": "success", "confidence": 0.9}
        )
        return doc

    def generate_architecture_summary(
        self,
        state: WorkflowState,
        repo_type: str = "",
        components: List[str] = None,
        dependencies: Dict[str, Any] = None,
    ) -> str:
        classification = state.get("classification", repo_type or "unknown")
        file_index = state.get("file_index", [])
        dep_graph = state.get("dependency_graph", dependencies or {})

        comps = components or self._extract_components(dep_graph)

        template = DOCUMENTATION_TEMPLATES["architecture_summary"]["template"]
        doc = template.format(
            repo_type=classification,
            total_files=len(file_index),
            components="\n".join([f"- {c}" for c in comps[:10]]),
            dependencies=str(dep_graph)[:500],
        )

        self._append_audit(
            state, "architecture_summary", {"status": "success", "confidence": 0.85}
        )
        return doc

    def generate_api_documentation(
        self,
        state: WorkflowState,
        overview: str = "",
        endpoints: List[Dict[str, str]] = None,
        models: List[Dict[str, str]] = None,
    ) -> str:
        classification = state.get("classification", "unknown")
        file_index = state.get("file_index", [])

        overview_text = overview or f"API documentation for {classification} repository"

        eps = endpoints or [
            {"path": "/", "method": "GET", "description": "Root endpoint"}
        ]
        endpoint_str = "\n".join(
            [f"- {e['method']} {e['path']}: {e['description']}" for e in eps]
        )

        mdl = models or [{"name": "GenericModel", "fields": "N/A"}]
        model_str = "\n".join([f"- {m['name']}: {m['fields']}" for m in mdl])

        template = DOCUMENTATION_TEMPLATES["api_documentation"]["template"]
        doc = template.format(
            overview=overview_text, endpoints=endpoint_str, models=model_str
        )

        self._append_audit(
            state, "api_documentation", {"status": "success", "confidence": 0.85}
        )
        return doc

    def _extract_components(self, dep_graph: Dict[str, Any]) -> List[str]:
        modules = dep_graph.get("modules", {})
        if modules:
            return list(modules.keys())
        nodes = dep_graph.get("nodes", [])
        return [n.get("file", "unknown") for n in nodes[:10]]


_documentation_agent: DocumentationAgent = None


def get_documentation_agent() -> DocumentationAgent:
    global _documentation_agent
    if _documentation_agent is None:
        _documentation_agent = DocumentationAgent()
    return _documentation_agent
