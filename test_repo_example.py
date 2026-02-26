#!/usr/bin/env python
"""
APRIS - Autonomous Public Repository Intelligence System
Example test script to analyze repositories
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

from app.graph.workflow import get_workflow_engine


def analyze_repo(repo_url: str):
    """Analyze a GitHub repository and print results"""
    engine = get_workflow_engine()

    print(f"\n{'=' * 60}")
    print(f"Analyzing: {repo_url}")
    print("=" * 60)

    # Run workflow
    result = engine.run_workflow(f"test-{hash(repo_url)}", repo_url)

    # Extract results
    project_desc = result.get("project_description", {})
    file_count = len(result.get("file_index", []))
    classification = result.get("classification", "unknown")

    print(f"\n[+] Classification: {classification}")
    print(f"[+] Files indexed: {file_count}")

    print(f"\n{'=' * 40}")
    print("PROJECT PURPOSE")
    print("=" * 40)
    print(project_desc.get("purpose", "N/A"))

    features = project_desc.get("key_features", [])
    if features:
        print(f"\n{'=' * 40}")
        print("KEY FEATURES")
        print("=" * 40)
        for f in features[:6]:
            clean = f.strip().lstrip("-•*").strip()
            if len(clean) > 5:
                print(f"  • {clean[:100]}")

    tech_stack = project_desc.get("tech_stack", [])
    if tech_stack:
        print(f"\n{'=' * 40}")
        print("TECH STACK")
        print("=" * 40)
        print(", ".join(tech_stack[:12]))

    # Full documentation
    print(f"\n{'=' * 40}")
    print("FULL DOCUMENTATION")
    print("=" * 40)
    print(result.get("documentation", "N/A"))

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Run a quick test to generate Langfuse traces
        print("Running quick test to generate Langfuse traces...")

        # Import and test Langfuse directly
        from app.agents.analysis_agent import (
            _langfuse_handler,
            _langfuse_client,
            _langchain_model,
        )
        from langchain_core.messages import HumanMessage

        if _langchain_model and _langfuse_handler:
            print("Using LangChain + Langfuse for full tracing...")

            # Make a test call
            response = _langchain_model.invoke(
                [HumanMessage(content="Say hello for Langfuse tracing test")],
                config={"callbacks": [_langfuse_handler]},
            )

            print(f"Response: {response.content}")
            print("\nCheck Langfuse dashboard for traces!")

            # Flush
            if _langfuse_client:
                _langfuse_client.flush()
        else:
            print("LangChain or Langfuse not available")
            print("Falling back to default repos...")

            repos = [
                "https://github.com/dicksarp09/Deploy-STT-Gateway-API-",
                "https://github.com/dicksarp09/Deepseek-OCR-PaddleOCR-endpoints",
            ]
            for repo in repos:
                analyze_repo(repo)
                print("\n")
    else:
        # Analyze user-provided repo
        repo_url = sys.argv[1]
        analyze_repo(repo_url)
