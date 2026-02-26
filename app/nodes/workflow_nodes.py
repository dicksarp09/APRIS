import os
import subprocess
import tempfile
import shutil
from typing import List, Optional
from app.nodes.base import BaseNode, NodeResult, SandboxableNode
from app.graph.state import WorkflowState


class CloneRepoNode(SandboxableNode):
    def __init__(self):
        super().__init__("CloneRepo", cost=2.0, requires_sandbox=True)

    def execute_in_sandbox(self, state: WorkflowState) -> NodeResult:
        repo_url = state.get("repo_url", "")
        if not repo_url:
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="invalid_input",
                retryable=False,
            )

        try:
            import uuid

            base_dir = os.path.join(os.path.expanduser("~"), ".apris", "repos")
            os.makedirs(base_dir, exist_ok=True)

            repo_name = repo_url.rstrip("/").split("/")[-1]
            unique_id = uuid.uuid4().hex[:8]
            repo_path = os.path.join(base_dir, f"{repo_name}_{unique_id}")

            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, repo_path],
                capture_output=True,
                timeout=180,
            )
            if result.returncode != 0:
                return NodeResult(
                    status="failure",
                    confidence=0.0,
                    error_type="clone_failed",
                    retryable=True,
                    updates={
                        "error_state": {
                            "error_type": "clone_failed",
                            "message": result.stderr.decode(),
                        }
                    },
                )

            files = []
            for root, _, filenames in os.walk(repo_path):
                for f in filenames:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, repo_path)
                    if not rel_path.startswith(".git"):
                        files.append(rel_path)

            updates = {
                "file_index": sorted(files),
                "repo_metadata": {"local_path": repo_path, "clone_success": True},
            }
            return NodeResult(
                status="success", confidence=1.0, retryable=False, updates=updates
            )
        except subprocess.TimeoutExpired:
            return NodeResult(
                status="failure", confidence=0.0, error_type="timeout", retryable=True
            )
        except Exception as e:
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="execution_error",
                retryable=True,
                updates={
                    "error_state": {"error_type": "execution_error", "message": str(e)}
                },
            )

    def _execute_internal(self, state: WorkflowState) -> NodeResult:
        return self.execute_in_sandbox(state)


class ProfileRepoNode(SandboxableNode):
    def __init__(self):
        super().__init__("ProfileRepo", cost=1.5, requires_sandbox=True)

    def execute_in_sandbox(self, state: WorkflowState) -> NodeResult:
        repo_metadata = state.get("repo_metadata", {})
        repo_path = repo_metadata.get("local_path")

        if not repo_path or not os.path.exists(repo_path):
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="repo_not_found",
                retryable=False,
            )

        try:
            metadata = self._analyze_structure(repo_path)
            metadata.update(repo_metadata)
            return NodeResult(
                status="success",
                confidence=0.9,
                retryable=False,
                updates={"repo_metadata": metadata},
            )
        except Exception as e:
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="analysis_error",
                retryable=True,
                updates={
                    "error_state": {"error_type": "analysis_error", "message": str(e)}
                },
            )

    def _analyze_structure(self, repo_path: str) -> dict:
        file_types = {}
        total_size = 0

        for root, _, files in os.walk(repo_path):
            for f in files:
                full_path = os.path.join(root, f)
                if os.path.isfile(full_path):
                    total_size += os.path.getsize(full_path)
                    ext = os.path.splitext(f)[1] or "no_ext"
                    file_types[ext] = file_types.get(ext, 0) + 1

        return {
            "file_types": file_types,
            "total_size": total_size,
            "profile_complete": True,
        }

    def _execute_internal(self, state: WorkflowState) -> NodeResult:
        return self.execute_in_sandbox(state)


class ClassifyRepoNode(BaseNode):
    def __init__(self):
        super().__init__("ClassifyRepo", cost=1.0)

    def execute(self, state: WorkflowState) -> NodeResult:
        repo_metadata = state.get("repo_metadata", {})
        file_types = repo_metadata.get("file_types", {})

        classification = self._classify(file_types)

        return NodeResult(
            status="success",
            confidence=0.85,
            retryable=False,
            updates={"classification": classification},
        )

    def _classify(self, file_types: dict) -> str:
        exts = set(file_types.keys())
        if ".py" in exts:
            return "python"
        elif ".js" in exts or ".ts" in exts:
            return "javascript"
        elif ".java" in exts:
            return "java"
        elif ".go" in exts:
            return "go"
        elif ".rs" in exts:
            return "rust"
        elif ".cpp" in exts or ".cc" in exts or ".cxx" in exts:
            return "cpp"
        elif ".cs" in exts:
            return "csharp"
        elif ".rb" in exts:
            return "ruby"
        elif ".php" in exts:
            return "php"
        elif ".swift" in exts:
            return "swift"
        elif ".kt" in exts:
            return "kotlin"
        return "unknown"


class SafetyScanNode(SandboxableNode):
    def __init__(self):
        super().__init__("SafetyScan", cost=1.5, requires_sandbox=True)

    def execute_in_sandbox(self, state: WorkflowState) -> NodeResult:
        repo_metadata = state.get("repo_metadata", {})
        repo_path = repo_metadata.get("local_path")

        if not repo_path:
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="repo_not_found",
                retryable=False,
            )

        try:
            issues = self._scan_for_dangers(repo_path)
            if issues:
                return NodeResult(
                    status="failure",
                    confidence=1.0,
                    error_type="safety_violation",
                    retryable=False,
                    updates={"error_state": {"safety_issues": issues}},
                )

            return NodeResult(
                status="success",
                confidence=1.0,
                retryable=False,
                updates={"repo_metadata": {**repo_metadata, "safety_passed": True}},
            )
        except Exception as e:
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="scan_error",
                retryable=True,
            )

    def _scan_for_dangers(self, repo_path: str) -> List[dict]:
        issues = []
        dangerous_patterns = ["eval(", "exec(", "subprocess.call", "os.system"]

        for root, _, files in os.walk(repo_path):
            for f in files:
                if f.endswith((".py", ".js", ".sh", ".bash")):
                    full_path = os.path.join(root, f)
                    try:
                        with open(
                            full_path, "r", encoding="utf-8", errors="ignore"
                        ) as fp:
                            content = fp.read()
                            for pattern in dangerous_patterns:
                                if pattern in content:
                                    issues.append(
                                        {
                                            "file": f,
                                            "pattern": pattern,
                                            "severity": "high",
                                        }
                                    )
                    except Exception:
                        pass
        return issues

    def _execute_internal(self, state: WorkflowState) -> NodeResult:
        return self.execute_in_sandbox(state)


class ParseFilesNode(SandboxableNode):
    def __init__(self):
        super().__init__("ParseFiles", cost=3.0, requires_sandbox=True)

    def execute_in_sandbox(self, state: WorkflowState) -> NodeResult:
        file_index = state.get("file_index", [])
        repo_metadata = state.get("repo_metadata", {})
        repo_path = repo_metadata.get("local_path")

        if not repo_path:
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="repo_not_found",
                retryable=False,
            )

        try:
            parsed = {}
            for filepath in sorted(file_index):
                full_path = os.path.join(repo_path, filepath)
                if os.path.isfile(full_path):
                    parsed[filepath] = self._parse_file(full_path)

            return NodeResult(
                status="success",
                confidence=0.9,
                retryable=False,
                updates={"repo_metadata": {**repo_metadata, "parsed_files": parsed}},
            )
        except Exception as e:
            return NodeResult(
                status="failure",
                confidence=0.0,
                error_type="parse_error",
                retryable=True,
            )

    def _parse_file(self, filepath: str) -> dict:
        ext = os.path.splitext(filepath)[1]
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return {
                "extension": ext,
                "size": len(content),
                "lines": len(content.splitlines()),
                "parseable": True,
            }
        except Exception:
            return {"extension": ext, "parseable": False}

    def _execute_internal(self, state: WorkflowState) -> NodeResult:
        return self.execute_in_sandbox(state)


class SummarizeFilesNode(BaseNode):
    def __init__(self):
        super().__init__("SummarizeFiles", cost=2.5)

    def execute(self, state: WorkflowState) -> NodeResult:
        repo_metadata = state.get("repo_metadata", {})
        parsed_files = repo_metadata.get("parsed_files", {})
        file_index = state.get("file_index", [])
        repo_path = repo_metadata.get("local_path", "")

        summaries = {}
        file_contents = {}

        for filepath in sorted(file_index):
            if filepath in parsed_files:
                parsed = parsed_files[filepath]
                summary, content = self._summarize(filepath, parsed, repo_path)
                summaries[filepath] = summary
                if content:
                    file_contents[filepath] = content

        return NodeResult(
            status="success",
            confidence=0.8,
            retryable=False,
            updates={"summaries": summaries, "file_contents": file_contents},
        )

    def _summarize(self, filepath: str, parsed: dict, repo_path: str) -> tuple:
        ext = parsed.get("extension", "")
        lines = parsed.get("lines", 0)
        size = parsed.get("size", 0)

        content = ""
        if ext in [
            ".py",
            ".md",
            ".txt",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".yaml",
            ".yml",
            ".json",
            ".toml",
            ".ini",
            ".cfg",
        ]:
            try:
                full_path = os.path.join(repo_path, filepath) if repo_path else filepath
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
            except Exception:
                pass

        basic_info = f"{filepath}: {ext} file, {lines} lines, {size} bytes"

        if content:
            if filepath.lower().endswith("readme.md") or filepath.lower() == "readme":
                return (f"{basic_info}\n# README CONTENT DETECTED", content)
            elif filepath.endswith(".py"):
                functions = self._extract_functions(content)
                imports = self._extract_imports(content)
                desc = f"{basic_info}\n  Imports: {', '.join(imports[:5])}\n  Functions: {', '.join(functions[:5])}"
                return (desc, content)
            elif filepath.endswith(".md"):
                return (f"{basic_info}\n# DOCUMENTATION", content)

        return (basic_info, content)

    def _extract_functions(self, content: str) -> list:
        import re

        functions = re.findall(r"^def (\w+)", content, re.MULTILINE)
        classes = re.findall(r"^class (\w+)", content, re.MULTILINE)
        return functions + classes

    def _extract_imports(self, content: str) -> list:
        import re

        imports = re.findall(r"^import (\w+)", content, re.MULTILINE)
        from_imports = re.findall(r"^from (\w+)", content, re.MULTILINE)
        return imports + from_imports


class BuildDependencyGraphNode(BaseNode):
    def __init__(self):
        super().__init__("BuildDependencyGraph", cost=2.0)

    def execute(self, state: WorkflowState) -> NodeResult:
        classification = state.get("classification", "")
        file_index = state.get("file_index", [])
        file_contents = state.get("file_contents", {})
        repo_metadata = state.get("repo_metadata", {})
        repo_path = repo_metadata.get("local_path", "")

        dep_graph = self._build_graph(
            classification, file_index, file_contents, repo_path
        )

        return NodeResult(
            status="success",
            confidence=0.85,
            retryable=False,
            updates={"dependency_graph": dep_graph},
        )

    def _build_graph(
        self,
        classification: str,
        file_index: List[str],
        file_contents: dict,
        repo_path: str,
    ) -> dict:
        import re

        # External packages (third-party)
        external_packages = set()
        # Internal modules
        internal_modules = {}
        # Edges (import relationships)
        edges = []

        # Service detection
        services = {
            "api": [],
            "database": [],
            "ml_ai": [],
            "metrics": [],
            "config": [],
            "utils": [],
        }

        # External services used
        external_services = {
            "mongodb": [],
            "postgres": [],
            "mysql": [],
            "redis": [],
            "groq": [],
            "openai": [],
            "anthropic": [],
            "aws": [],
            "gcp": [],
            "docker": [],
            "kafka": [],
        }

        # Get all Python files for local module detection
        py_files = {
            f: f.replace("\\", "/").replace("/", ".").replace(".py", "")
            for f in file_index
            if f.endswith(".py")
        }

        for filepath in file_index:
            if not filepath.endswith(".py"):
                continue

            # Get content
            content = file_contents.get(filepath, "")
            if not content and repo_path:
                full_path = os.path.join(repo_path, filepath)
                if os.path.exists(full_path):
                    try:
                        with open(
                            full_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()
                    except:
                        continue

            if not content:
                continue

            # Extract imports
            local_imports = []
            external_imports = []

            # from X import Y
            from_imports = re.findall(
                r"^from\s+([\w.]+)\s+import", content, re.MULTILINE
            )
            # import X
            direct_imports = re.findall(r"^import\s+([\w.]+)", content, re.MULTILINE)

            all_imports = from_imports + direct_imports

            for imp in all_imports:
                # Check if it's a local module
                is_local = False
                for py_file, module_name in py_files.items():
                    if imp == module_name or imp.startswith(module_name + "."):
                        is_local = True
                        local_imports.append(imp)
                        edges.append(
                            {"from": filepath, "to": py_file, "type": "import"}
                        )
                        break

                if not is_local:
                    # It's external
                    pkg = imp.split(".")[0]
                    if pkg not in (
                        "sys",
                        "os",
                        "typing",
                        "re",
                        "json",
                        "time",
                        "datetime",
                        "logging",
                        "collections",
                        " pathlib",
                        "abc",
                        "typing_extensions",
                        "contextlib",
                        "functools",
                        "itertools",
                        "uuid",
                        "hashlib",
                    ):
                        external_imports.append(pkg)
                        external_packages.add(pkg)

            # Categorize file into service layer (order matters - API takes precedence)
            fname = filepath.lower()
            # First check for explicit API files
            if any(
                x in fname
                for x in [
                    "main.py",
                    "server.py",
                    "app.py",
                    "api.py",
                    "router",
                    "endpoint",
                    "fastapi",
                ]
            ):
                services["api"].append(filepath)
            elif any(x in fname for x in ["mcp", "agent"]):
                services["api"].append(filepath)  # MCP is a protocol/API
            elif any(
                x in fname
                for x in [
                    "metric",
                    "observability",
                    "tracing",
                    "log",
                    "prometheus",
                    "grafana",
                ]
            ):
                services["metrics"].append(filepath)
            elif any(
                x in fname for x in ["db", "database", "model", "repository", "mongo"]
            ):
                services["database"].append(filepath)
            elif any(x in fname for x in ["config", "setting", "env"]):
                services["config"].append(filepath)
            elif any(x in fname for x in ["util", "helper", "tool"]):
                services["utils"].append(filepath)
            # Only ML/AI if explicitly ML-related
            elif any(
                x in fname
                for x in [
                    "model",
                    "train",
                    "inference",
                    "tensor",
                    "torch",
                    "tensorflow",
                ]
            ):
                services["ml_ai"].append(filepath)

            # Detect external service usage
            content_lower = content.lower()
            if "mongo" in content_lower or "pymongo" in content_lower:
                external_services["mongodb"].append(filepath)
            if "groq" in content_lower:
                external_services["groq"].append(filepath)
            if "openai" in content_lower:
                external_services["openai"].append(filepath)
            if "psycopg" in content_lower or "asyncpg" in content_lower:
                external_services["postgres"].append(filepath)
            if "redis" in content_lower:
                external_services["redis"].append(filepath)
            if "boto" in content_lower or "boto3" in content_lower:
                external_services["aws"].append(filepath)

            # Build module info
            module_name = (
                filepath.replace("\\", "/").replace("/", ".").replace(".py", "")
            )

            # Extract classes and functions
            classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
            functions = re.findall(r"^def\s+(\w+)", content, re.MULTILINE)

            internal_modules[filepath] = {
                "module": module_name,
                "imports": local_imports,
                "external_imports": list(set(external_imports)),
                "exports": classes + functions,
                "layer": self._detect_layer(filepath, services),
            }

        # Build nodes with more detail
        nodes = []
        for f in sorted(file_index):
            if f.endswith(".py"):
                module_info = internal_modules.get(f, {})
                nodes.append(
                    {
                        "file": f,
                        "type": "module",
                        "module": module_info.get("module", ""),
                        "exports": module_info.get("exports", [])[:10],
                        "layer": module_info.get("layer", "unknown"),
                    }
                )

        # Detect cycles (simple detection)
        cycles = self._detect_cycles(edges, internal_modules)

        return {
            "language": classification,
            "nodes": nodes,
            "edges": edges[:100],  # Limit edges
            "modules": internal_modules,
            "external_packages": list(external_packages)[:30],
            "services": {k: v for k, v in services.items() if v},
            "external_services": {k: v for k, v in external_services.items() if v},
            "cycles": cycles,
            "stats": {
                "total_modules": len(internal_modules),
                "total_edges": len(edges),
                "external_deps": len(external_packages),
            },
        }

    def _detect_layer(self, filepath: str, services: dict) -> str:
        """Detect which layer the file belongs to"""
        fname = filepath.lower()
        if any(x in fname for x in ["api", "router", "endpoint", "controller"]):
            return "api"
        if any(x in fname for x in ["db", "database", "model", "repository"]):
            return "data"
        if any(x in fname for x in ["service", "business"]):
            return "service"
        if any(x in fname for x in ["ml", "ai", "model", "llm"]):
            return "ml_ai"
        if any(x in fname for x in ["metric", "observability", "log"]):
            return "observability"
        if any(x in fname for x in ["config", "setting"]):
            return "config"
        return "utility"

    def _detect_cycles(self, edges: list, modules: dict) -> list:
        """Detect import cycles"""
        cycles = []

        # Build adjacency dict
        adj = {}
        for edge in edges:
            from_file = edge.get("from", "")
            to_file = edge.get("to", "")
            if from_file and to_file:
                if from_file not in adj:
                    adj[from_file] = set()
                adj[from_file].add(to_file)

        # Simple cycle detection using DFS
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in adj:
            visited = set()
            rec_stack = set()
            if has_cycle(node, visited, rec_stack):
                cycles.append({"type": "import_cycle", "files": list(rec_stack)})
                break

        return cycles[:5]  # Limit cycles


class ContentAnalysisNode(BaseNode):
    def __init__(self):
        super().__init__("ContentAnalysis", cost=3.0)

    def execute(self, state: WorkflowState) -> NodeResult:
        file_contents = state.get("file_contents", {})
        file_index = state.get("file_index", [])
        classification = state.get("classification", "")
        repo_path = state.get("repo_metadata", {}).get("local_path", "")

        # Collect all documentation files
        doc_files = {}
        project_files = {}
        config_files = {}
        requirements = {}

        # File extension analysis
        file_extensions = {}
        binary_extensions = {
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".bin",
            ".dat",
            ".zip",
            ".tar",
            ".gz",
            ".jpg",
            ".png",
            ".gif",
            ".ico",
            ".pdf",
            ".so",
        }

        for filepath in sorted(file_index):
            ext = os.path.splitext(filepath)[1].lower()

            # Skip binary files
            if ext in binary_extensions:
                continue

            if filepath in file_contents:
                content = file_contents[filepath]
                file_extensions[ext] = file_extensions.get(ext, 0) + 1

                # Documentation files
                if any(
                    doc in filepath.lower()
                    for doc in [
                        "readme",
                        "contributing",
                        "license",
                        "changelog",
                        "install",
                    ]
                ):
                    if filepath not in doc_files or len(doc_files[filepath]) < len(
                        content
                    ):
                        doc_files[filepath] = content[:8000]

                # Configuration files
                if any(
                    cfg in filepath.lower()
                    for cfg in [
                        "dockerfile",
                        "docker-compose",
                        ".env",
                        ".gitignore",
                        "Makefile",
                        "railway",
                        "vercel",
                        "netlify",
                    ]
                ):
                    config_files[filepath] = content[:3000]

                # Requirements/dependencies
                if "requirements" in filepath or filepath in [
                    "package.json",
                    "go.mod",
                    "Cargo.toml",
                    "Pipfile",
                    "poetry.lock",
                    "Gemfile",
                    "pom.xml",
                    "build.gradle",
                ]:
                    requirements[filepath] = content[:5000]

                # Language-specific files
                if filepath.endswith(".py"):
                    project_files[filepath] = content[:5000]
                elif filepath.endswith(
                    (".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte")
                ):
                    project_files[filepath] = content[:5000]
                elif filepath.endswith((".go", ".rs", ".java", ".cpp", ".c", ".cs")):
                    project_files[filepath] = content[:5000]

        # Analyze documentation
        project_description = self._analyze_project_docs(
            doc_files, config_files, requirements
        )

        # Determine primary language from extensions and indicator files
        primary_lang = self._detect_primary_language(
            file_extensions, file_index, requirements
        )

        # Analyze files by language
        file_summaries = {}
        py_files = {k: v for k, v in project_files.items() if k.endswith(".py")}
        js_files = {
            k: v
            for k, v in project_files.items()
            if k.endswith((".js", ".jsx", ".ts", ".tsx"))
        }
        go_files = {k: v for k, v in project_files.items() if k.endswith(".go")}
        rust_files = {k: v for k, v in project_files.items() if k.endswith(".rs")}

        for filepath, content in py_files.items():
            file_summaries[filepath] = self._analyze_python_file(filepath, content)

        for filepath, content in js_files.items():
            file_summaries[filepath] = self._analyze_js_file(filepath, content)

        for filepath, content in go_files.items():
            file_summaries[filepath] = self._analyze_go_file(filepath, content)

        for filepath, content in rust_files.items():
            file_summaries[filepath] = self._analyze_rust_file(filepath, content)

        # Parse requirements
        dependencies = self._parse_dependencies(requirements)

        # Extract configuration info
        config_info = self._analyze_configs(config_files)

        # Try LLM-powered summary if available
        llm_summary = ""
        try:
            from app.agents.analysis_agent import get_analysis_agent

            agent = get_analysis_agent()
            repo_name = state.get("repo_url", "").split("/")[-1].replace(".git", "")
            purpose = project_description.get("purpose", "Unknown")
            features = ", ".join(project_description.get("key_features", [])[:5])
            deps = ", ".join(
                dependencies.get("python", [])[:5]
                + dependencies.get("javascript", [])[:5]
            )
            config = ", ".join(
                config_info.get("docker", []) + config_info.get("cloud", [])
            )

            result = agent.run_analysis(
                "repo_summary",
                {
                    "repo_name": repo_name,
                    "primary_language": primary_lang,
                    "file_count": str(len(file_index)),
                    "purpose": purpose,
                    "features": features,
                    "dependencies": deps,
                    "config": config,
                },
                state,
            )
            if result.get("status") == "success":
                llm_summary = result.get("analysis", "")
        except Exception:
            pass

        if llm_summary:
            project_description["llm_summary"] = llm_summary

        return NodeResult(
            status="success",
            confidence=0.85,
            retryable=False,
            updates={
                "project_description": project_description,
                "file_summaries": file_summaries,
                "dependencies": dependencies,
                "config_info": config_info,
                "primary_language": primary_lang,
            },
        )

    def _detect_primary_language(
        self,
        file_extensions: dict,
        file_index: Optional[List[str]] = None,
        requirements: Optional[dict] = None,
    ) -> str:
        """Detect primary language from file extensions and indicator files"""
        if file_index is None:
            file_index = []
        if requirements is None:
            requirements = {}

        lang_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "JavaScript (React)",
            ".ts": "TypeScript",
            ".tsx": "TypeScript (React)",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".vue": "Vue.js",
            ".svelte": "Svelte",
        }

        # Language indicator files (high-priority files that indicate the primary language)
        indicator_files = {
            "Python": [
                "main.py",
                "app.py",
                "server.py",
                "api.py",
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "Pipfile",
                "manage.py",
                "wsgi.py",
                "__main__.py",
            ],
            "JavaScript": [
                "package.json",
                "index.js",
                "app.js",
                "server.js",
                "webpack.config.js",
                "vite.config.js",
            ],
            "TypeScript": ["tsconfig.json", "index.ts", "app.ts"],
            "Go": ["go.mod", "main.go"],
            "Rust": ["Cargo.toml", "Cargo.lock", "main.rs", "lib.rs"],
            "Java": ["pom.xml", "build.gradle", "settings.gradle", "Main.java"],
            "Ruby": ["Gemfile", "config.ru", "Rakefile"],
            "PHP": ["composer.json", "index.php"],
        }

        # Calculate scores
        scores = {}

        # Count file extensions
        code_exts = {k: v for k, v in file_extensions.items() if k in lang_map}
        for ext, count in code_exts.items():
            lang = lang_map[ext]
            scores[lang] = scores.get(lang, 0) + count

        # Boost score based on indicator files
        if file_index:
            for lang, indicators in indicator_files.items():
                for indicator in indicators:
                    if any(
                        f.endswith(indicator) or f == indicator.lower()
                        for f in file_index
                    ):
                        scores[lang] = scores.get(lang, 0) + 10

        # Boost score based on requirements files
        if requirements:
            req_files = [r.lower() for r in requirements.keys()]
            if any("requirements" in r or r == "pipfile" for r in req_files):
                scores["Python"] = scores.get("Python", 0) + 15
            if "package.json" in req_files:
                scores["JavaScript"] = scores.get("JavaScript", 0) + 15
            if "go.mod" in req_files:
                scores["Go"] = scores.get("Go", 0) + 15
            if "cargo.toml" in req_files:
                scores["Rust"] = scores.get("Rust", 0) + 15

        if not scores:
            return "Unknown"

        primary_lang = max(scores, key=scores.get)
        return primary_lang

    def _analyze_project_docs(
        self, doc_files: dict, config_files: dict, requirements: dict
    ) -> dict:
        """Analyze all documentation files for project description"""
        description = {
            "purpose": "Analyzed repository",
            "key_features": [],
            "tech_stack": [],
            "structure": [],
            "languages": [],
            "deployment": [],
        }

        # Combine all doc content
        all_docs = []
        for filepath, content in sorted(doc_files.items()):
            all_docs.append(f"=== {filepath} ===\n{content}")

        combined_docs = "\n\n".join(all_docs)

        if combined_docs:
            lines = combined_docs.split("\n")

            # Find purpose (first substantial non-header line)
            for line in lines[:100]:
                line = line.strip()
                if (
                    line
                    and not line.startswith("#")
                    and not line.startswith("=")
                    and len(line) > 20
                ):
                    description["purpose"] = line[:300]
                    break

            # Extract features
            feature_keywords = [
                "feature",
                "capability",
                "support",
                "provides",
                "- ",
                "• ",
                "* ",
            ]
            for line in lines:
                if any(kw in line.lower() for kw in feature_keywords):
                    clean = line.strip().lstrip("-•*#").strip()
                    if (
                        10 < len(clean) < 150
                        and clean not in description["key_features"]
                    ):
                        description["key_features"].append(clean[:120])
                        if len(description["key_features"]) >= 8:
                            break

        # Extract deployment info from configs
        for filepath, content in config_files.items():
            if "docker" in filepath.lower() or "dockerfile" in filepath.lower():
                description["deployment"].append("Docker")
            if "railway" in filepath.lower():
                description["deployment"].append("Railway")
            if "vercel" in filepath.lower():
                description["deployment"].append("Vercel")
            if "netlify" in filepath.lower():
                description["deployment"].append("Netlify")
            if "kubernetes" in content.lower() or "k8s" in content.lower():
                description["deployment"].append("Kubernetes")

        # Parse dependencies from requirements files
        all_deps = []
        for filepath, content in requirements.items():
            if "requirements" in filepath or filepath == "package.json":
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        if "==" in line:
                            pkg = line.split("==")[0].strip()
                            all_deps.append(pkg)
                        elif filepath == "package.json":
                            # Try to extract package names from JSON
                            import json

                            try:
                                pkg_data = json.loads(content)
                                all_deps.extend(pkg_data.get("dependencies", {}).keys())
                            except:
                                pass

        description["tech_stack"] = list(set(all_deps))[:15]

        return description

    def _parse_dependencies(self, requirements: dict) -> dict:
        """Parse dependencies from various package managers"""
        deps = {
            "python": [],
            "javascript": [],
            "go": [],
            "rust": [],
            "docker": [],
        }

        for filepath, content in requirements.items():
            if "requirements" in filepath.lower():
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        if "==" in line:
                            deps["python"].append(line.split("==")[0].strip())
                        else:
                            deps["python"].append(line.strip())

            elif filepath == "package.json":
                import json

                try:
                    pkg_data = json.loads(content)
                    deps["javascript"] = list(pkg_data.get("dependencies", {}).keys())
                    deps["javascript"].extend(
                        list(pkg_data.get("devDependencies", {}).keys())
                    )
                except:
                    pass

            elif filepath == "go.mod":
                for line in content.split("\n"):
                    if line.startswith("require ("):
                        continue
                    if "require " in line:
                        pkg = line.replace("require", "").strip().split()[0]
                        deps["go"].append(pkg)

            elif filepath == "Cargo.toml":
                for line in content.split("\n"):
                    if line.strip().startswith("name = "):
                        deps["rust"].append(line.split("=")[1].strip().strip('"'))

        return deps

    def _analyze_configs(self, config_files: dict) -> dict:
        """Analyze configuration files"""
        config = {
            "docker": [],
            "environment": [],
            "ci_cd": [],
            "cloud": [],
        }

        for filepath, content in config_files.items():
            fname = filepath.lower()

            if "dockerfile" in fname:
                config["docker"].append("Dockerfile found")
            elif "docker-compose" in fname:
                config["docker"].append("docker-compose found")

            if ".env" in fname and "example" not in fname:
                config["environment"].append(f".env file: {filepath}")

            if any(
                ci in fname
                for ci in [".github", "gitlab-ci", "jenkins", "travis", "circleci"]
            ):
                config["ci_cd"].append(filepath)

            if any(
                cloud in fname
                for cloud in ["railway", "vercel", "netlify", "aws", "gcp", "azure"]
            ):
                config["cloud"].append(filepath)

        return config

    def _analyze_python_file(self, filepath: str, content: str) -> dict:
        """Analyze a single Python file and return its purpose and components"""
        import re

        summary = {
            "filepath": filepath,
            "purpose": "",
            "functions": [],
            "classes": [],
            "imports": [],
            "description": "",
        }

        lines = content.split("\n")

        # Extract imports
        for line in lines[:50]:
            if line.startswith("import "):
                summary["imports"].append(line.replace("import ", "").strip())
            elif line.startswith("from "):
                summary["imports"].append(
                    line.replace("from ", "").split(" import")[0].strip()
                )

        # Extract functions
        functions = re.findall(r"^def (\w+)\s*\([^)]*\):", content, re.MULTILINE)
        summary["functions"] = functions[:10]

        # Extract classes
        classes = re.findall(r"^class (\w+)[\(:]", content, re.MULTILINE)
        summary["classes"] = classes[:8]

        # Extract docstring (first module docstring)
        docstring_match = re.search(r'^"""(.+?)"""', content, re.MULTILINE | re.DOTALL)
        if docstring_match:
            summary["purpose"] = docstring_match.group(1).strip()[:150]

        # If no docstring, try to infer from classes/functions
        if not summary["purpose"]:
            if classes:
                summary["purpose"] = f"Defines {', '.join(classes[:3])} class(es)"
            elif functions:
                # Check if it's a main entry point
                if "__main__" in content or "if __name__" in content:
                    summary["purpose"] = "Main entry point script"
                else:
                    summary["purpose"] = (
                        f"Provides {len(functions)} function(s): {', '.join(functions[:3])}"
                    )
            else:
                summary["purpose"] = "Python module"

        # Generate description
        parts = []
        if classes:
            parts.append(f"Classes: {', '.join(classes[:3])}")
        if functions:
            parts.append(f"Functions: {', '.join(functions[:5])}")

        summary["description"] = " | ".join(parts) if parts else "Utility module"

        return summary

    def _analyze_js_file(self, filepath: str, content: str) -> dict:
        """Analyze JavaScript/TypeScript file"""
        import re

        summary = {
            "filepath": filepath,
            "purpose": "",
            "functions": [],
            "classes": [],
            "imports": [],
            "description": "",
        }

        # Extract imports
        import_patterns = [
            r"import\s+(?:{\s*)?([\w,\s]+)(?:\s*})?\s+from\s+['\"](.+?)['\"]",
            r"import\s+(.+?)\s+from\s+['\"](.+?)['\"]",
            r"require\(['\"](.+?)['\"]",
        ]

        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for m in matches:
                if isinstance(m, tuple):
                    summary["imports"].extend([x.strip() for x in m if x.strip()])
                else:
                    summary["imports"].append(str(m).strip())

        # Extract functions (various patterns)
        func_patterns = [
            r"function\s+(\w+)",
            r"const\s+(\w+)\s*=\s*(?:async\s*)?\(",
            r"const\s+(\w+)\s*=\s*async\s+",
            r"=>\s*function\s*(\w+)",
            r"export\s+(?:async\s+)?function\s+(\w+)",
        ]

        for pattern in func_patterns:
            matches = re.findall(pattern, content)
            summary["functions"].extend(matches)

        # Extract classes
        classes = re.findall(r"class\s+(\w+)", content)
        summary["classes"] = classes[:8]

        # Extract React components
        components = re.findall(
            r"(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)", content
        )
        if components:
            summary["purpose"] = f"React components: {', '.join(components[:3])}"

        # Extract exports
        exports = re.findall(
            r"export\s+(?:default\s+)?(?:const|let|var|function|class)\s+(\w+)", content
        )
        if exports and not summary["purpose"]:
            summary["purpose"] = f"Exports: {', '.join(exports[:5])}"

        if not summary["purpose"]:
            summary["purpose"] = "JavaScript/TypeScript module"

        # Description
        parts = []
        if classes:
            parts.append(f"Classes: {', '.join(classes[:3])}")
        if summary["functions"]:
            parts.append(f"Functions: {', '.join(summary['functions'][:5])}")

        summary["description"] = " | ".join(parts) if parts else "Utility module"

        return summary

    def _analyze_go_file(self, filepath: str, content: str) -> dict:
        """Analyze Go source file"""
        import re

        summary = {
            "filepath": filepath,
            "purpose": "",
            "functions": [],
            "types": [],
            "imports": [],
            "description": "",
        }

        lines = content.split("\n")

        for line in lines[:50]:
            if line.startswith("import "):
                import_name = line.replace("import ", "").strip().strip('"')
                summary["imports"].append(import_name)

        functions = re.findall(
            r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", content, re.MULTILINE
        )
        summary["functions"] = functions[:10]

        types = re.findall(r"^type\s+(\w+)", content, re.MULTILINE)
        summary["types"] = types[:8]

        if types:
            summary["purpose"] = f"Defines types: {', '.join(types[:3])}"
        elif functions:
            summary["purpose"] = f"Provides {len(functions)} function(s)"

        if not summary["purpose"]:
            summary["purpose"] = "Go package"

        parts = []
        if types:
            parts.append(f"Types: {', '.join(types[:3])}")
        if functions:
            parts.append(f"Functions: {', '.join(functions[:5])}")

        summary["description"] = " | ".join(parts) if parts else "Go module"
        return summary

    def _analyze_rust_file(self, filepath: str, content: str) -> dict:
        """Analyze Rust source file"""
        import re

        summary = {
            "filepath": filepath,
            "purpose": "",
            "functions": [],
            "structs": [],
            "impls": [],
            "imports": [],
            "description": "",
        }

        lines = content.split("\n")

        for line in lines[:50]:
            if line.startswith("use "):
                import_name = line.replace("use ", "").split("::")[0].strip()
                if "{" not in import_name:
                    summary["imports"].append(import_name)

        functions = re.findall(r"^pub\s+fn\s+(\w+)", content, re.MULTILINE)
        functions.extend(re.findall(r"^fn\s+(\w+)", content, re.MULTILINE))
        summary["functions"] = list(set(functions))[:10]

        structs = re.findall(r"^pub\s+struct\s+(\w+)", content, re.MULTILINE)
        structs.extend(re.findall(r"^struct\s+(\w+)", content, re.MULTILINE))
        summary["structs"] = list(set(structs))[:8]

        impls = re.findall(
            r"^impl(?:\s+\w+)?\s+(?:for\s+)?(\w+)", content, re.MULTILINE
        )
        summary["impls"] = list(set(impls))[:5]

        if summary["structs"]:
            summary["purpose"] = f"Defines structs: {', '.join(summary['structs'][:3])}"
        elif summary["functions"]:
            summary["purpose"] = f"Provides {len(summary['functions'])} function(s)"

        if not summary["purpose"]:
            summary["purpose"] = "Rust module"

        parts = []
        if summary["structs"]:
            parts.append(f"Structs: {', '.join(summary['structs'][:3])}")
        if summary["functions"]:
            parts.append(f"Functions: {', '.join(summary['functions'][:5])}")

        summary["description"] = " | ".join(parts) if parts else "Rust crate"
        return summary


class ArchitectureSynthesisNode(BaseNode):
    def __init__(self):
        super().__init__("ArchitectureSynthesis", cost=1.5)

    def execute(self, state: WorkflowState) -> NodeResult:
        classification = state.get("classification", "")
        dependency_graph = state.get("dependency_graph", {})
        repo_metadata = state.get("repo_metadata", {})
        project_description = state.get("project_description", {})

        summary = self._synthesize(
            classification, dependency_graph, repo_metadata, project_description
        )

        return NodeResult(
            status="success",
            confidence=0.9,
            retryable=False,
            updates={"architecture_summary": summary},
        )

    def _synthesize(
        self, classification: str, dep_graph: dict, metadata: dict, project_desc: dict
    ) -> str:
        parts = []

        # Basic info
        stats = dep_graph.get("stats", {})
        parts.append("**Architecture Overview**")
        parts.append(f"- **Language**: {classification}")
        parts.append(f"- **Modules**: {stats.get('total_modules', 0)} Python files")
        parts.append(
            f"- **Internal Dependencies**: {stats.get('total_edges', 0)} import relationships"
        )
        parts.append(
            f"- **External Packages**: {stats.get('external_deps', 0)} third-party libraries"
        )

        # Service layers
        services = dep_graph.get("services", {})
        if services:
            parts.append("\n**Service Layers:**")
            for layer, files in services.items():
                if files:
                    layer_name = layer.replace("_", " ").title()
                    parts.append(f"  - **{layer_name}**: {len(files)} files")

        # External services
        external = dep_graph.get("external_services", {})
        if external:
            parts.append("\n**External Integrations:**")
            for service, files in external.items():
                if files:
                    parts.append(
                        f"  - **{service.title()}**: Used in {len(files)} file(s)"
                    )

        # Architectural Pattern Detection
        pattern = self._detect_architecture_pattern(dep_graph, services, external)
        if pattern:
            parts.append(f"\n**Architecture Pattern**: {pattern}")

        # Data Flow / Query Path Detection
        flow = self._detect_data_flow(dep_graph, external)
        if flow:
            parts.append(f"\n**Data Flow (Query Path)**:\n  {flow}")

        # External packages (key ones - filter stdlib)
        stdlib = {
            "sys",
            "os",
            "typing",
            "re",
            "json",
            "time",
            "datetime",
            "logging",
            "collections",
            "pathlib",
            "abc",
            "contextlib",
            "functools",
            "itertools",
            "uuid",
            "hashlib",
            "asyncio",
            "enum",
            "threading",
            "multiprocessing",
            "dataclasses",
            "warnings",
            "tempfile",
            "io",
            "copy",
            "pickle",
        }

        ext_pkgs = dep_graph.get("external_packages", [])
        if ext_pkgs:
            key_pkgs = [
                p
                for p in ext_pkgs
                if p not in stdlib and p not in ("src",) and not p.startswith("src.")
            ]
            if key_pkgs:
                parts.append(
                    f"\n**Third-Party Dependencies**: `{', '.join(key_pkgs[:12])}`"
                )

        # Cycles
        cycles = dep_graph.get("cycles", [])
        if cycles:
            parts.append(f"\n⚠️ **Import Cycles Detected**: {len(cycles)}")

        # Module dependency summary
        modules = dep_graph.get("modules", {})
        if modules:
            # Find entry points (files with main/if __name__)
            entry_points = []
            for f, info in modules.items():
                exports = info.get("exports", [])
                if "main" in f or "__main__" in str(exports):
                    entry_points.append(f)
                elif len(info.get("imports", [])) < 3 and len(exports) > 2:
                    entry_points.append(f)

            if entry_points:
                parts.append(f"\n**Entry Points**: `{', '.join(entry_points[:3])}`")

        return "\n".join(parts)

    def _detect_architecture_pattern(
        self, dep_graph: dict, services: dict, external: dict
    ) -> str:
        """Detect architectural pattern from signals"""
        modules = dep_graph.get("modules", {})
        stats = dep_graph.get("stats", {})
        ext_services = dep_graph.get("external_services", {})

        module_count = stats.get("total_modules", 0)
        has_api = "api" in services
        has_metrics = "metrics" in services
        has_database = "database" in services
        has_mongo = bool(ext_services.get("mongodb", []))
        has_postgres = bool(ext_services.get("postgres", []))

        # Check for MVC indicators
        has_models = any(
            "model" in str(v.get("exports", [])).lower() for v in modules.values()
        )
        has_views = any(
            "view" in f.lower() or "template" in f.lower() for f in modules.keys()
        )
        has_controllers = any("controller" in f.lower() for f in modules.keys())

        # Check for service-oriented indicators
        has_multiple_entry_points = (
            len(
                [
                    f
                    for f in modules.keys()
                    if "main" in f.lower() or "server" in f.lower()
                ]
            )
            > 1
        )

        # Check for microservices indicators
        has_docker = bool(
            dep_graph.get("services", {}).get("docker")
        ) or "docker" in str(ext_services)
        has_k8s = any("k8s" in str(v) for v in ext_services.values())

        # Check for API-focused
        has_fastapi = any(
            "fastapi" in str(v.get("external_imports", [])) for v in modules.values()
        )
        has_flask = any(
            "flask" in str(v.get("external_imports", [])) for v in modules.values()
        )

        # Scoring for patterns
        scores = {
            "Layered Architecture": 0,
            "MVC (Model-View-Controller)": 0,
            "Service-Oriented Architecture (SOA)": 0,
            "Microservices": 0,
            "Monolithic": 0,
            "API-First Backend": 0,
            "Serverless-Ready": 0,
        }

        # Layered: has clear separation (API, service, data, utils)
        if len(services) >= 3:
            scores["Layered Architecture"] += 3
        elif len(services) >= 2:
            scores["Layered Architecture"] += 1

        # MVC
        if has_models:
            scores["MVC (Model-View-Controller)"] += 2
        if has_controllers:
            scores["MVC (Model-View-Controller)"] += 2
        if has_views:
            scores["MVC (Model-View-Controller)"] += 1

        # SOA
        if has_multiple_entry_points:
            scores["Service-Oriented Architecture (SOA)"] += 2
        if len(services) >= 3:
            scores["Service-Oriented Architecture (SOA)"] += 1

        # Microservices
        if has_docker:
            scores["Microservices"] += 2
        if has_k8s:
            scores["Microservices"] += 3
        if has_multiple_entry_points and module_count > 20:
            scores["Microservices"] += 1

        # Monolithic
        if module_count < 15 and not has_docker:
            scores["Monolithic"] += 2
        if not has_multiple_entry_points and has_fastapi or has_flask:
            scores["Monolithic"] += 1

        # API-First
        if has_fastapi or has_flask:
            scores["API-First Backend"] += 3
        if has_api:
            scores["API-First Backend"] += 2

        # Serverless
        if has_fastapi and not has_database:
            scores["Serverless-Ready"] += 1
        if (
            "railway" in str(ext_services)
            or "vercel" in str(ext_services)
            or "netlify" in str(ext_services)
        ):
            scores["Serverless-Ready"] += 2

        # Return best match
        if scores:
            best_pattern = max(scores, key=scores.get)
            if scores[best_pattern] > 0:
                return f"{best_pattern} (confidence: {scores[best_pattern]}/5)"

        return "Single-File Script" if module_count <= 1 else "Simple Module"

    def _detect_data_flow(self, dep_graph: dict, external: dict) -> str:
        """Detect data flow / query path through the system"""
        modules = dep_graph.get("modules", {})
        ext_services = dep_graph.get("external_services", {})

        # Check for RAG system patterns
        has_rag = False
        rag_components = []

        # Detect vector DB (Qdrant, Pinecone, Chroma, etc.)
        if ext_services.get("qdrant") or any(
            "qdrant" in str(v) for v in modules.values()
        ):
            rag_components.append("Vector DB (Qdrant)")
            has_rag = True
        if ext_services.get("pinecone") or any(
            "pinecone" in str(v) for v in modules.values()
        ):
            rag_components.append("Vector DB (Pinecone)")
            has_rag = True
        if ext_services.get("chroma") or any(
            "chroma" in str(v) for v in modules.values()
        ):
            rag_components.append("Vector DB (Chroma)")
            has_rag = True

        # Detect LLM providers
        if ext_services.get("groq"):
            rag_components.append("LLM (Groq)")
        if ext_services.get("openai"):
            rag_components.append("LLM (OpenAI)")
        if ext_services.get("anthropic"):
            rag_components.append("LLM (Anthropic)")

        # Detect SQL DB
        if ext_services.get("postgres") or ext_services.get("mysql"):
            rag_components.append("SQL Database")
        if ext_services.get("sqlite"):
            rag_components.append("SQLite")
        if ext_services.get("mongodb"):
            rag_components.append("MongoDB")

        # Detect cache/queue
        if ext_services.get("redis"):
            rag_components.append("Redis Cache")
        if ext_services.get("kafka"):
            rag_components.append("Kafka")

        # Build flow based on detected components
        flow_parts = []

        # Check for API layer
        has_api = any(
            "api" in services or "router" in str(v)
            for services, v in [(k, modules) for k in modules.keys()]
        )
        flow_parts.append("User")
        flow_parts.append("API Endpoint")

        if has_rag:
            flow_parts.append("Request Handler")
            if any(
                "retriever" in str(v).lower() or "retrieval" in str(v).lower()
                for v in modules.values()
            ):
                flow_parts.append("Retriever")
            if rag_components:
                flow_parts.append(rag_components[0])  # Vector DB
            flow_parts.append("Ranker/Processor")
            if rag_components and len(rag_components) > 1:
                flow_parts.append(rag_components[1])  # LLM
            elif any(
                "groq" in str(v).lower() or "openai" in str(v).lower()
                for v in modules.values()
            ):
                flow_parts.append("LLM")
            flow_parts.append("Response Formatter")
        else:
            # Non-RAG API flow
            if any("service" in str(v).lower() for v in modules.values()):
                flow_parts.append("Service Layer")
            if rag_components:
                flow_parts.append(rag_components[0])
            flow_parts.append("Response")

        flow_parts.append("User")

        # Create arrow flow
        flow = " → ".join(flow_parts)

        # Add component summary
        if rag_components:
            flow += f"\n\n**Components Detected**: {', '.join(rag_components)}"

        return flow


class DocumentationGenerationNode(BaseNode):
    def __init__(self):
        super().__init__("DocumentationGeneration", cost=1.0)

    def execute(self, state: WorkflowState) -> NodeResult:
        architecture_summary = state.get("architecture_summary", "")
        classification = state.get("classification", "")
        file_index = state.get("file_index", [])
        summaries = state.get("summaries", {})
        project_description = state.get("project_description", {})
        file_summaries = state.get("file_summaries", {})
        dependencies = state.get("dependencies", {})
        config_info = state.get("config_info", {})
        primary_language = state.get("primary_language", classification)

        doc = self._generate(
            architecture_summary,
            primary_language,
            file_index,
            summaries,
            project_description,
            file_summaries,
            dependencies,
            config_info,
            state,
        )

        return NodeResult(
            status="success",
            confidence=0.85,
            retryable=False,
            updates={"documentation": doc},
        )

    def _generate(
        self,
        arch: str,
        primary_language: str,
        files: List[str],
        summaries: dict,
        project_desc: dict,
        file_summaries: dict,
        dependencies: dict,
        config_info: dict,
        state: WorkflowState,
    ) -> str:
        doc = "# Repository Analysis\n\n"

        # AI/LLM Summary (if available)
        llm_summary = project_desc.get("llm_summary", "")
        if llm_summary:
            doc += f"> **AI Summary**: {llm_summary}\n\n"

        # Project Purpose
        if project_desc:
            purpose = project_desc.get("purpose", "")
            if purpose and purpose != "Analyzed repository":
                doc += f"## Project Overview\n\n{purpose}\n\n"

            features = project_desc.get("key_features", [])
            if features:
                doc += "## Key Features\n\n"
                for feature in features[:8]:
                    clean = feature.strip().lstrip("-•*").strip()
                    if len(clean) > 5:
                        doc += f"- {clean}\n"
                doc += "\n"

        # Technology Stack
        doc += "## Technology Stack\n\n"
        doc += f"**Primary Language**: {primary_language}\n\n"

        all_deps = []
        for lang, deps in dependencies.items():
            if deps:
                all_deps.extend(deps[:8])

        if all_deps:
            doc += f"**Dependencies**: `{'`, `'.join(all_deps[:12])}`\n\n"

        # === NEW: Decision-Oriented Sections ===

        # 1. Executive Summary
        doc += self._generate_executive_summary(
            project_desc, primary_language, file_summaries, config_info
        )

        # 2. Architectural Maturity Score
        doc += self._generate_maturity_score(
            file_summaries, config_info, dependencies, primary_language
        )

        # 3. Runtime Risk Profile
        doc += self._generate_risk_profile(file_summaries, dependencies)

        # 4. Complexity Profile
        doc += self._generate_complexity_profile(files, file_summaries, dependencies)

        # 5. Engineering Hygiene
        doc += self._generate_engineering_hygiene(config_info, file_summaries)

        # 6. Red Flags
        doc += self._generate_red_flags(file_summaries, dependencies, config_info)

        # === End Decision-Oriented Sections ===

        # Deployment & Infrastructure
        deployment = project_desc.get("deployment", [])
        if deployment or config_info.get("docker") or config_info.get("cloud"):
            doc += "## Deployment & Infrastructure\n\n"
            for d in set(deployment):
                doc += f"- {d}\n"
            for d in config_info.get("docker", []):
                doc += f"- {d}\n"
            for d in config_info.get("cloud", []):
                doc += f"- Cloud: {d}\n"
            doc += "\n"

        # Repository Details
        doc += f"## Repository Details\n\n"
        doc += f"- **Type**: {primary_language}\n"
        doc += f"- **Total Files**: {len(files)}\n"

        # Code files breakdown
        py_count = len([f for f in files if f.endswith(".py")])
        js_count = len([f for f in files if f.endswith((".js", ".jsx", ".ts", ".tsx"))])
        doc += f"- **Python Files**: {py_count}\n"
        doc += f"- **JS/TS Files**: {js_count}\n"
        doc += f"- **Architecture**: {arch}\n\n"

        # Add per-file analysis for Python files in natural language
        if file_summaries:
            doc += "## Code File Analysis\n\n"

            py_files = [
                (f, s) for f, s in sorted(file_summaries.items()) if f.endswith(".py")
            ]

            for filepath, file_summary in py_files:
                purpose = file_summary.get("purpose", "")
                classes = file_summary.get("classes", [])
                functions = file_summary.get("functions", [])
                imports = file_summary.get("imports", [])

                # Generate natural language description
                doc += (
                    self._generate_natural_description(
                        filepath, purpose, classes, functions, imports
                    )
                    + "\n\n"
                )

        doc += "## File Structure\n\n"
        for f in sorted(files)[:25]:
            if f in summaries:
                summary_line = summaries[f].split("\n")[0]
                doc += f"- `{f}`\n"

        return doc

    def _classify_file_role(
        self, filepath: str, purpose: str, classes: list, functions: list, imports: list
    ) -> dict:
        """Classify file into architectural role and determine characteristics"""

        import_str = " ".join(imports).lower()
        filename = filepath.lower().replace("\\", "/")

        role = "unknown"
        is_hot_path = False
        is_cost_sensitive = False
        is_cold_path = False
        description = ""

        # Infrastructure Layer - initialization, DB setup, config
        if any(
            x in filename for x in ["init_", "setup", "config", "create_db", "migrate"]
        ):
            role = "infrastructure"
            is_cold_path = True
            description = "Initializes infrastructure components. Runs during deployment or startup, not in the runtime query path."

        # Test files
        elif "test" in filename or "/tests/" in filename:
            role = "testing"
            description = (
                "Contains unit/integration tests. Not part of production runtime."
            )

        # Observability/Tracing
        elif any(
            x in filename
            for x in [
                "tracing",
                "monitoring",
                "metrics",
                "logging",
                "audit",
                "langsmith",
            ]
        ):
            role = "observability"
            description = "Provides observability and monitoring. Tracks runtime behavior but is not a latency driver."

        # Scripts - offline pipeline
        elif "/scripts/" in filename or filename.startswith("scripts/"):
            role = "offline_pipeline"
            is_cold_path = True
            description = "Offline preprocessing script. Runs during data ingestion or batch operations, not in the hot path."

        # Router/API Layer - thin boundary (check this BEFORE other checks)
        elif "/routers/" in filename or "/api/" in filename:
            role = "boundary"
            is_hot_path = True
            func_names = " ".join(functions).lower() if functions else ""

            if "ingest" in func_names or "ingestion" in filename:
                description = "Handles document ingestion endpoints. Thin adapter that validates requests and passes to service."
            elif "query" in func_names:
                description = "Handles query endpoints. Thin HTTP adapter - parses query params, delegates to retrieval service, formats response."
            elif "chunk" in func_names or "chunk" in filename:
                description = (
                    "Handles chunk retrieval endpoints. Returns stored document chunks."
                )
            elif "log" in func_names:
                description = (
                    "Handles logging/metrics endpoints. Returns system information."
                )
            elif "evaluat" in func_names:
                description = (
                    "Handles evaluation endpoints. Returns RAG evaluation metrics."
                )
            else:
                description = "HTTP adapter layer. Parses requests, calls service layer, formats responses. Not a cost driver."

        # Service/Orchestration Layer - coordinates multiple components

        # Service/Orchestration Layer - coordinates multiple components
        elif "/services/" in filepath or "/orchestr" in filename:
            role = "orchestration"
            is_hot_path = True
            is_cost_sensitive = True
            description = "Service orchestration layer. Coordinates retrieval, LLM calls, and postprocessing. This is a primary cost and latency driver."

        # Retrieval/Search Layer
        elif any(
            x in filename for x in ["retriev", "search", "hybrid", "ranker", "embed"]
        ):
            role = "retrieval"
            is_hot_path = True
            description = "Retrieval/search layer. Handles vector search, keyword matching, and ranking. Key latency driver in RAG systems."

        # Models/Schemas - data contracts
        elif (
            "/models/" in filepath or "/schemas" in filename or "schemas" in import_str
        ):
            role = "data_contract"
            description = "Defines data models and schemas. Pure data structures - no business logic."

        # Main entry point
        elif "main.py" in filename or purpose.lower().startswith("main entry"):
            role = "entry_point"
            description = (
                "Application entry point. Initializes components and starts the server."
            )

        # Default: analyze imports
        else:
            # Check for LLM calls (cost sensitive)
            has_llm = any(
                x in import_str for x in ["groq", "openai", "anthropic", "langchain"]
            )
            # Check for storage
            has_storage = any(
                x in import_str
                for x in ["sqlite", "sqlalchemy", "database", "qdrant", "chroma"]
            )
            # Check for API
            has_api = any(x in import_str for x in ["fastapi", "flask", "router"])

            if has_api and has_llm:
                role = "orchestration"
                is_hot_path = True
                is_cost_sensitive = True
                description = "Orchestrates API requests and LLM generation. Primary cost and latency driver."
            elif has_api:
                role = "boundary"
                is_hot_path = True
                description = "HTTP request handler. Thin adapter in the request path."
            elif has_llm and has_storage:
                role = "retrieval"
                is_hot_path = True
                description = "Retrieval layer connecting storage with LLM inference."
            elif has_storage:
                role = "infrastructure"
                is_cold_path = True
                description = "Data persistence layer. Not in the hot query path."
            else:
                role = "utility"
                description = "Utility module with helper functions."

        # Refine description based on specific file
        if role == "boundary" and functions:
            # Look at what the router actually does
            func_names = " ".join(functions).lower()
            if "ingest" in func_names:
                description = "Handles document ingestion endpoints. Thin adapter that validates and passes to ingestion service."
            elif "query" in func_names:
                description = "Handles query endpoints. Thin adapter that parses query params and returns responses."
            elif "chunk" in func_names:
                description = "Handles chunk/metadata endpoints. Read-only API for retrieved content."
            elif "log" in func_names:
                description = (
                    "Handles logging/monitoring endpoints. Returns system metrics."
                )
            elif "evaluat" in func_names:
                description = "Handles evaluation endpoints. Returns RAG system evaluation metrics."
            else:
                description = "HTTP adapter layer. Parses requests, calls service layer, formats responses. Not a cost driver."

        elif role == "retrieval":
            func_names = " ".join(functions).lower()
            if "hybrid" in func_names:
                description = "Implements hybrid search combining BM25 keyword matching with vector similarity. Core retrieval engine - major latency impact."
            elif "bm25" in func_names:
                description = (
                    "Implements BM25 keyword search. Contributes to retrieval latency."
                )
            elif "embed" in func_names:
                description = "Handles embedding generation for documents. Offline or part of ingestion pipeline."
            else:
                description = "Retrieval/search component. Likely impacts query latency in RAG pipelines."

        elif role == "orchestration":
            func_names = " ".join(functions).lower()
            if "query" in func_names or "rag" in func_names:
                description = "Central RAG orchestration. Coordinates retrieval → context → LLM → response. Highest cost and latency impact."

        return {
            "role": role,
            "is_hot_path": is_hot_path,
            "is_cost_sensitive": is_cost_sensitive,
            "is_cold_path": is_cold_path,
            "description": description,
        }

    def _generate_natural_description(
        self, filepath: str, purpose: str, classes: list, functions: list, imports: list
    ) -> str:
        """Generate natural language description for a Python file"""

        # Get role classification
        role_info = self._classify_file_role(
            filepath, purpose, classes, functions, imports
        )

        lines = []
        lines.append(f"### `{filepath}`")
        lines.append("")

        # Clean purpose
        clean_purpose = ""
        if purpose and purpose not in ["Python module", "JavaScript/TypeScript module"]:
            if "class(es)" in purpose:
                import re

                match = re.search(r"Defines (.+?) class\(es\)", purpose)
                if match:
                    clean_purpose = f"Defines {match.group(1)} classes. "
            elif "function(s)" in purpose:
                clean_purpose = "Provides utility functions. "
            elif "Main entry point" in purpose:
                clean_purpose = "Application entry point. "
            elif "Exports:" in purpose:
                clean_purpose = "Exports components. "
            elif not any(x in purpose.lower() for x in ["tracing", "tracer", "module"]):
                clean_purpose = f"{purpose.rstrip('.')}. "

        # Build description
        description = clean_purpose + role_info["description"]

        # Add risk indicators
        if role_info["is_cost_sensitive"]:
            description += " **High cost risk.**"
        elif role_info["is_hot_path"] and not role_info["is_cost_sensitive"]:
            description += " **Latency-sensitive.**"
        elif role_info["is_cold_path"]:
            description += " **Cold path - not in runtime query path.**"

        lines.append(description)
        lines.append("")

        return "\n".join(lines)

    def _generate_executive_summary(
        self,
        project_desc: dict,
        primary_language: str,
        file_summaries: dict,
        config_info: dict,
    ) -> str:
        """Generate decision-oriented executive summary"""

        arch_pattern = project_desc.get("architecture_pattern", "")
        features = project_desc.get("key_features", [])

        # Analyze characteristics
        has_rag = any("rag" in str(f).lower() for f in features)
        has_api = arch_pattern and "api" in arch_pattern.lower()
        has_docker = config_info.get("docker")
        has_cicd = config_info.get("ci_cd")

        py_files = [f for f in file_summaries.keys() if f.endswith(".py")]

        # Build summary
        sentences = []

        # Maturity
        maturity = []
        if has_api and has_rag:
            maturity.append("production-ready RAG backend")
        if has_docker:
            maturity.append("containerized")
        if has_cicd:
            maturity.append("CI/CD equipped")

        if maturity:
            sentences.append(f"{' / '.join(maturity).capitalize()} system")

        # Architecture
        if arch_pattern:
            sentences.append(f"architecture: {arch_pattern}")

        # Stack
        deps = []
        for v in project_desc.values():
            v_str = str(v).lower()
            if "groq" in v_str and "Groq" not in deps:
                deps.append("Groq")
            if "qdrant" in v_str and "Qdrant" not in deps:
                deps.append("Qdrant")
            if "fastapi" in v_str and "FastAPI" not in deps:
                deps.append("FastAPI")

        if deps:
            sentences.append(f"stack: {', '.join(deps)}")

        # Cost warning
        if has_rag:
            sentences.append("cost-sensitive due to external LLM calls")

        # Concerns
        backend_files = [f for f in py_files if "/backend/" in f.replace("\\", "/")]
        script_files = [f for f in py_files if "/scripts/" in f.replace("\\", "/")]

        concerns = []
        if len(backend_files) > 3 and len(script_files) > 3:
            concerns.append("duplication between backend/ and scripts/")

        if concerns:
            sentences.append(f"watch: {', '.join(concerns)}")

        doc = "## Executive Summary\n\n"
        if sentences:
            # Capitalize first letter of first sentence
            summary_text = ". ".join(sentences)
            doc += summary_text[0].upper() + summary_text[1:] + ".\n\n"
        else:
            doc += "Analysis complete.\n\n"

        return doc

    def _generate_maturity_score(
        self,
        file_summaries: dict,
        config_info: dict,
        dependencies: dict,
        primary_language: str,
    ) -> str:
        """Generate architectural maturity score (0-10)"""

        score = 0.0
        max_score = 10.0
        factors = []

        py_files = [f for f in file_summaries.keys() if f.endswith(".py")]

        # Layer separation (max 2)
        has_routers = any("/routers/" in f.replace("\\", "/") for f in py_files)
        has_models = any("/models/" in f.replace("\\", "/") for f in py_files)
        has_services = any("/services/" in f.replace("\\", "/") for f in py_files)
        layer_count = sum([has_routers, has_models, has_services])
        if layer_count >= 2:
            score += 2
            factors.append("Layer separation: Good")
        elif layer_count >= 1:
            score += 1
            factors.append("Layer separation: Partial")
        else:
            factors.append("Layer separation: None")

        # Docker presence (max 1)
        if config_info.get("docker"):
            score += 1
            factors.append("Docker: Present")

        # Tests presence (max 1.5)
        test_files = [f for f in py_files if "test" in f.lower()]
        if len(test_files) >= 3:
            score += 1.5
            factors.append(f"Tests: {len(test_files)} files")
        elif len(test_files) > 0:
            score += 0.5
            factors.append(f"Tests: Minimal ({len(test_files)})")
        else:
            factors.append("Tests: None detected")

        # Linting/Quality tools (max 1)
        if config_info.get("lint") or config_info.get("formatter"):
            score += 1
            factors.append("Code quality tools: Present")

        # CI/CD (max 1)
        if config_info.get("ci_cd"):
            score += 1
            factors.append("CI/CD: Present")

        # Documentation (max 1)
        readme = config_info.get("readme", False)
        docs = config_info.get("docs", [])
        if readme or len(docs) >= 2:
            score += 1
            factors.append("Documentation: Good")
        elif len(docs) > 0:
            score += 0.5
            factors.append("Documentation: Minimal")

        # Observability (max 1)
        obs_keywords = [
            "tracing",
            "logging",
            "metrics",
            "monitoring",
            "langsmith",
            "prometheus",
        ]
        obs_count = sum(1 for f in py_files for kw in obs_keywords if kw in f.lower())
        if obs_count >= 2:
            score += 1
            factors.append("Observability: Good")
        elif obs_count > 0:
            score += 0.5
            factors.append("Observability: Partial")

        # Dependency hygiene (max 1.5)
        dep_count = sum(len(deps) for deps in dependencies.values())
        if dep_count < 30:
            score += 1.5
            factors.append(f"Dependencies: Manageable ({dep_count})")
        elif dep_count < 50:
            score += 1
            factors.append(f"Dependencies: Moderate ({dep_count})")
        else:
            factors.append(f"Dependencies: High ({dep_count})")

        # Calculate confidence (based on how many factors we could evaluate)
        confidence = min(0.95, 0.5 + (len(factors) / 10) * 0.5)

        doc = "## Architectural Maturity\n\n"
        doc += (
            f"**Score: {score:.1f} / {max_score}** (Confidence: {confidence:.2f})\n\n"
        )
        doc += "- " + "\n- ".join(factors) + "\n\n"

        # Verdict
        if score >= 8:
            verdict = "Production-grade. Well-structured for scale."
        elif score >= 6:
            verdict = "Development-ready. Some improvements recommended."
        elif score >= 4:
            verdict = "MVP stage. Significant work needed for production."
        else:
            verdict = "Early prototype. Not ready for production."

        doc += f"**Verdict**: {verdict}\n\n"

        return doc

    def _generate_risk_profile(self, file_summaries: dict, dependencies: dict) -> str:
        """Generate runtime risk profile"""

        py_files = list(file_summaries.keys())

        # Check for risk factors
        has_llm = any(
            "groq" in str(v).lower() or "openai" in str(v).lower()
            for fs in file_summaries.values()
            for v in fs.values()
        )
        has_vector = any(
            "qdrant" in str(v).lower() or "chroma" in str(v).lower()
            for fs in file_summaries.values()
            for v in fs.values()
        )
        has_retry = any("retry" in f.lower() for f in py_files)
        has_circuit_breaker = any("circuit" in f.lower() for f in py_files)

        # External services
        all_deps = [d for deps in dependencies.values() for d in deps]
        external_services = []
        for svc, keywords in [
            ("Groq", ["groq"]),
            ("OpenAI", ["openai"]),
            ("Qdrant", ["qdrant"]),
            ("LangSmith", ["langsmith"]),
        ]:
            if any(kw in str(all_deps).lower() for kw in keywords):
                external_services.append(svc)

        doc = "## Runtime Risk Profile\n\n"

        # Cost Risk
        doc += "### Cost Risk\n"
        if external_services:
            doc += f"- **External LLM calls**: Yes ({', '.join(external_services)})\n"
            doc += "- **Risk level**: Moderate to High\n"
            doc += "- **Recommendation**: Implement budget controls\n"
        else:
            doc += "- **External LLM calls**: No\n"
            doc += "- **Risk level**: Low\n"

        # Latency Risk
        doc += "\n### Latency Risk\n"
        if has_vector:
            doc += "- **Vector DB**: Yes (query latency dependency)\n"
        if has_llm:
            doc += "- **LLM inference**: Yes (network latency)\n"
        if has_retry:
            doc += "- **Retry logic**: Present\n"
        else:
            doc += "- **Retry logic**: Not detected\n"
        if has_circuit_breaker:
            doc += "- **Circuit breaker**: Present\n"

        # Scalability Risk
        doc += "\n### Scalability Risk\n"
        doc += f"- **Async support**: {'Detected' if any('async' in str(fs.get('functions', [])).lower() for fs in file_summaries.values()) else 'Not detected'}\n"
        doc += "- **Caching**: Not detected\n"

        doc += "\n"

        return doc

    def _generate_complexity_profile(
        self, files: List[str], file_summaries: dict, dependencies: dict
    ) -> str:
        """Generate complexity profile"""

        py_files = [f for f in files if f.endswith(".py")]
        js_files = [f for f in files if f.endswith((".js", ".jsx", ".ts", ".tsx"))]

        # Count internal imports
        internal_imports = 0
        for fs in file_summaries.values():
            imports = fs.get("imports", [])
            internal_imports += sum(
                1 for i in imports if not i.startswith("_") and "." in i
            )

        # External dependencies
        ext_deps = sum(len(deps) for deps in dependencies.values())

        doc = "## Complexity Profile\n\n"
        doc += f"- **Total files**: {len(files)}\n"
        doc += f"- **Python modules**: {len(py_files)}\n"
        doc += f"- **Frontend files**: {len(js_files)}\n"
        doc += f"- **Internal imports**: ~{internal_imports} (coupling)\n"
        doc += f"- **External dependencies**: {ext_deps}\n\n"

        # Assessment
        if len(py_files) < 20 and ext_deps < 30:
            complexity = "Low - manageable for small team"
        elif len(py_files) < 50 and ext_deps < 50:
            complexity = "Moderate - needs good documentation"
        else:
            complexity = "High - requires experienced team"

        doc += f"**Assessment**: {complexity}\n\n"

        return doc

    def _generate_engineering_hygiene(
        self, config_info: dict, file_summaries: dict
    ) -> str:
        """Generate engineering hygiene checklist"""

        py_files = [f for f in file_summaries.keys() if f.endswith(".py")]
        test_files = [f for f in py_files if "test" in f.lower()]
        has_tests = len(test_files) >= 1

        doc = "## Engineering Hygiene\n\n"

        checks = [
            ("Docker", config_info.get("docker"), "Containerization ready"),
            ("Tests", has_tests, f"Test coverage ({len(test_files)} files)"),
            ("CI/CD", config_info.get("ci_cd"), "Continuous integration"),
            ("Linting", config_info.get("lint"), "Code quality tools"),
            ("Type hints", config_info.get("type_check"), "Type safety"),
            (
                "Docs",
                config_info.get("readme") or config_info.get("docs"),
                "Documentation",
            ),
        ]

        for name, present, description in checks:
            status = "✔" if present else "✘"
            doc += f"- {status} **{name}**: {description}\n"

        doc += "\n"

        return doc

    def _generate_red_flags(
        self, file_summaries: dict, dependencies: dict, config_info: dict
    ) -> str:
        """Generate red flags / warnings"""

        py_files = [
            f.replace("\\", "/") for f in file_summaries.keys() if f.endswith(".py")
        ]

        flags = []

        # Check for duplication
        backend_retrieval = [
            f for f in py_files if "hybrid" in f.lower() and "/backend/" in f
        ]
        script_retrieval = [
            f for f in py_files if "hybrid" in f.lower() and "/scripts/" in f
        ]
        if backend_retrieval and script_retrieval:
            flags.append(
                f"Duplicate retrieval logic: found in both backend/ and scripts/"
            )

        # Check for utility files
        utility_count = sum(1 for f in py_files if "util" in f.lower())
        if utility_count > 5:
            flags.append(
                f"High number of utility files ({utility_count}) - consider consolidation"
            )

        # Check for missing observability
        obs_count = sum(
            1
            for f in py_files
            if any(x in f.lower() for x in ["tracing", "logging", "langsmith"])
        )
        if obs_count == 0 and len(py_files) > 10:
            flags.append(
                "No observability/tracing detected - runtime debugging will be difficult"
            )

        # Check for missing tests
        test_count = sum(1 for f in py_files if "test" in f.lower())
        if test_count == 0 and len(py_files) > 5:
            flags.append("No tests detected - risky for production")

        # Check for hardcoded secrets (heuristic)
        secrets_keywords = ["password", "api_key", "secret", "token"]
        # Note: This is just a warning, we'd need actual content analysis

        # Check for monolithic tendency
        main_files = [
            f for f in py_files if f.endswith("main.py") or f.endswith("__init__.py")
        ]
        if len(main_files) > 3:
            flags.append(
                f"Multiple entry points ({len(main_files)}) - may indicate unclear architecture"
            )

        doc = "## Red Flags\n\n"

        if flags:
            for flag in flags:
                doc += f"- ⚠️ {flag}\n"
        else:
            doc += "- ✅ No major issues detected\n"

        doc += "\n"

        return doc
