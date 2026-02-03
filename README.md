# ⚡ Agentic Workflow Engine

A schema-driven workflow orchestration engine for AI applications.

**[Live Demo →](https://agentic-workflow-engine.streamlit.app)**

## What This Demonstrates

This portfolio project showcases production-grade agentic AI engineering:

### 🚀 Practical Value
- **Multi-step workflow automation** — Chain HTTP requests, data transforms, and LLM calls
- **Real API integrations** — arXiv, Wikipedia, and more
- **Error handling** — Retries, timeouts, and graceful fallbacks

### 🔍 Technical Breadth
- **Tool calling** — Modular action registry with typed inputs/outputs
- **LLM orchestration** — Integrate language models into workflows
- **DAG execution** — Topological ordering with dependency resolution

### 🏗️ Engineering Depth
- **Schema validation** — JSON Schema-based input/output contracts
- **Deterministic execution** — Reproducible workflow runs
- **Observability** — Detailed execution logs and metrics

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Streamlit UI                       │
├─────────────────────────────────────────────────────┤
│  Run Workflows  │  How It Works  │  Architecture    │
├─────────────────────────────────────────────────────┤
│                 Executor Wrapper                     │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Runner    │  │  Registry   │  │   Actions   │ │
│  │   (DAG)     │  │  (Schemas)  │  │  (Handlers) │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Featured Workflows

| Workflow | Description | Actions Used |
|----------|-------------|--------------|
| **arXiv Search** | Search academic papers | HTTP GET → XML Transform |
| **Wiki Summary** | Wikipedia lookup | HTTP GET → JQ Transform |
| **Error Recovery** | Retry demonstration | HTTP GET with retries |

## Running Locally

```bash
# Clone
git clone https://github.com/vandyand/agentic-workflow-engine.git
cd agentic-workflow-engine

# Install
pip install -r requirements.txt

# Run
streamlit run app.py
```

## Tech Stack

- **UI:** Streamlit
- **Workflow Engine:** Custom Python runner with DAG execution
- **Visualization:** Graphviz
- **Caching:** JSON file-based with fallback

## About

Built by [Andrew VanDyke](https://github.com/vandyand) as a portfolio demonstration of agentic AI systems engineering.

This is a standalone extraction from a larger [Autonomous Digital Company](https://github.com/vandyand) project exploring schema-driven AI automation.
