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

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Environment Setup

```bash
ollama pull phi4:14b
ollama pull nomic-embed-text
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock          # use the lock file for reproducible installs
cd web && npm install && cd ..
```

Ollama must be running on `http://localhost:11434` before starting the stack.

Required `.env` variables:
- `JWT_SECRET` — must be changed from the default before any production use
- `SQL_SERVER` — SQL Server hostname or IP
- `SQL_DATABASES` — comma-separated list of databases to expose
- `SQL_USERNAME` / `SQL_PASSWORD` — credentials when using `SQL_AUTH_METHOD=sql`

Key optional variables:
- `MODEL` — default `phi4:14b`; Ollama model used by the ReAct agent
- `AT_RISK_THRESHOLD` — default `75.0`
- `ADMIN_PASSWORD` — default `admin123`; sets the initial admin password on first run

Schema / domain config (all optional, override to point at any tabular SQL schema):
- `PRIMARY_TABLE` — default `attendance`; main table the agent queries
- `METRIC_COLUMN` / `POSITIVE_VALUE` — default `status` / `present`; what counts as a success
- `DATE_COLUMN` — default `date`; time column for period filtering
- `ENTITY_COLUMN` / `ENTITY_NAME_COLUMN` — default `student_id` / `student_name`
- `GROUP_COLUMNS` — default `class,grade`; comma-separated grouping dimensions

RAG / vector store config:
- `CHROMA_PATH` — default `.chroma`; persistent ChromaDB directory
- `EMBED_MODEL` — default `nomic-embed-text`; Ollama embedding model (must be pulled first)
- `DOCS_PATH` — default `docs`; directory scanned for policy PDFs and Markdown files

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

## Tests

```bash
pytest tests/test_qa.py -v                 # unit tests only (no Ollama needed)
pytest tests/test_qa.py -v -m integration  # integration tests (requires Ollama)
pytest tests/test_qa.py -v --run-all       # everything
```

Unit tests (`TestZeroKnowledge`) call tools directly — no LLM involved, fast. Integration tests (`TestModelStress`) hit a live Ollama instance.

## Jupyter Notebook

```bash
source .venv/bin/activate
jupyter notebook Excelsis.ipynb
```

Run cells in order (1 → 9). To change the analyst identity, edit `CURRENT_USER` in Cell 5.

---

## Architecture

### Request flow

Browser → React (`web/`) → FastAPI (`api/`) → `ExcelsisAgent` (`src/agent.py`) → LangGraph ReAct loop → tools (`src/tools.py`) → `SQLDataStore` (`src/sql_store.py`)

For schema/policy questions, tools also call → `ExcelsisRAGStore` (`src/rag_store.py`) → ChromaDB vector search.

The `/chat/stream` endpoint uses SSE (`StreamingResponse`); the frontend consumes `on_chat_model_stream`, `on_tool_start`, and `on_tool_end` events from LangGraph's `astream_events`.

### Security (`src/security.py`)

`UserContext` is a simple dataclass with a single field: `user_id`. There is no role enum, no permission system, and no row-level filtering in the current implementation. Authentication is purely identity-based — the JWT `sub` claim is decoded to a username and wrapped in `UserContext`.

### User management (`api/auth.py` + `api/users.json`)

Users are stored as bcrypt-hashed records in `api/users.json`. On startup, `ensure_default_admin()` creates the admin account if missing. JWTs embed only `sub` (username) and `exp` (expiry); `decode_token()` reconstructs a `UserContext(user_id=username)` from them. Token TTL is 24 hours.

### RAG layer (`src/rag_store.py` + `src/rag_ingestor.py`)

`ExcelsisRAGStore` holds two ChromaDB collections: `excelsis_schema` (SQL table/column metadata, 6 results) and `excelsis_policy` (policy documents, 4 results). Embeddings use `nomic-embed-text` via Ollama. On startup, a background daemon thread runs `ExcelsisRAGIngestor`, which indexes every `.pdf` and `.md` file under `DOCS_PATH` and auto-ingests `INFORMATION_SCHEMA` for all databases in `SQL_DATABASES`. Chunk size: 800 chars, overlap: 80.

### MCP server (`src/mcp_server.py`)

FastMCP stdio server. User identity is set at process start via the `MCP_USER_ID` env var — one process per user. The server exposes 6 tools: `ask_analyst`, `data_summary`, `threshold_alerts`, `group_statistics`, `schema_lookup`, `knowledge_lookup`.

### Data backend (`src/sql_store.py`)

`SQLDataStore` connects to SQL Server via `pyodbc`. Connection is configured through env vars (`SQL_SERVER`, `SQL_DATABASES`, `SQL_PRIMARY_DB`, `SQL_AUTH_METHOD`, `SQL_USERNAME`, `SQL_PASSWORD`). The table and column names are fully configurable via `PRIMARY_TABLE`, `METRIC_COLUMN`, `POSITIVE_VALUE`, `DATE_COLUMN`, `ENTITY_COLUMN`, `ENTITY_NAME_COLUMN`, and `GROUP_COLUMNS` — defaults match the original attendance schema (`attendance`, `status`, `present`, `date`, `student_id`, `student_name`, `class,grade`). The agent can also query other databases listed in `SQL_DATABASES` via the `run_sql_query` tool's `database` parameter. All queries are read-only; writes are blocked via `sqlglot` parse-time validation.
