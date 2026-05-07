# Excelsis 360 — Attendance Analyst Agent

AI-powered attendance analysis system built on a LangGraph ReAct agent (Llama via NVIDIA NIM), ChromaDB vector search, and a FastAPI + React full-stack web interface.

---

## Features

- **Natural-language chat** — ask questions about attendance in plain English; the Llama model reasons across multiple tools and streams the answer token-by-token
- **ReAct reasoning loop** — the model decides which tools to call (attendance stats, at-risk query, vector knowledge base, web search) and in what order
- **ChromaDB vector search** — semantic search over intervention policy documents and indexed class summaries using NVIDIA NIM embeddings
- **Role-based access control** — four roles (admin, counselor, teacher, viewer) enforced at both the tool and data level; teachers only ever see their own classes
- **Interactive dashboards** — Plotly interactive charts and a multi-panel matplotlib/seaborn static dashboard (PNG)
- **Web UI** — React + Tailwind dark-themed interface with live streaming chat, KPI dashboard, at-risk student table, and admin user management
- **REST API** — FastAPI backend with JWT auth, SSE streaming, file upload, and dashboard generation
- **Jupyter notebook** — full interactive analysis environment that shares the same `src/` backend
- **MCP server** — exposes tools to Claude Code via the Model Context Protocol

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Llama 3.1 8B via NVIDIA NIM (`langchain-nvidia-ai-endpoints`) |
| Agent | LangGraph ReAct (`create_react_agent`) |
| Vector DB | ChromaDB + NVIDIA NIM embeddings (`nvidia/nv-embedqa-e5-v5`) |
| Backend | FastAPI + Uvicorn |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | React 18 + Vite + Tailwind CSS |
| Data | pandas, supports CSV / Excel / Parquet |
| Dashboards | Plotly (interactive HTML) + matplotlib/seaborn (PNG) |

---

## Project Structure

```
├── api/                  # FastAPI backend
│   ├── main.py           # App startup, CORS, static file mounts
│   ├── auth.py           # User registry (users.json), JWT, bcrypt
│   ├── deps.py           # FastAPI dependencies (get_current_user, etc.)
│   ├── models.py         # Pydantic request/response models
│   ├── users.json        # Persisted user accounts (auto-created)
│   └── routers/
│       ├── auth.py       # Login, user CRUD
│       ├── chat.py       # SSE streaming chat endpoint
│       ├── data.py       # Attendance stats, at-risk, file upload
│       └── dashboard.py  # Dashboard generation
│
├── src/                  # Shared Python backend (used by API + notebook)
│   ├── security.py       # RBAC: Role, Permission, UserContext, SecurityManager
│   ├── data_store.py     # AttendanceDataStore (ingest, stats, at-risk)
│   ├── vector_store.py   # AttendanceVectorStore (ChromaDB + NVIDIA embeddings)
│   ├── tools.py          # LangGraph tools (5 tools, all security-aware)
│   ├── agent.py          # ExcelsisAgent — LangGraph ReAct agent
│   ├── dashboard.py      # Dashboard builder (matplotlib/seaborn)
│   └── mcp_server.py     # FastMCP server for Claude Code
│
├── web/                  # React frontend
│   └── src/
│       ├── pages/        # Login, Chat, Dashboard, Users
│       ├── components/   # Sidebar, MessageBubble, ProtectedRoute
│       └── api/client.ts # Axios instance + SSE streaming helper
│
├── Excelsis.ipynb        # Interactive Jupyter notebook
├── start.sh              # Start both servers (backend :8000, frontend :5173)
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variable template
```

---

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
NVIDIA_API_KEY=nvapi-...          # Required — NVIDIA NIM API key
TAVILY_API_KEY=tvly-...           # Optional — enables web search tool
JWT_SECRET=change-me-in-production
ADMIN_PASSWORD=your-admin-password
```

### 2. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```bash
cd web && npm install && cd ..
```

### 4. Start both servers

```bash
bash start.sh
```

This starts:
- **FastAPI** on `http://localhost:8000`
- **React** on `http://localhost:5173`

Open **http://localhost:5173** in your browser. You'll be redirected to the login page.

Default credentials: `admin` / the value of `ADMIN_PASSWORD` in your `.env` (defaults to `admin123` if not set).

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `NVIDIA_API_KEY` | Yes | — | NVIDIA NIM API key for LLM and embeddings |
| `TAVILY_API_KEY` | No | — | Tavily web search (enables the web search tool) |
| `LLM_MODEL` | No | `meta/llama-3.1-8b-instruct` | NVIDIA NIM model ID |
| `NVIDIA_BASE_URL` | No | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM base URL |
| `EMBED_MODEL` | No | `nvidia/nv-embedqa-e5-v5` | Embedding model for ChromaDB |
| `CHROMA_PATH` | No | `./data/chroma_db` | ChromaDB persistence directory |
| `ATTENDANCE_DATA_PATH` | No | `./data/attendance` | Directory of attendance files to load on startup |
| `AT_RISK_THRESHOLD` | No | `75.0` | Default attendance % threshold for at-risk flagging |
| `JWT_SECRET` | Yes (prod) | `change-me-in-production` | Secret key for JWT signing |
| `ADMIN_PASSWORD` | No | `admin123` | Password for the default admin account |

---

## User Roles

Access is enforced at two levels: the tool is blocked before it runs, and query results are filtered to only include rows the user is allowed to see.

| Role | Own classes | At-risk list | Web search | Upload data | Audit log |
|---|---|---|---|---|---|
| `admin` | ✓ all | ✓ | ✓ | ✓ | ✓ |
| `counselor` | ✓ assigned | ✓ | ✓ | — | — |
| `teacher` | ✓ assigned | — | — | ✓ | — |
| `viewer` | ✓ assigned | — | — | — | — |

Users are managed through the **Users** page (admin only) or directly in `api/users.json`.

---

## Web Interface

| Page | Path | Access |
|---|---|---|
| Login | `/login` | Public |
| Chat | `/chat` | All authenticated users |
| Dashboard | `/dashboard` | All authenticated users |
| Users | `/users` | Admin only |

### Chat
Type any question in natural language. The Llama model streams its response token-by-token, with tool-use indicators showing which data sources it consulted (e.g. *🔧 Attendance data*, *🔧 Knowledge base*).

Example questions:
- *Which classes have the lowest attendance this month?*
- *List all students below 70% in class 10A*
- *What are the best intervention strategies for chronic absenteeism?*
- *How does Monday attendance compare to Friday?*

---

## REST API

The FastAPI backend is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | None | Username + password → JWT |
| GET | `/auth/me` | Any | Current user info |
| GET | `/auth/users` | Admin | List all users |
| POST | `/auth/users` | Admin | Create user |
| DELETE | `/auth/users/{username}` | Admin | Delete user |
| POST | `/chat/stream` | Any | SSE streaming chat |
| GET | `/data/summary` | Any | Attendance overview |
| GET | `/data/at-risk` | Counselor+ | At-risk student list |
| GET | `/data/stats` | Any | Stats by group/period |
| POST | `/data/upload` | Admin/Teacher | Upload CSV/Excel/Parquet |
| POST | `/dashboard/generate` | Any | Generate dashboard PNG |
| GET | `/health` | None | Liveness check |

---

## Jupyter Notebook

For interactive analysis, run the notebook directly:

```bash
source .venv/bin/activate
jupyter notebook Excelsis.ipynb
```

Run cells in order (1 → 10). The notebook uses the same `src/` modules as the web backend. After loading data in Cell 6, call `vec.index_store_summaries(store)` to make class summaries searchable via the vector DB.

To change who the analyst is (and what data they can access), edit `CURRENT_USER` in Cell 5:

```python
CURRENT_USER = UserContext("ms_johnson", Role.TEACHER, allowed_classes=["10A", "10B"])
```

---

## Loading Attendance Data

Place CSV, Excel (`.xlsx`), or Parquet files in `data/attendance/`. The server loads them automatically on startup.

Required columns: `student_id`, `date`, `status` (`present` / `absent` / `late` / `excused`).

Optional columns: `student_name`, `class`, `grade`.

Files can also be uploaded via the Dashboard page or the `POST /data/upload` endpoint.

---

## MCP Server (Claude Code)

The project exposes a Model Context Protocol server so Claude Code can query attendance data directly. It auto-starts via `.claude/settings.json` when you open the project in Claude Code. To run it manually:

```bash
source .venv/bin/activate
python -m src.mcp_server
```

Set `MCP_USER_ROLE` in `.env` to control what Claude Code is allowed to access (`admin`, `teacher`, `counselor`, or `viewer`).
