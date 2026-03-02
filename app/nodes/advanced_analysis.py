import ast
import os
import random
from typing import Dict, Any, List, Optional, Set, Tuple
from app.graph.state import WorkflowState


class ComplexityAnalyzer:
    def __init__(self):
        self.sample_size_ratio = 0.1

    def analyze_complexity(self, state: WorkflowState) -> Dict[str, Any]:
        repo_metadata = state.get("repo_metadata", {})
        repo_path = repo_metadata.get("local_path", "")

        if not repo_path or not os.path.exists(repo_path):
            return {"error": "Repository path not found"}

        python_files = self._find_python_files(repo_path)

        if not python_files:
            return {"error": "No Python files found"}

        sample_size = max(1, int(len(python_files) * self.sample_size_ratio))
        sampled_files = random.sample(python_files, min(sample_size, len(python_files)))

        complexities = []
        file_complexities = {}

        for file_path in sampled_files:
            try:
                complexity = self._calculate_complexity(file_path)
                file_complexities[os.path.basename(file_path)] = complexity
                complexities.append(complexity)
            except Exception:
                continue

        if not complexities:
            return {"error": "Could not analyze any files"}

        avg_complexity = sum(complexities) / len(complexities)
        max_complexity = max(complexities)
        min_complexity = min(complexities)

        complexity_profile = {
            "avg_complexity": round(avg_complexity, 2),
            "max_complexity": max_complexity,
            "min_complexity": min_complexity,
            "files_analyzed": len(complexities),
            "total_python_files": len(python_files),
            "sample_ratio": round(len(complexities) / len(python_files), 2)
            if python_files
            else 0,
            "file_details": file_complexities,
            "risk_level": self._assess_risk(avg_complexity),
        }

        return complexity_profile

    def _find_python_files(self, repo_path: str) -> List[str]:
        python_files = []
        for root, _, files in os.walk(repo_path):
            if "__pycache__" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    python_files.append(os.path.join(root, f))
        return python_files

    def _calculate_complexity(self, file_path: str) -> int:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
            visitor = ComplexityVisitor()
            visitor.visit(tree)
            return visitor.complexity
        except SyntaxError:
            return 1

    def _assess_risk(self, avg_complexity: float) -> str:
        if avg_complexity < 5:
            return "low"
        elif avg_complexity < 10:
            return "moderate"
        elif avg_complexity < 15:
            return "high"
        else:
            return "critical"


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Try(self, node):
        self.complexity += len(node.handlers)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)


class DependencyGraphAnalyzer:
    def __init__(self):
        self.allowed_dependencies = {
            "routers": ["services", "models", "schemas", "utils"],
            "services": ["models", "schemas", "database", "utils", "memory"],
            "models": ["schemas", "utils"],
            "schemas": ["utils"],
            "database": [],
            "utils": [],
            "memory": ["database", "utils"],
            "agents": ["services", "models", "memory", "utils"],
            "nodes": ["agents", "services", "models", "memory", "utils"],
            "graph": ["nodes", "agents", "services", "memory"],
            "security": ["database", "models"],
            "governance": ["database", "security"],
            "observability": [],
            "config": [],
            "api": ["routers", "services", "models"],
        }

    def analyze_dependency_graph(self, state: WorkflowState) -> Dict[str, Any]:
        repo_metadata = state.get("repo_metadata", {})
        repo_path = repo_metadata.get("local_path", "")

        if not repo_path or not os.path.exists(repo_path):
            return {"error": "Repository path not found"}

        import_graph = self._build_import_graph(repo_path)

        density = self._calculate_density(import_graph)
        has_cycles = self._has_cycles(import_graph)
        layer_violations = self._detect_layer_violations(import_graph)

        return {
            "density": density,
            "has_cycles": has_cycles,
            "layer_violations": layer_violations,
            "total_modules": len(import_graph),
            "total_edges": sum(len(deps) for deps in import_graph.values()),
            "risk_assessment": self._assess_dependency_risk(
                density, has_cycles, layer_violations
            ),
        }

    def _build_import_graph(self, repo_path: str) -> Dict[str, Set[str]]:
        import_graph: Dict[str, Set[str]] = {}

        for root, _, files in os.walk(repo_path):
            if "__pycache__" in root or ".git" in root or "node_modules" in root:
                continue

            for file in files:
                if not file.endswith(".py") or file.startswith("__"):
                    continue

                file_path = os.path.join(root, file)
                module_name = self._get_module_name(repo_path, root, file)

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    imports = self._extract_imports(content)
                    import_graph[module_name] = imports
                except Exception:
                    continue

        return import_graph

    def _get_module_name(self, repo_path: str, root: str, file: str) -> str:
        rel_path = os.path.relpath(root, repo_path)
        if rel_path == ".":
            module = file[:-3]
        else:
            module = os.path.join(rel_path.replace(os.sep, "."), file[:-3])
        return module

    def _extract_imports(self, content: str) -> Set[str]:
        imports = set()

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
        except SyntaxError:
            pass

        return imports

    def _calculate_density(self, import_graph: Dict[str, Set[str]]) -> float:
        if not import_graph:
            return 0.0

        modules = len(import_graph)
        edges = sum(len(deps) for deps in import_graph.values())

        max_edges = modules * (modules - 1)

        if max_edges == 0:
            return 0.0

        return round(edges / max_edges, 4)

    def _has_cycles(self, import_graph: Dict[str, Set[str]]) -> bool:
        def dfs(node: str, visited: Set[str], stack: Set[str]) -> bool:
            if node in stack:
                return True
            if node in visited:
                return False

            visited.add(node)
            stack.add(node)

            for neighbor in import_graph.get(node, set()):
                if dfs(neighbor, visited, stack):
                    return True

            stack.remove(node)
            return False

        visited = set()
        for node in import_graph:
            if node not in visited:
                if dfs(node, visited, set()):
                    return True

        return False

    def _detect_layer_violations(
        self, import_graph: Dict[str, Set[str]]
    ) -> List[Dict[str, str]]:
        violations = []

        for module, imports in import_graph.items():
            source_layer = self._get_layer(module)

            if not source_layer:
                continue

            allowed = self.allowed_dependencies.get(source_layer, [])

            for imported in imports:
                target_layer = self._get_layer(imported)

                if target_layer and target_layer not in allowed:
                    violations.append(
                        {
                            "source": module,
                            "target": imported,
                            "source_layer": source_layer,
                            "target_layer": target_layer,
                            "violation": f"{source_layer} should not import from {target_layer}",
                        }
                    )

        return violations

    def _get_layer(self, module: str) -> Optional[str]:
        module_lower = module.lower()

        layers = [
            "routers",
            "services",
            "models",
            "schemas",
            "database",
            "utils",
            "memory",
            "agents",
            "nodes",
            "graph",
            "security",
            "governance",
            "observability",
            "config",
            "api",
        ]

        for layer in layers:
            if layer in module_lower:
                return layer

        return None

    def _assess_dependency_risk(
        self, density: float, has_cycles: bool, layer_violations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        risk_score = 0
        risk_factors = []

        if density > 0.3:
            risk_score += 3
            risk_factors.append("High coupling density")
        elif density > 0.1:
            risk_score += 1

        if has_cycles:
            risk_score += 4
            risk_factors.append("Circular dependencies detected")

        violation_count = len(layer_violations)
        if violation_count > 5:
            risk_score += 3
            risk_factors.append(f"Multiple layer violations ({violation_count})")
        elif violation_count > 0:
            risk_score += 1

        if risk_score >= 7:
            risk_level = "critical"
        elif risk_score >= 4:
            risk_level = "high"
        elif risk_score >= 2:
            risk_level = "moderate"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
        }


class ArchitectureScorer:
    def __init__(self):
        self.complexity_analyzer = ComplexityAnalyzer()
        self.dep_analyzer = DependencyGraphAnalyzer()

    def calculate_architecture_score(self, state: WorkflowState) -> Dict[str, Any]:
        complexity_result = self.complexity_analyzer.analyze_complexity(state)
        dep_result = self.dep_analyzer.analyze_dependency_graph(state)

        maturity_score = self._calculate_maturity_score(state)
        risk_profile = self._calculate_risk_profile(complexity_result, dep_result)

        overall_score = self._calculate_overall_score(
            maturity_score, complexity_result, dep_result
        )

        return {
            "architecture_score": overall_score,
            "maturity_score": maturity_score,
            "complexity_profile": complexity_result,
            "dependency_profile": dep_result,
            "risk_profile": risk_profile,
        }

    def _calculate_maturity_score(self, state: WorkflowState) -> Dict[str, Any]:
        score = 0.0
        max_score = 10.0
        factors = []

        file_index = state.get("file_index", [])
        python_files = [f for f in file_index if f.endswith(".py")]

        has_docker = any("docker" in f.lower() for f in file_index)
        has_tests = any("test" in f.lower() for f in file_index)
        has_readme = any("readme" in f.lower() for f in file_index)
        has_requirements = any(
            "requirements" in f.lower() or "pyproject" in f.lower() for f in file_index
        )

        has_ci = any(
            "github/workflows" in f or "gitlab-ci" in f or ".github" in f
            for f in file_index
        )

        has_type_hints = False
        for pf in python_files[:10]:
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    content = f.read()
                    if (
                        ": str" in content
                        or ": int" in content
                        or ": Dict" in content
                        or ": List" in content
                    ):
                        has_type_hints = True
            except:
                pass

        layer_separation = len([f for f in file_index if "/" in f])

        if has_docker:
            score += 1.5
            factors.append("Docker present (+1.5)")

        if has_tests:
            score += 1.5
            factors.append("Test coverage (+1.5)")

        if has_readme:
            score += 1.0
            factors.append("Documentation (+1.0)")

        if has_requirements:
            score += 1.0
            factors.append("Dependency manifest (+1.0)")

        if has_ci:
            score += 1.5
            factors.append("CI/CD pipeline (+1.5)")

        if has_type_hints:
            score += 1.0
            factors.append("Type hints (+1.0)")

        if layer_separation > 3:
            score += 1.5
            factors.append(f"Layer separation ({layer_separation} dirs, +1.5)")

        if len(python_files) > 0:
            score += 1.0
            factors.append("Python modules (+1.0)")

        confidence = min(1.0, len(python_files) / 20.0)

        return {
            "score": round(score, 1),
            "max_score": max_score,
            "confidence": round(confidence, 2),
            "factors": factors,
            "verdict": "Production-ready"
            if score >= 7
            else "Development-ready"
            if score >= 5
            else "Needs improvement",
        }

    def _calculate_risk_profile(
        self, complexity_result: Dict[str, Any], dep_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        cost_risk = "low"
        latency_risk = "low"
        scalability_risk = "low"

        if dep_result.get("has_cycles"):
            scalability_risk = "high"

        complexity_risk = complexity_result.get("risk_level", "low")

        return {
            "cost_risk": cost_risk,
            "latency_risk": latency_risk,
            "scalability_risk": scalability_risk,
            "complexity_risk": complexity_risk,
            "overall_risk": max(
                ["low", "moderate", "high", "critical"].index(complexity_risk),
                ["low", "moderate", "high", "critical"].index(scalability_risk),
            ),
        }

    def _calculate_overall_score(
        self,
        maturity: Dict[str, Any],
        complexity: Dict[str, Any],
        dependencies: Dict[str, Any],
    ) -> float:
        maturity_score = maturity.get("score", 5.0)

        complexity_penalty = 0
        if complexity.get("avg_complexity", 0) > 10:
            complexity_penalty = 1.5
        elif complexity.get("avg_complexity", 0) > 5:
            complexity_penalty = 0.5

        dependency_penalty = 0
        if dependencies.get("has_cycles"):
            dependency_penalty += 2
        dependency_penalty += len(dependencies.get("layer_violations", [])) * 0.2

        risk = dependencies.get("risk_assessment", {})
        if risk.get("risk_level") == "critical":
            dependency_penalty += 2
        elif risk.get("risk_level") == "high":
            dependency_penalty += 1

        overall = max(0, maturity_score - complexity_penalty - dependency_penalty)

        return round(overall, 1)


def analyze_architecture(state: WorkflowState) -> Dict[str, Any]:
    scorer = ArchitectureScorer()
    return scorer.calculate_architecture_score(state)
