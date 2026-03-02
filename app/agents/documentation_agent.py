from typing import Dict, Any, List, Optional
from datetime import datetime
from app.graph.state import WorkflowState
from app.db.persistence import get_database
import json

TEMPLATE_VERSION = "v2"


class DocumentationAgent:
    def __init__(self, temperature: float = 0.7):
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

    def _truncate_smart(
        self,
        text: str,
        max_length: int = 2000,
        min_remaining: int = 100,
        respect_sentences: bool = True,
    ) -> str:
        """Smart truncation that respects word and sentence boundaries."""
        if len(text) <= max_length:
            return text

        # Leave buffer for ellipsis and continuation
        truncated_at = max_length - min_remaining - 3

        if respect_sentences:
            # Find the last sentence boundary (period, question mark, exclamation)
            last_period = max(
                text.rfind(". "),
                text.rfind(".\n"),
                text.rfind("? "),
                text.rfind("!\n"),
                text.rfind(".\r"),
            )

            # If last sentence fits within our limit, include it
            if (
                last_period > truncated_at - 50
                and last_period < max_length - min_remaining
            ):
                return text[: last_period + 1]

        # Fall back to word boundary
        last_space = text[:truncated_at].rfind(" ")
        if last_space > truncated_at - 100:
            truncated_at = last_space

        return text[:truncated_at] + "..."

    def _generate_natural_list(
        self, items: List[str], max_items: int = 8, connector: str = "and"
    ) -> str:
        """Generate natural language list with proper punctuation."""
        if not items:
            return "No items found"

        # Filter and limit items
        filtered = [str(item).strip() for item in items if item][:max_items]

        if len(filtered) == 1:
            return filtered[0]
        elif len(filtered) == 2:
            return f"{filtered[0]} {connector} {filtered[1]}"
        elif len(filtered) <= 4:
            return ", ".join(filtered[:-1]) + f", {connector} {filtered[-1]}"
        else:
            remaining = len(filtered) - 3
            return ", ".join(filtered[:3]) + f", and {remaining} more"

    def _extract_file_types(self, file_index: List[str]) -> Dict[str, int]:
        """Extract file type distribution from file index."""
        extensions = {}
        for f in file_index:
            if "." in f:
                ext = f.rsplit(".", 1)[-1]
                extensions[ext] = extensions.get(ext, 0) + 1
            else:
                extensions["no_ext"] = extensions.get("no_ext", 0) + 1
        return extensions

    def _generate_project_description(self, state: WorkflowState) -> str:
        """Generate a natural language project description."""
        project_desc = state.get("project_description", {})

        # Try to get LLM summary first
        llm_summary = project_desc.get("llm_summary", "")
        if llm_summary:
            return self._truncate_smart(llm_summary, max_length=500)

        # Fall back to generating from metadata
        classification = state.get("classification", "unknown")
        primary_lang = state.get("primary_language", "")
        file_count = len(state.get("file_index", []))

        file_types = self._extract_file_types(state.get("file_index", []))
        top_languages = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:3]
        lang_str = ", ".join([f"{ext} ({count})" for ext, count in top_languages])

        description = f"This is a {classification}"
        if primary_lang:
            description += f" written primarily in {primary_lang}"
        description += f" containing {file_count} files"
        if lang_str:
            description += f" ({lang_str})"

        # Add component info if available
        file_summaries = state.get("file_summaries", {})
        if file_summaries:
            top_components = list(file_summaries.keys())[:3]
            if top_components:
                comp_str = self._generate_natural_list(top_components)
                description += f". The main components include {comp_str}"

        return description

    def generate_setup_guide(
        self,
        state: WorkflowState,
        prerequisites: Optional[List[str]] = None,
        steps: Optional[List[str]] = None,
        verification: str = "",
    ) -> str:
        # Analyze the project to generate relevant prerequisites and steps
        classification = state.get("classification", "")
        primary_lang = state.get("primary_language", "")
        dependencies = state.get("dependencies", {})
        config_info = state.get("config_info", {})

        # Generate dynamic prerequisites based on project type
        prereqs: List[str] = []
        if prerequisites is None:
            prereqs = []

            if primary_lang:
                if primary_lang.lower() in ["python", "py"]:
                    prereqs.append("Python 3.8 or higher installed")
                    if dependencies.get("python"):
                        prereqs.append(
                            f"Python packages: {self._generate_natural_list(dependencies['python'][:5])}"
                        )
                elif primary_lang.lower() in ["javascript", "js", "typescript", "ts"]:
                    prereqs.append("Node.js 18+ and npm installed")
                    if dependencies.get("javascript"):
                        prereqs.append(
                            f"Dependencies: {self._generate_natural_list(dependencies['javascript'][:5])}"
                        )
                elif primary_lang.lower() in ["java"]:
                    prereqs.append("Java Development Kit (JDK) 11+")
                elif primary_lang.lower() in ["go"]:
                    prereqs.append("Go 1.18+ installed")
                elif primary_lang.lower() in ["rust"]:
                    prereqs.append("Rust toolchain installed")

            prereqs.append("Git for version control")

            # Check for specific config files
            if config_info.get("docker"):
                prereqs.append("Docker and Docker Compose (for containerization)")
            if config_info.get("database"):
                prereqs.append("Database server (PostgreSQL, MySQL, or as specified)")

        # Generate dynamic steps
        step_list: List[str] = []
        if steps is None:
            step_list = []

            # Clone step
            repo_url = state.get("repo_url", "")
            if repo_url:
                step_list.append(f"Clone the repository: `git clone {repo_url}`")

            # Install step based on language
            if primary_lang.lower() in ["python", "py"]:
                step_list.append("Create a virtual environment and activate it")
                if "requirements.txt" in str(config_info.get("files", [])):
                    step_list.append(
                        "Install dependencies: `pip install -r requirements.txt`"
                    )
                elif "pyproject.toml" in str(config_info.get("files", [])):
                    step_list.append(
                        "Install dependencies: `pip install -e .` or `poetry install`"
                    )
                else:
                    step_list.append("Install required Python packages")
            elif primary_lang.lower() in ["javascript", "js", "typescript", "ts"]:
                if "package.json" in str(config_info.get("files", [])):
                    step_list.append("Install dependencies: `npm install`")
                step_list.append("Build the project if needed: `npm run build`")
            elif primary_lang.lower() in ["java"]:
                step_list.append(
                    "Build with Maven/Gradle: `./mvnw install` or `./gradlew build`"
                )
            elif primary_lang.lower() in ["go"]:
                step_list.append(
                    "Download dependencies: `go mod download` and build: `go build`"
                )
            elif primary_lang.lower() in ["rust"]:
                step_list.append("Build the project: `cargo build --release`")

            # Run step
            step_list.append("Start the application following the instructions below")

        # Generate verification command
        if not verification:
            if primary_lang.lower() in ["python", "py"]:
                if "pytest" in str(config_info.get("files", [])):
                    verification = "Run tests with: `pytest` or `python -m pytest`"
                elif "main.py" in str(state.get("file_index", [])):
                    verification = "Run the main application: `python main.py`"
            elif primary_lang.lower() in ["javascript", "js", "typescript", "ts"]:
                verification = "Start the development server: `npm run dev`"
            elif primary_lang.lower() in ["java"]:
                verification = "Run the application: `java -jar target/*.jar`"
            elif primary_lang.lower() in ["go"]:
                verification = "Run the application: `go run main.go`"
            elif primary_lang.lower() in ["rust"]:
                verification = "Run the application: `cargo run`"
            else:
                verification = (
                    "Consult the project documentation for running instructions"
                )

        # Build the documentation with natural language
        prereqs_text = (
            "\n".join([f"- {p}" for p in prereqs])
            if prereqs
            else "- No specific prerequisites detected"
        )

        steps_text = (
            "\n".join([f"{i + 1}. {s}" for i, s in enumerate(step_list)])
            if step_list
            else "No setup steps detected"
        )

        doc = f"""# Setup Guide

## Prerequisites
{prereqs_text}

## Installation Steps
{steps_text}

## Verification
{verification}

---
*Generated for {state.get("repo_url", "this repository")}*
"""

        doc = self._truncate_smart(doc, max_length=3000)

        self._append_audit(
            state, "setup_guide", {"status": "success", "confidence": 0.9}
        )
        return doc

    def generate_architecture_summary(
        self,
        state: WorkflowState,
        repo_type: str = "",
        components: Optional[List[str]] = None,
        dependencies: Optional[Dict[str, Any]] = None,
    ) -> str:
        classification = state.get("classification", repo_type or "Unknown")
        file_index = state.get("file_index", [])
        file_count = len(file_index)

        # Get project description
        project_desc = self._generate_project_description(state)

        # Extract components from file summaries if available
        file_summaries = state.get("file_summaries", {})

        if components is None:
            if file_summaries:
                components = list(file_summaries.keys())[:10]
            else:
                components = self._extract_components(
                    dependencies or state.get("dependency_graph", {})
                )

        # Generate dependency overview
        deps = dependencies or state.get("dependencies", {})
        dep_overview = self._generate_dependency_overview(deps)

        # Generate structure overview
        structure_overview = self._generate_structure_overview(file_index)

        # Build natural language components section
        if components:
            comp_details = []
            for comp in components[:5]:
                summary = file_summaries.get(comp, "")
                if summary:
                    comp_details.append(
                        f"**{comp}**: {self._truncate_smart(summary, max_length=150)}"
                    )
                else:
                    comp_details.append(f"**{comp}**")

            components_text = "\n".join([f"- {c}" for c in comp_details])
            if len(components) > 5:
                components_text += f"\n- ... and {len(components) - 5} more components"
        else:
            components_text = "No detailed component information available"

        doc = f"""# Architecture Summary

## Project Overview
{project_desc}

## Classification
This project is classified as: **{classification}**

## File Structure
The repository contains **{file_count}** files organized as follows:

{structure_overview}

## Key Components
{components_text}

## Dependencies Overview
{dep_overview}

---
*Analysis based on {len(file_index)} files scanned*
"""

        doc = self._truncate_smart(doc, max_length=4000)

        self._append_audit(
            state, "architecture_summary", {"status": "success", "confidence": 0.85}
        )
        return doc

    def _generate_dependency_overview(self, deps: Dict[str, Any]) -> str:
        """Generate a natural language overview of dependencies."""
        if not deps:
            return "No dependencies detected"

        lines = []

        for lang, packages in deps.items():
            if not packages:
                continue

            if isinstance(packages, list):
                count = len(packages)
                top_packages = packages[:5]
                if count <= 3:
                    pkg_list = self._generate_natural_list(packages, max_items=count)
                else:
                    pkg_list = self._generate_natural_list(top_packages, max_items=3)
                    pkg_list += f" (and {count - 3} more)"

                lines.append(f"**{lang}**: {pkg_list}")
            elif isinstance(packages, dict):
                count = len(packages)
                lines.append(f"**{lang}**: {count} packages detected")

        if not lines:
            return "Dependencies found but could not be parsed"

        return "\n".join(lines)

    def _generate_structure_overview(self, file_index: List[str]) -> str:
        """Generate a natural language overview of the project structure."""
        if not file_index:
            return "No files found in repository"

        # Group files by directory
        dirs: Dict[str, int] = {}
        for f in file_index:
            if "/" in f:
                dir_part = f.rsplit("/", 1)[0]
                dirs[dir_part] = dirs.get(dir_part, 0) + 1

        # Get top directories
        top_dirs = sorted(dirs.items(), key=lambda x: x[1], reverse=True)[:5]

        lines = []
        for dir_name, count in top_dirs:
            # Simplify directory names
            display_name = dir_name.split("/")[0] if "/" in dir_name else dir_name
            lines.append(f"- **{display_name}**: {count} files")

        root_files = len([f for f in file_index if "/" not in f])
        if root_files > 0:
            lines.append(f"- **Root level**: {root_files} files")

        return "\n".join(lines) if lines else "Flat file structure detected"

    def generate_api_documentation(
        self,
        state: WorkflowState,
        overview: str = "",
        endpoints: Optional[List[Dict[str, str]]] = None,
        models: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        classification = state.get("classification", "unknown")
        file_index = state.get("file_index", [])

        # Generate overview if not provided
        if not overview:
            primary_lang = state.get("primary_language", "")
            file_count = len(file_index)

            # Detect API framework
            api_framework = self._detect_api_framework(file_index)

            if api_framework:
                overview = f"This API is built using **{api_framework}** and consists of {file_count} files. "
                overview += f"It's classified as a {classification} project."
            else:
                overview = f"This is a {classification} project containing {file_count} files. "
                overview += (
                    "API endpoints and models have been inferred from the codebase."
                )

        # Extract endpoints if not provided
        eps = endpoints
        if eps is None:
            eps = self._extract_endpoints(file_index, state.get("file_summaries", {}))

        # Extract models if not provided
        mdl = models
        if mdl is None:
            mdl = self._extract_models(file_index, state.get("file_summaries", {}))

        # Format endpoints
        if eps:
            endpoint_list = []
            for ep in eps[:10]:
                method = ep.get("method", "GET")
                path = ep.get("path", "/")
                desc = ep.get("description", "No description")
                endpoint_list.append(f"- **{method}** `{path}`: {desc}")
            endpoints_text = "\n".join(endpoint_list)
            if len(eps) > 10:
                endpoints_text += f"\n- ... and {len(eps) - 10} more endpoints"
        else:
            endpoints_text = "No API endpoints detected in the codebase"

        # Format models
        if mdl:
            model_list = []
            for m in mdl[:10]:
                name = m.get("name", "Unknown")
                fields = m.get("fields", "N/A")
                model_list.append(f"- **{name}**: {fields}")
            models_text = "\n".join(model_list)
            if len(mdl) > 10:
                models_text += f"\n- ... and {len(mdl) - 10} more models"
        else:
            models_text = "No data models detected"

        doc = f"""# API Documentation

## Overview
{overview}

## Endpoints
{endpoints_text}

## Data Models
{models_text}

---
*Documentation generated from codebase analysis*
"""

        doc = self._truncate_smart(doc, max_length=3500)

        self._append_audit(
            state, "api_documentation", {"status": "success", "confidence": 0.85}
        )
        return doc

    def _detect_api_framework(self, file_index: List[str]) -> Optional[str]:
        """Detect the API framework used in the project."""
        files_str = " ".join(file_index).lower()

        # Check for various framework indicators
        frameworks = {
            "FastAPI": ["fastapi", "uvicorn"],
            "Flask": ["flask"],
            "Django": ["django", "urls.py", "views.py", "settings.py"],
            "Express": ["express", "app.js", "server.js"],
            "Spring Boot": ["spring", "application.java", "controller"],
            "Gin": ["gin"],
            "Echo": ["echo"],
            "Rails": ["routes.rb", "application_controller"],
            "Laravel": ["routes/web.php", "Controller.php"],
        }

        for framework, indicators in frameworks.items():
            if any(ind in files_str for ind in indicators):
                return framework

        return None

    def _extract_endpoints(
        self, file_index: List[str], file_summaries: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Extract API endpoints from file index and summaries."""
        endpoints = []

        # Look for route files
        route_files = [
            f
            for f in file_index
            if any(x in f.lower() for x in ["route", "endpoint", "api"])
        ]

        for rf in route_files[:5]:
            summary = file_summaries.get(rf, "")
            if "get" in summary.lower() or "post" in summary.lower():
                endpoints.append(
                    {
                        "path": f"/{rf.replace('.py', '').replace('.js', '')}",
                        "method": "GET/POST",
                        "description": summary[:100] if summary else "Route handler",
                    }
                )

        return endpoints

    def _extract_models(
        self, file_index: List[str], file_summaries: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Extract data models from file index and summaries."""
        models = []

        # Look for model files
        model_files = [
            f
            for f in file_index
            if any(x in f.lower() for x in ["model", "schema", "entity"])
        ]

        for mf in model_files[:10]:
            summary = file_summaries.get(mf, "")
            models.append(
                {
                    "name": mf.split("/")[-1].rsplit(".", 1)[0],
                    "fields": summary[:80] if summary else "Model definition",
                }
            )

        return models

    def _extract_components(self, dep_graph: Dict[str, Any]) -> List[str]:
        """Extract components from dependency graph."""
        modules = dep_graph.get("modules", {})
        if modules:
            return list(modules.keys())

        nodes = dep_graph.get("nodes", [])
        return [n.get("file", "unknown") for n in nodes[:10]]


_documentation_agent: Optional[DocumentationAgent] = None


def get_documentation_agent() -> DocumentationAgent:
    global _documentation_agent
    if _documentation_agent is None:
        _documentation_agent = DocumentationAgent()
    return _documentation_agent
