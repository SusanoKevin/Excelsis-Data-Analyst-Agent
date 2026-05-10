# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Environment Setup

```bash
ollama pull qwen2.5-coder:7b && ollama pull llama3.1:8b && ollama pull nomic-embed-text
cp .env.example .env   # TAVILY_API_KEY optional; no LLM API key required
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && cd ..
```

Ollama must be running on `http://localhost:11434` before starting the stack.

Required `.env` variables:
- `JWT_SECRET` — must be changed from the default before any production use

Key optional variables:
- `TAVILY_API_KEY` — enables the `web_search` agent tool
- `ANALYSIS_MODEL` — default `qwen2.5-coder:7b`; drives the ReAct agent with tool calling
- `CHAT_MODEL` — default `llama3.1:8b`; handles lightweight conversational replies
- `EMBED_MODEL` — default `nomic-embed-text`; Ollama embedding model used by ChromaDB
- `AT_RISK_THRESHOLD` — default `75.0`
- `ADMIN_PASSWORD` — default `admin123`; sets the initial admin password on first run

## Running the Stack

```bash
bash start.sh          # FastAPI :8000 + React :5173
```

Or individually:
```bash
source .venv/bin/activate
uvicorn api.main:app --reload          # backend only
cd web && npm run dev                  # frontend only
```

Interactive API docs: `http://localhost:8000/docs`

## Jupyter Notebook

```bash
source .venv/bin/activate
jupyter notebook Excelsis.ipynb
```

Run cells in order (1 → 10). After Cell 6 loads data, call `vec.index_store_summaries(store)` once to populate the vector DB. To change the analyst identity, edit `CURRENT_USER` in Cell 5.

## Architecture

### Request flow

Browser → React (`web/`) → FastAPI (`api/`) → `ExcelsisAgent` (`src/agent.py`) → LangGraph ReAct loop → tools (`src/tools.py`) → `AttendanceDataStore` / `AttendanceVectorStore` / Tavily

The `/chat/stream` endpoint uses SSE (`StreamingResponse`); the frontend consumes `on_chat_model_stream`, `on_tool_start`, and `on_tool_end` events from LangGraph's `astream_events`.

### Security — two-layer enforcement (`src/security.py`)

Every data access passes through `SecurityManager` twice:
1. **Tool level** — `security.require(user, Permission.X)` raises `AccessDeniedError` before computation runs
2. **Data level** — `security.filter_df(df, user)` strips rows outside `user.allowed_classes` from the returned DataFrame

`UserContext` (user_id, role, allowed_classes) flows from JWT → `api/deps.py` → FastAPI Depends → `RunnableConfig["configurable"]["user_context"]` → every LangGraph tool. Tools read it via `config.get("configurable", {}).get("user_context", ADMIN_USER)`.

Role → permission mapping lives in `ROLE_PERMISSIONS` in `security.py`. Teachers get `READ_OWN_CLASSES` + `GENERATE_DASHBOARD` only; the `READ_AT_RISK` and `WEB_SEARCH` permissions require counselor or above.

### User management (`api/auth.py` + `api/users.json`)

Users are stored as bcrypt-hashed records in `api/users.json`. On startup, `ensure_default_admin()` creates the admin account if missing. JWTs embed `sub`, `role`, and `allowed_classes`; `decode_token()` reconstructs a `UserContext` from them. Token TTL is 24 hours.

### Vector store (`src/vector_store.py`)

Two ChromaDB collections persisted to `data/chroma_db/`:
- `policies` — 5 seeded best-practice documents, seeded once on first `AttendanceVectorStore()` init
- `attendance_summaries` — per-class summaries built by `index_store_summaries(store)`; class-restricted via ChromaDB's `$in` metadata filter, so security is enforced at the DB layer for this collection

Embeddings use `nomic-embed-text` via Ollama (`OllamaEmbeddings` from `langchain-community`).

### MCP server (`src/mcp_server.py`)

FastMCP stdio server. User identity is set at process start via `MCP_USER_ID`, `MCP_USER_ROLE`, `MCP_ALLOWED_CLASSES` env vars — one process per user. The server exposes 7 tools (`ask_analyst`, `attendance_summary`, `at_risk_students`, `class_statistics`, `search_policies`, `search_attendance_records`, `audit_log`) and enforces the same RBAC as the web backend.

### Data format

Drop CSV/Excel/Parquet files into `data/attendance/`. Required columns: `student_id`, `date`, `status` (`present`/`absent`/`late`/`excused`). Optional: `student_name`, `class`, `grade`. Files can also be uploaded via `POST /data/upload` (admin/teacher only).


