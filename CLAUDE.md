# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

```bash
cp .env.example .env   # fill in NVIDIA_API_KEY and TAVILY_API_KEY
pip install -r requirements.txt
```

Required `.env` variables:
- `NVIDIA_API_KEY` — NVIDIA NIM API key (nvapi-...)
- `TAVILY_API_KEY` — Tavily web search key
- `LLM_MODEL` — default `meta/llama-3.1-8b-instruct`
- `NVIDIA_BASE_URL` — default `https://integrate.api.nvidia.com/v1`
- `AT_RISK_THRESHOLD` — default `75.0` (attendance % below which a student is flagged at-risk)

## Running the Notebook

```bash
source .venv/bin/activate
jupyter notebook Excelsis.ipynb
```

Run cells **in order** (1 → 10). The `store` and `_agent` globals must be initialised before calling `ask()`.

After loading data in Cell 6, call `vec.index_store_summaries(store)` once to make class summaries searchable via the vector DB.

## Running the MCP Server (for Claude Code)

```bash
source .venv/bin/activate
python -m src.mcp_server
```

Claude Code auto-starts this via `.claude/settings.json`. Loads data from `data/attendance/` and exposes 7 tools to Claude.

## Architecture

### Notebook cell map

| Cell | Purpose |
|------|---------|
| 1 | Dependency install (includes `chromadb`, `langchain-chroma`, `mcp`) |
| 2 | Load `.env`, initialise environment variables |
| 3a | Register `src/` on `sys.path` |
| 3 | `AttendanceDataStore` — ingests CSV/Excel/Parquet, computes stats |
| 4 | Dashboard builder — Plotly interactive + matplotlib/seaborn static |
| 5 | **Llama ReAct agent** — `ask()` entry point, ChromaDB vector store, `CURRENT_USER` security context |
| 6 | Sample data generator (180-day school year, 6 classes, ~30 students each) |
| 7 | Static matplotlib dashboard |
| 8–10 | Example `ask()` calls |

### Module map (`src/`)

```
src/
├── security.py      # RBAC: Role, Permission, UserContext, SecurityManager
├── data_store.py    # AttendanceDataStore, parse_attendance_query
├── vector_store.py  # AttendanceVectorStore (ChromaDB + NVIDIA embeddings)
├── tools.py         # LangGraph tool definitions (5 tools)
├── agent.py         # ExcelsisAgent — LangGraph ReAct agent
└── mcp_server.py    # FastMCP server exposing tools to Claude Code
```

### Security model (`src/security.py`)

Permissions are enforced at two levels simultaneously:

1. **Tool level** — `SecurityManager.require(user, Permission.X)` raises `AccessDeniedError` before any computation runs
2. **Data level** — `SecurityManager.filter_df(df, user)` strips rows the user cannot see, based on `user.allowed_classes`

| Role | Can query own classes | At-risk list | Web search | Ingest data | Audit log |
|------|----------------------|--------------|------------|-------------|-----------|
| `admin` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `counselor` | ✓ | ✓ | ✓ | — | — |
| `teacher` | ✓ | — | — | — | — |
| `viewer` | ✓ | — | — | — | — |

`allowed_classes` on a `UserContext` further restricts which class rows are returned, enforced at the pandas DataFrame level.

### LangGraph ReAct agent (`src/agent.py`)

Replaces keyword routing with a real reasoning loop: the LLM decides which tools to call, in what order, and synthesises a final answer. User context is passed via `RunnableConfig["configurable"]["user_context"]` — tools read it from there, so security applies to every step of the agent's reasoning.

Available tools: `query_attendance`, `get_at_risk_students`, `search_knowledge_base`, `get_summary`, `web_search`.

### Vector store (`src/vector_store.py`)

ChromaDB with two collections:
- `policies` — 5 seeded best-practice documents + any custom policy docs. No auth required.
- `attendance_summaries` — per-class summaries indexed by `index_store_summaries(store)`. `search_records()` accepts `allowed_classes` and passes it as a ChromaDB `$in` metadata filter, so the database itself enforces access scope.

Embeddings: `nvidia/nv-embedqa-e5-v5` via NVIDIA NIM. Persisted to `data/chroma_db/`.

### MCP server (`src/mcp_server.py`)

FastMCP stdio server. Claude Code connects via `.claude/settings.json`. User identity is set at process start via env vars (`MCP_USER_ID`, `MCP_USER_ROLE`, `MCP_ALLOWED_CLASSES`). For multi-user deployments, start one process per user with different `MCP_USER_*` values, or use `EXCELSIS_TOKENS` for a token registry.

Exposed tools: `ask_analyst`, `attendance_summary`, `at_risk_students`, `class_statistics`, `search_policies`, `search_attendance_records`, `audit_log`.

### Dashboard outputs

- **Interactive (Plotly)**: `build_dashboard(chart_type, df, title, group_col)` — HTML saved to `data/dashboards/`
- **Static (matplotlib/seaborn)**: `build_modern_static_dashboard(store)` — PNG saved to `data/dashboards/attendance_dashboard_modern.png`

### Data directory

`data/attendance/` — drop CSV/Excel/Parquet files here; reload with `AttendanceDataStore(data_path="data/attendance")`.  
`data/chroma_db/` — ChromaDB persistent storage (auto-created).  
`data/dashboards/` — generated HTML and PNG outputs.
