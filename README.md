# APRIS - Autonomous Public Repository Intelligence System

An AI-powered agent that analyzes GitHub repositories and provides decision-oriented summaries in seconds. Reduces code review time by ~98%.

## Project Description

APRIS (Autonomous Public Repository Intelligence System) is an enterprise-grade AI agent for analyzing GitHub repositories. Instead of spending hours reading code, users get instant insights:

- **Is this worth my time?**
- **Is it production-ready?**
- **What are the risks?**
- **What does it cost to run?**

### Key Features

- AI-generated repository summaries with LLM reasoning
- Architectural pattern detection (API-First, Layered, Microservices, etc.)
- Real dependency graph analysis with service layer identification
- Decision-oriented evaluation (Maturity Score, Risk Profile, Red Flags)
- Full LLM observability with Langfuse tracing

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        APRIS Workflow                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: Clone & Index                                         │
│  - GitHub API → Clone repo → Index files                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: Language Classification                                │
│  - Detect primary language (Python, JS, Go, Rust, etc.)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 3: Content Analysis (LLM)                                │
│  - Extract purpose, key features, tech stack                    │
│  - Analyze README, config files                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 4: AST Analysis                                           │
│  - Parse file structure, imports, classes, functions            │
│  - Multi-language support (Python, JS, Go, Rust)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 5: Dependency Graph Build                                 │
│  - Map internal imports → Service layers                         │
│  - Identify external integrations (GROQ, OpenAI, Qdrant, etc.)  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 6: Architecture Pattern Detection                         │
│  - API-First Backend, Layered, Microservices, Monolithic       │
│  - Confidence scoring                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 7: Data Flow Analysis                                     │
│  - Trace query path: User → API → LLM → Response                │
│  - Identify latency-sensitive components                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 8: Role Classification                                     │
│  - Classify files: Boundary, Orchestration, Retrieval, etc.     │
│  - Hot path vs cold path analysis                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 9: Executive Summary (LLM)                               │
│  - Decision-oriented paragraph                                   │
│  - Stack, maturity, risks                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 10: Maturity Scoring                                      │
│  - Score: Layer separation, tests, Docker, CI/CD, observability │
│  - 0-10 scale with confidence                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 11: Risk Profile                                          │
│  - Cost risk (external LLM calls)                                │
│  - Latency risk (vector DB, sync operations)                     │
│  - Scalability risk                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 12: Documentation Generation                              │
│  - Full markdown report with all sections                        │
│  - File analysis with role descriptions                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Final Output:     │
                    │ • Executive Summary │
                    │ • Maturity Score    │
                    │ • Risk Profile      │
                    │ • Red Flags         │
                    │ • File Analysis     │
                    └─────────────────────┘
```

---

## How It Works (Phase by Phase)

### Phase 1: Clone & Index
- Uses GitHub API to fetch repository contents
- Indexes all files for analysis

### Phase 2: Language Classification
- Detects primary language using file extensions
- Categories: Python, JavaScript/TypeScript, Go, Rust, etc.

### Phase 3: Content Analysis (LLM)
- Feeds repository context to LLM (GROQ)
- Extracts: purpose, key features, tech stack

### Phase 4: AST Analysis
- Parses source files to extract:
  - Classes, functions, imports
  - Dependencies between modules

### Phase 5: Dependency Graph Build
- Analyzes import relationships
- Identifies service layers (API, Database, Services)
- Maps external integrations

### Phase 6: Architecture Pattern Detection
- Detects patterns: API-First, Layered, Microservices, Monolithic
- Provides confidence score (0-5)

### Phase 7: Data Flow Analysis
- Traces query path through system
- Identifies hot paths and latency drivers

### Phase 8: Role Classification
- Classifies each file into architectural role:
  - **Boundary** (HTTP adapters)
  - **Orchestration** (service layer)
  - **Retrieval** (search/vector)
  - **Infrastructure** (DB/storage init)
  - **Offline Pipeline** (scripts)

### Phase 9: Executive Summary (LLM)
- Generates decision-oriented summary
- Answers: "Should I use this?"

### Phase 10: Maturity Scoring
- Scores architecture on 0-10 scale
- Factors: layer separation, tests, Docker, CI/CD, observability

### Phase 11: Risk Profile
- **Cost Risk**: External LLM calls, integrations
- **Latency Risk**: Vector DB, sync operations
- **Scalability Risk**: Async support, caching

### Phase 12: Documentation Generation
- Compiles full markdown report
- Includes per-file role descriptions

---

## Evaluation Metrics

### Traditional Code Review vs APRIS

| Metric | Manual Review | APRIS |
|--------|--------------|-------|
| **Time to Decision** | 2-4 hours | ~3 minutes |
| **Reading Time** | ~8-12 hours (thorough) | ~3 minutes |
| **Time Saved** | - | **~98%** |

### Output Quality Metrics

| Aspect | Description |
|--------|-------------|
| **Architecture Detection** | 5/5 confidence for API-First patterns |
| **Role Classification** | Correctly identifies Boundary vs Orchestration vs Infrastructure |
| **Maturity Scoring** | 0-10 scale with confidence interval |
| **Risk Identification** | Cost, Latency, Scalability assessments |

### Sample Analysis Results

**Repository**: Malaria-RAG-system (77 files)

| Metric | Value |
|--------|-------|
| **Maturity Score** | 7.0 / 10.0 |
| **Confidence** | 0.75 |
| **Layer Separation** | Good |
| **Tests** | 5 files |
| **External Dependencies** | 22 (manageable) |

**Repository**: mcp-agent-dashboard (55 files)

| Metric | Value |
|--------|-------|
| **Maturity Score** | 3.0 / 10.0 |
| **Confidence** | 0.75 |
| **Layer Separation** | None |
| **Tests** | None detected |
| **External Dependencies** | 9 (manageable) |

---

## Langfuse Tracing Metrics

APRIS integrates with Langfuse for full LLM observability.

### Current Metrics

```
Generation latency percentiles
Generation Name    p50     p90     p95     p99
ChatGroq          0.79s   1.78s   1.99s   2.15s

Token Usage
- Tokens per call: ~934
- Cost: $0 (GROQ free tier)
```

### What's Tracked

- **Model**: llama-3.3-70b-versatile (GROQ)
- **Latency**: Full generation time
- **Tokens**: Input + output tokens
- **Traces**: Each LLM call during analysis

---

## Example Query and Summary Response

### Input

```bash
python test_repo_example.py https://github.com/dicksarp09/Malaria-RAG-system
```

### Summary Response

```
## Executive Summary

Containerized system. stack: Qdrant, FastAPI, Groq. cost-sensitive due to 
external LLM calls.

## Architectural Maturity

**Score: 7.0 / 10.0** (Confidence: 0.75)

- Layer separation: Good
- Docker: Present
- Tests: 5 files
- Observability: Good
- Dependencies: Manageable (22)

**Verdict**: Development-ready. Some improvements recommended.

## Runtime Risk Profile

### Cost Risk
- External LLM calls: Yes (Groq, Qdrant, LangSmith)
- Risk level: Moderate to High
- Recommendation: Implement budget controls

### Latency Risk
- Vector DB: Yes (query latency dependency)
- LLM inference: Yes (network latency)
- Retry logic: Not detected

## Complexity Profile

- Total files: 77
- Python modules: 33
- Assessment: Moderate - needs good documentation

## Engineering Hygiene

- ✔ Docker: Containerization ready
- ✔ Tests: Test coverage (5 files)
- ✘ CI/CD: Continuous integration
- ✘ Linting: Code quality tools
- ✘ Type hints: Type safety
- ✘ Docs: Documentation

## Red Flags

- ⚠️ Multiple entry points (4) - may indicate unclear architecture

## Code File Analysis

### `backend/main.py`

Defines QueryRequest, ChunkMetadata, QueryResponse classes. Application entry point. 
Initializes components and starts the server.

### `backend/hybrid_retrieval.py`

Defines BM25Index, HybridRetriever classes. Retrieval/search component. 
Likely impacts query latency in RAG pipelines. **Latency-sensitive.**

### `backend/routers/query.py`

HTTP adapter layer. Parses requests, calls service layer, formats responses. 
Not a cost driver. **Latency-sensitive.**
```

---

## Tech Stack

- **LLM**: GROQ (llama-3.3-70b-versatile)
- **Framework**: LangGraph (workflow orchestration)
- **Tracing**: Langfuse + LangChain
- **Storage**: SQLite (audit logs)
- **Language**: Python

## Environment Variables

```bash
GROQ_API_KEY=your_groq_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
GITHUB_TOKEN=your_github_token
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run analysis
python test_repo_example.py https://github.com/owner/repo
```

---

## License

MIT
