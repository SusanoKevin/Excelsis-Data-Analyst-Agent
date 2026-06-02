"""
generate_docs.py — Regenerates "Excelsis 360 Analyst Agent.pdf"
Run: python generate_docs.py
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph,
    Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle,
)

W, H = A4
MARGIN = 2.2 * cm

C_BLACK   = colors.HexColor("#0d0d0d")
C_WHITE   = colors.white
C_GREY    = colors.HexColor("#5d5d5d")
C_LGREY   = colors.HexColor("#ececec")
C_MGREY   = colors.HexColor("#8f8f8f")
C_TBLHEAD = colors.HexColor("#0d0d0d")
C_TBLALT  = colors.HexColor("#f9f9f9")

def S(name, **kw): return ParagraphStyle(name, **kw)

H1   = S("h1",   fontSize=22, fontName="Helvetica-Bold", textColor=C_BLACK,
         leading=28, spaceBefore=22, spaceAfter=10)
H2   = S("h2",   fontSize=14, fontName="Helvetica-Bold", textColor=C_BLACK,
         leading=18, spaceBefore=16, spaceAfter=6)
H3   = S("h3",   fontSize=11, fontName="Helvetica-Bold", textColor=C_BLACK,
         leading=15, spaceBefore=10, spaceAfter=4)
BODY = S("body", fontSize=10, fontName="Helvetica", textColor=C_BLACK,
         leading=15, spaceAfter=6)
BSML = S("bsml", fontSize=9,  fontName="Helvetica", textColor=C_BLACK,
         leading=13, spaceAfter=4)
BULL = S("bull", fontSize=10, fontName="Helvetica", textColor=C_BLACK,
         leading=14, leftIndent=14, spaceAfter=3, bulletIndent=4, bulletText="•")
CODE = S("code", fontSize=8.5, fontName="Courier", textColor=C_BLACK,
         leading=12, backColor=colors.HexColor("#f4f4f4"),
         leftIndent=10, rightIndent=10, spaceBefore=4, spaceAfter=6)
TH   = S("th",   fontSize=9, fontName="Helvetica-Bold", textColor=C_WHITE, leading=12)
TD   = S("td",   fontSize=9, fontName="Helvetica",      textColor=C_BLACK, leading=12)
TDC  = S("tdc",  fontSize=8.5, fontName="Courier",      textColor=C_BLACK, leading=12)
CVSB = S("cvsb", fontSize=16, fontName="Helvetica",
         textColor=colors.HexColor("#cccccc"), leading=22)
CVMT = S("cvmt", fontSize=10, fontName="Helvetica-Oblique",
         textColor=C_MGREY, leading=14, spaceBefore=30)

TS = TableStyle([
    ("BACKGROUND",    (0,0),(-1,0),  C_TBLHEAD),
    ("TEXTCOLOR",     (0,0),(-1,0),  C_WHITE),
    ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
    ("FONTSIZE",      (0,0),(-1,0),  9),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_WHITE, C_TBLALT]),
    ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
    ("FONTSIZE",      (0,1),(-1,-1), 9),
    ("GRID",          (0,0),(-1,-1), 0.4, C_LGREY),
    ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ("TOPPADDING",    (0,0),(-1,-1), 5),
    ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ("LEFTPADDING",   (0,0),(-1,-1), 7),
    ("RIGHTPADDING",  (0,0),(-1,-1), 7),
])
NS = TableStyle([
    ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#fffbe6")),
    ("BOX",         (0,0),(-1,-1), 0.8, colors.HexColor("#e0c000")),
    ("LEFTPADDING", (0,0),(-1,-1), 10),
    ("RIGHTPADDING",(0,0),(-1,-1), 10),
    ("TOPPADDING",  (0,0),(-1,-1), 8),
    ("BOTTOMPADDING",(0,0),(-1,-1),8),
])

cw = W - 2 * MARGIN

def p(t, s=BODY):    return Paragraph(t, s)
def h1(t):           return Paragraph(t, H1)
def h2(t):           return Paragraph(t, H2)
def h3(t):           return Paragraph(t, H3)
def b(t):            return Paragraph(t, BULL)
def sp(n=6):         return Spacer(1, n)
def hr():            return HRFlowable(width="100%", thickness=0.5, color=C_LGREY, spaceAfter=6)
def pre(t):          return Preformatted(t, CODE)
def th(*c):          return [Paragraph(x, TH) for x in c]
def td(*c):          return [Paragraph(x, TD) for x in c]
def tdc(*c):         return [Paragraph(x, TDC) for x in c]
def tbl(d, w=None):
    t = Table(d, colWidths=w, repeatRows=1); t.setStyle(TS); return t
def note(t):
    inner = [[Paragraph("<b>Known Limitations</b><br/>" + t, BSML)]]
    tb = Table(inner, colWidths=[cw]); tb.setStyle(NS); return tb

def _cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_BLACK)
    canvas.rect(0, H - 6*cm, W, 6*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 38); canvas.setFillColor(C_WHITE)
    canvas.drawString(MARGIN, H - 3.2*cm, "Excelsis 360")
    canvas.setFont("Helvetica", 16)
    canvas.drawString(MARGIN, H - 4.2*cm, "Data Analyst Agent")
    canvas.setFont("Helvetica", 11); canvas.setFillColor(colors.HexColor("#aaaaaa"))
    canvas.drawString(MARGIN, H - 5.0*cm, "Technical Documentation  ·  v1.2")
    canvas.restoreState()

def _page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 9); canvas.setFillColor(C_BLACK)
    canvas.drawString(MARGIN, H - 1.5*cm, "Excelsis 360 — Data Analyst Agent")
    canvas.setFont("Helvetica", 9); canvas.setFillColor(C_GREY)
    canvas.drawRightString(W - MARGIN, H - 1.5*cm, "Technical Documentation")
    canvas.line(MARGIN, H - 1.7*cm, W - MARGIN, H - 1.7*cm)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 1.2*cm, "Confidential · Internal Use")
    canvas.drawRightString(W - MARGIN, 1.2*cm, f"Page {doc.page}")
    canvas.line(MARGIN, 1.6*cm, W - MARGIN, 1.6*cm)
    canvas.restoreState()

def _tmpl(canvas, doc):
    (_cover if doc.page == 1 else _page)(canvas, doc)

# ─────────────────────────────────────────────────────────────────────────────

def build():
    doc = SimpleDocTemplate(
        "Excelsis 360 Analyst Agent.pdf", pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=3.2*cm, bottomMargin=2.5*cm,
    )
    s = []   # story

    # COVER
    s += [Spacer(1,7*cm), p("Technical Documentation", CVSB), sp(10),
          p("An AI-powered data analyst for the Excelsis360 platform,<br/>"
            "built on locally-hosted LLMs, SQL Server, and a React web interface.", CVSB),
          sp(20), hr(), p("Version 1.2  ·  June 2026", CVMT), PageBreak()]

    # TOC
    s.append(h1("Table of Contents"))
    s.append(tbl([
        th("#","Chapter","Summary"),
        td("1","Project Overview","What Excelsis 360 is, its purpose, and its key capabilities"),
        td("2","Use Cases","Scenarios the system is designed to support"),
        td("3","System Architecture","High-level design and data flow"),
        td("4","Technology Stack","Every library and tool used and why"),
        td("5","Data Backend — SQLDataStore","SQL Server integration, caching, and SQL safety"),
        td("6","AI Agent — ExcelsisAgent","LangGraph ReAct loop, SqliteSaver checkpointer, and streaming"),
        td("7","Agent Tools","All 13 tools exposed to the LLM"),
        td("8","REST API","FastAPI endpoints, auth, rate limiting, and SSE"),
        td("9","Authentication & User Management","JWT, bcrypt, and users.json"),
        td("10","React Web Interface","Pages, components, and the design system"),
        td("11","MCP Server","Claude Code integration via FastMCP"),
        td("12","Jupyter Notebook","Interactive analysis environment"),
        td("13","Configuration Reference","All environment variables"),
        td("14","Security Model","What is enforced and what is not"),
        td("15","Running the Stack","Installation, setup, and operation"),
        td("16","Test Suite","Unit and integration tests"),
        td("17","Extending the System","How to add databases, tools, and pages"),
    ], [1.2*cm, 5.5*cm, cw-6.7*cm]))
    s.append(PageBreak())

    # CH 1 ────────────────────────────────────────────────────────────────────
    s.append(h1("1. Project Overview"))
    s += [p("The Excelsis 360 Data Analyst Agent is a full-stack AI analyst. It extends existing data "
            "infrastructure with a reasoning AI layer — combining a locally-hosted LLM (qwen2.5:14b via Ollama), "
            "direct SQL Server access, a ChromaDB RAG layer, and a dedicated web interface — to give staff a "
            "conversational way to interrogate data without writing reports or navigating dashboards."),
          h2("1.1 Core Principles"),
          b("<b>Privacy-first.</b> All inference runs locally via Ollama — no data ever leaves the network."),
          b("<b>Read-only data access.</b> AST-level SQL parsing rejects DML/DDL; database allowlist enforced."),
          b("<b>Transparent reasoning.</b> Streaming interface shows each tool call as it happens."),
          b("<b>Zero speculative statistics.</b> Agent never fabricates data."),
          b("<b>Minimal footprint.</b> No cloud dependencies at inference time."),
          h2("1.2 Key Features")]
    s.append(tbl([
        th("Feature","Description"),
        td("Natural-language chat",   "Ask questions in plain English; agent reasons and streams answer token-by-token"),
        td("ReAct reasoning loop",    "Model decides which tools to call, in what order, across multiple steps"),
        td("At-risk detection",       "Automatic flagging of entities below a configurable metric threshold (default 75%)"),
        td("Ad-hoc SQL",              "Agent can write and run T-SQL SELECT queries against any configured database"),
        td("Live dashboard",          "5 interactive Recharts charts with Power BI-style cross-filtering and drill-down"),
        td("Agent ↔ dashboard link",  "Asking the agent to show a chart updates the dashboard live via SSE"),
        td("User management",         "Admin-controlled accounts with bcrypt-hashed passwords and 24h JWT tokens"),
        td("RAG knowledge base",      "ChromaDB + BAAI/bge-small-en-v1.5 (HuggingFace, auto-downloaded); "
                                      "indexes SQL schema and policy documents"),
        td("Persistent chat history", "Per-user conversation stored in SQLite via LangGraph SqliteSaver (CHAT_DB); "
                                      "survives restarts, shared across all Uvicorn workers"),
        td("Rate limiting",           "10 req/min/user via SlowAPI; Redis-backed (REDIS_URI) for multi-worker accuracy; "
                                      "falls back to in-memory when REDIS_URI is unset"),
        td("MCP server",              "FastMCP stdio server: ask_analyst (full ReAct loop) + 5 direct-data tools"),
        td("Jupyter notebook",        "Full interactive analysis environment sharing the same src/ backend"),
    ], [4.5*cm, cw-4.5*cm]))
    s.append(PageBreak())

    # CH 2 ────────────────────────────────────────────────────────────────────
    s.append(h1("2. Use Cases"))
    s.append(p("Excelsis 360 is built around concrete workflows. Each use case maps to one or more agent tools."))
    for title, body in [
        ("2.1 Daily Check",
         "A staff member asks: \"Which groups had the lowest metric this week?\" The agent calls "
         "<font face='Courier'>query_data(period='last_7_days')</font> and streams a ranked table."),
        ("2.2 At-Risk Identification",
         "Ask: \"List all entities below 70%.\" The agent calls "
         "<font face='Courier'>get_threshold_alerts(threshold=70.0)</font> and returns a table with "
         "entity IDs, labels, groups, and metric rates."),
        ("2.3 Trend Analysis",
         "Ask: \"How does this month compare to the previous month?\" The agent calls "
         "<font face='Courier'>compare_periods</font> and returns a side-by-side table with a delta column."),
        ("2.4 Segment Comparison",
         "Ask: \"Compare segment A and B.\" The agent calls <font face='Courier'>compare_segments</font> "
         "and presents both segments side by side."),
        ("2.5 Ad-hoc Reporting",
         "The agent calls <font face='Courier'>query_data(group_by='day_of_week')</font> or writes a "
         "T-SQL query via <font face='Courier'>run_sql_query</font> for complex custom reports."),
        ("2.6 Dashboard-Driven Exploration",
         "Navigate to the Dashboard. Use FilterBar, click charts to cross-filter, double-click to drill down. "
         "Use 'Ask Excelsis' to open the embedded chat panel — the agent updates dashboard filters live."),
        ("2.7 Policy Knowledge",
         "The agent calls <font face='Courier'>retrieve_policy</font>. The RAG layer returns top-matching "
         "excerpts from docs/*.md and docs/*.pdf. The agent synthesises a grounded answer."),
        ("2.8 Model Context Protocol (MCP)",
         "Start: <font face='Courier'>python -m src.mcp_server</font>. Call "
         "<font face='Courier'>ask_analyst</font> for full ReAct loop, or direct tools for raw results."),
    ]:
        s.append(h2(title)); s.append(p(body))
    s.append(PageBreak())

    # CH 3 ────────────────────────────────────────────────────────────────────
    s.append(h1("3. System Architecture"))
    s.append(h2("3.1 Request Flow"))
    s.append(tbl([
        th("Layer","Component","Technology","Role"),
        td("React App",         "React 18 + Vite",   "Browser",           "Renders UI, manages auth token, opens SSE stream"),
        td("Fetch / Axios",     "Browser Fetch API", "Fetch + Axios",     "POST /chat/stream → EventSource-style reader"),
        td("FastAPI",           "Python / Uvicorn",  "FastAPI",           "JWT validation, rate limiting, request routing"),
        td("ExcelsisAgent",     "LangGraph ReAct",   "langgraph",         "SqliteSaver checkpointer (CHAT_DB); streams LLM events"),
        td("qwen2.5:14b",       "Ollama",            "langchain-ollama",  "Reasons about tool selection and response"),
        td("13 tools",          "Python functions",  "langchain-core",    "SQL, stats, RAG, anomaly detection, trend analysis"),
        td("SQLDataStore",      "SQLAlchemy Pool",   "pyodbc + sqlalchemy","Read-only T-SQL with TTL cache and _exec/_query boundary"),
        td("SQL Server",        "ODBC Driver 18",    "pyodbc",            "Primary data table + optional extra databases"),
    ], [3.0*cm, 3.0*cm, 3.2*cm, cw-9.2*cm]))

    s.append(h2("3.2 Component Diagram"))
    s.append(pre(
        "Browser (React :5173)\n"
        "  POST /chat/stream  (Bearer JWT)\n"
        "  GET  /data/*\n"
        "  ▼\n"
        "FastAPI (:8000)\n"
        "  /auth/*        JWT sign/verify, user CRUD\n"
        "  /chat/stream   SSE → ExcelsisAgent.astream_events()\n"
        "  /data/*        Direct SQLDataStore queries (no LLM)\n\n"
        "ExcelsisAgent  (LangGraph ReAct)\n"
        "  ChatOllama    → qwen2.5:14b @ OLLAMA_BASE_URL\n"
        "  SqliteSaver   → CHAT_DB  (per-user history, thread_id=user_id)\n"
        "  13 tools\n\n"
        "SQLDataStore (read-only)\n"
        "  _exec()  ← trusted internal executor  (no parse guard)\n"
        "  _query() ← _assert_select_only() guard (LLM-provided SQL only)\n"
        "  QueuePool → SQL Server\n\n"
        "ExcelsisRAGStore (ChromaDB)\n"
        "  excelsis_schema ← INFORMATION_SCHEMA (indexed via _exec)\n"
        "  excelsis_policy ← docs/*.pdf + docs/*.md\n\n"
        "Rate Limiter (slowapi)\n"
        "  REDIS_URI set   → shared counters across workers\n"
        "  REDIS_URI empty → per-process in-memory counters"
    ))

    s.append(h2("3.3 Streaming Architecture"))
    s.append(tbl([
        th("SSE Event","Frontend Action"),
        tdc('{"type": "token", "content": "…"}',      "LLM token — appended to current message bubble"),
        tdc('{"type": "tool_start", "tool": "…"}',    "Tool call started — spinner badge shown"),
        tdc('{"type": "tool_end", "tool": "…"}',      "Tool call returned — spinner removed"),
        tdc('{"type": "tool_data", "tool": "…", …}',  "Tool returned table — rendered as interactive data grid"),
        tdc('{"type": "dashboard_filter", …}',         "update_dashboard_view called — dashboard state updates live"),
        tdc('{"type": "error", "message": "…"}',      "Timeout or model error — displayed to user"),
        tdc('{"type": "done"}',                        "Stream complete — input field unlocked"),
    ], [6.5*cm, cw-6.5*cm]))
    s.append(PageBreak())

    # CH 4 ────────────────────────────────────────────────────────────────────
    s.append(h1("4. Technology Stack"))
    s.append(tbl([
        th("Library","Package","Layer","Why chosen"),
        td("qwen2.5:14b",       "Ollama",                    "LLM",               "Strong tool-calling; fits on consumer GPU or Apple Silicon"),
        td("LangGraph",         "langgraph",                 "Agent framework",    "ReAct loop with checkpointer, tool routing, async event streaming"),
        td("SqliteSaver",       "langgraph-checkpoint-sqlite","Conversation state","Per-user persistent history via thread_id; worker-safe SQLite"),
        td("langchain-ollama",  "langchain-ollama",          "LLM bridge",         "ChatOllama wraps Ollama's HTTP API"),
        td("FastAPI",           "fastapi",                   "Web framework",      "Async, schema-validated, auto-docs, SSE"),
        td("pyodbc",            "pyodbc",                    "SQL driver",         "ODBC 18 for SQL Server; Windows Auth + SQL Auth"),
        td("SQLAlchemy",        "sqlalchemy",                "Connection pool",    "QueuePool per database; pool_pre_ping; contextlib.closing"),
        td("sqlglot",           "sqlglot",                   "SQL parser",         "AST SELECT-only enforcement via _assert_select_only()"),
        td("pandas",            "pandas",                    "Data wrangling",     "DataFrames for all intermediate computation"),
        td("python-jose",       "python-jose",               "JWT",                "HS256 signing/verification; 24-hour TTL"),
        td("bcrypt",            "bcrypt",                    "Password hashing",   "Per-password salt; stored in users.json"),
        td("SlowAPI",           "slowapi",                   "Rate limiting",      "10 req/min/user; Redis-backed when REDIS_URI is set"),
        td("redis",             "redis",                     "Cache backend",      "Optional; shared rate-limit counters across workers"),
        td("ChromaDB",          "chromadb",                  "Vector store",       "Persistent local vector DB; schema + policy collections"),
        td("HuggingFace Embed", "langchain-huggingface",     "Embeddings",         "BAAI/bge-small-en-v1.5 — auto-downloaded; no Ollama pull"),
        td("prometheus-client", "prometheus-client + prometheus-fastapi-instrumentator", "Metrics", "Agent tool invocations, query duration, errors, cache hit/miss; /metrics scrape endpoint"),

        td("FastMCP",           "mcp",                       "MCP server",         "stdio FastMCP; 6 tools for model-direct data access"),
        td("React 18",          "react",                     "Frontend",           "Hooks-based SPA; Vite build and HMR"),
        td("Tailwind CSS v4",   "tailwindcss",               "Styling",            "Utility-first; custom design tokens"),
        td("Recharts",          "recharts",                  "Charts",             "Responsive SVG: bar, line, donut, area"),
        td("Axios",             "axios",                     "HTTP client",        "Auto-attaches JWT; 401 → redirect to login"),
        td("React Router v6",   "react-router-dom",          "Client routing",     "SPA navigation; ProtectedRoute enforces auth"),
    ], [3.2*cm, 3.8*cm, 2.8*cm, cw-9.8*cm]))
    s.append(PageBreak())

    # CH 5 ────────────────────────────────────────────────────────────────────
    s.append(h1("5. Data Backend — SQLDataStore"))
    s += [p("SQLDataStore is the single source of truth for all Excelsis360 data. It is a read-only wrapper "
            "around SQL Server in <font face='Courier'>src/sql_store.py</font>."),
          h2("5.1 Database Schema"),
          p("All column names are configurable via environment variables:")]
    s.append(tbl([
        th("Env Var","Default","Purpose"),
        td("PRIMARY_TABLE",     "attendance",  "Main table the agent queries"),
        td("METRIC_COLUMN",     "status",      "Column holding the measured metric"),
        td("POSITIVE_VALUE",    "active",      "Value counted as a positive outcome"),
        td("DATE_COLUMN",       "date",        "Date column for time-based filtering"),
        td("ENTITY_COLUMN",     "entity_id",   "Primary entity key"),
        td("ENTITY_NAME_COLUMN","entity_name", "Human-readable entity label"),
        td("GROUP_COLUMNS",     "(empty)",     "Comma-separated grouping dimensions"),
    ], [4.5*cm, 3.0*cm, cw-7.5*cm]))

    s += [h2("5.2 SQL Safety — _exec vs _query"),
          p("Two execution methods with a clear security boundary:"),
          b("<b>_exec(sql, params, database)</b> — trusted internal executor used by all internal methods "
            "(<font face='Courier'>summary</font>, <font face='Courier'>compute_stats</font>, "
            "<font face='Courier'>get_threshold_alerts</font>, etc.). No parse-time guard — avoids overhead "
            "on hardcoded trusted SQL. Uses <font face='Courier'>contextlib.closing(engine.raw_connection())</font> "
            "for safe pool lifecycle management."),
          b("<b>_query(sql, params, database)</b> — security wrapper. Calls "
            "<font face='Courier'>_assert_select_only(sql)</font> first (sqlglot AST guard), then delegates to "
            "<font face='Courier'>_exec</font>. Used <b>exclusively</b> by the "
            "<font face='Courier'>run_sql_query</font> tool for LLM-provided SQL."),
          p("<font face='Courier'>_assert_select_only</font> rejects: INSERT, UPDATE, DELETE, DROP, CREATE, "
            "ALTER, TRUNCATE, MERGE, Command (EXEC/xp_cmdshell), multiple statements, and queries against "
            "databases not in SQL_DATABASES."),
          p("The RAG ingestor queries <font face='Courier'>INFORMATION_SCHEMA.COLUMNS</font> via "
            "<font face='Courier'>_exec</font> directly — bypassing the guard that would otherwise block "
            "system schema access."),
          h3("SQL Injection Prevention"),
          b("All user-supplied values are parameterised via pyodbc — never string-interpolated."),
          b("Group-by column expressions come from a hardcoded allow-list dict (_group_expr). "
            "Unambiguous prefix aliases (e.g. <font face='Courier'>\"class\"</font> → "
            "<font face='Courier'>\"class_section\"</font>) are resolved before validation; "
            "ambiguous or unknown values surface a clear valid-keys error."),
          b("sqlglot AST check catches multi-statement attacks even if parameterisation were bypassed."),
          h2("5.3 TTL Cache"),
          p("In-process _TTLCache with 5-minute expiry. All query methods check before hitting SQL Server. "
            "Cache key encodes all parameters so different filter combinations are cached independently. "
            "Each cache instance is labelled by name (e.g. <font face='Courier'>\"sql\"</font>, "
            "<font face='Courier'>\"rag\"</font>) and emits "
            "<font face='Courier'>cache_hits_total</font> / <font face='Courier'>cache_misses_total</font> "
            "Prometheus counters so cache effectiveness is visible in the /metrics scrape."),
          h2("5.4 Public Methods")]
    s.append(tbl([
        th("Method","Description"),
        td("summary()",                                     "Returns dict: total_records, entity_count, date_range, metric_rate, below_threshold_count, dimensions"),
        td("compute_stats(group_by, period, segments, ...)", "DataFrame aggregated by dimension and period; used by query_data, compare_periods, and /data/stats"),
        td("get_threshold_alerts(threshold, segments, ...)", "DataFrame of entities below threshold, ordered by metric_rate ascending"),
        td("entity_weekly_rates(entity_ids, weeks)",         "Dict mapping entity_id → weekly metric rate list; used for sparkline charts"),
        td("analyze_weekly_trend(...)",                      "Returns direction (improving/declining/stable), slope_per_week, and weekly breakdown"),
        td("compute_statistical_summary(group_by, ...)",     "describe() stats of metric_rate across groups"),
        td("detect_anomalies(group_by, sigma, ...)",         "Groups deviating more than sigma std deviations from the mean with z-scores"),
        td("get_top_n(group_by, n, ascending, ...)",         "Top or bottom N groups ranked by metric_rate"),
    ], [5.5*cm, cw-5.5*cm]))

    s += [h2("5.5 Connection Management"),
          p("SQLAlchemy QueuePool (one engine per database, created at startup). Pool size = SQL_POOL_SIZE "
            "(default 5). Each query uses <font face='Courier'>contextlib.closing(engine.raw_connection())</font> "
            "to borrow from the pool and return automatically. <font face='Courier'>store.close()</font> "
            "disposes all engines on FastAPI lifespan shutdown.")]
    s.append(PageBreak())

    # CH 6 ────────────────────────────────────────────────────────────────────
    s.append(h1("6. AI Agent — ExcelsisAgent"))
    s += [p("ExcelsisAgent wraps a LangGraph ReAct agent powered by qwen2.5:14b via Ollama."),
          h2("6.1 The ReAct Loop"),
          p("ReAct interleaves Reasoning (what to do) and Acting (calling a tool). LangGraph alternates "
            "llm ↔ tools nodes until the model emits a final AIMessage with no further tool calls."),
          pre(
              "User message\n"
              "  ▼\n"
              "LLM node  (qwen2.5:14b)\n"
              "  YES → Tools node → result → LLM node (decides again)\n"
              "  NO  → Final answer (streamed token-by-token)"
          ),
          h2("6.2 System Prompt"),
          p("Fixed system prompt defines persona, tool usage rules, and analytical approach:"),
          b("Never fabricate statistics — say so if data is unavailable"),
          b("Call tools immediately — never narrate a tool call before making it"),
          b("T-SQL syntax only; SELECT-only; use TOP, DATEPART, FORMAT, CONVERT, ISNULL"),
          b("Call update_dashboard_view when user asks to see a chart or visual"),
          b("Answer greetings and general questions directly without calling tools"),
          h2("6.3 Conversation History — SqliteSaver"),
          p("Conversation history is persisted using LangGraph's <b>SqliteSaver</b> checkpointer, stored "
            "in <font face='Courier'>CHAT_DB</font> (default <font face='Courier'>./chat.db</font>). "
            "Each user's thread is keyed by <font face='Courier'>thread_id=user.user_id</font> in the graph "
            "config. The checkpointer loads and saves message state automatically on every call — "
            "no manual history dict, no eviction loop, no per-message append code. "
            "History survives server restarts and is shared across all Uvicorn workers."),
          h2("6.4 Timeout Handling"),
          p("Both <font face='Courier'>ask()</font> (sync, daemon thread + queue.Queue) and "
            "<font face='Courier'>astream_events()</font> (async, asyncio.timeout) enforce a 240-second "
            "timeout. The frontend SSE timeout is 270 s to match this plus a 30 s network buffer."),
          h2("6.5 LLM Configuration")]
    s.append(tbl([
        th("Parameter","Value / Description"),
        td("model",      "qwen2.5:14b (overridden by MODEL env var)"),
        td("base_url",   "http://localhost:11434 (overridden by OLLAMA_BASE_URL)"),
        td("temperature","0.1 — low for consistent, factual responses"),
        td("num_ctx",    "8192 tokens context window"),
        td("keep_alive", "10 minutes — model stays loaded in VRAM between requests"),
    ], [3.5*cm, cw-3.5*cm]))

    s += [h2("6.6 Monitoring & Observability"),
          p("<font face='Courier'>src/tracker.py</font> provides <b>QueryTracker</b> — a lightweight "
            "per-request wrapper that records tool use, latency, and errors to Prometheus. "
            "Grafana dashboards in <font face='Courier'>docker/grafana/</font> visualise all metrics "
            "out of the box."),
          b("<font face='Courier'>agent_tool_invocations_total</font> [label: tool] — incremented each "
            "time the agent calls a named tool."),
          b("<font face='Courier'>agent_query_duration_seconds</font> — histogram (buckets 0.5 s – 240 s) "
            "of full agent invocation latency."),
          b("<font face='Courier'>agent_query_errors_total</font> — incremented on any agent exception."),
          b("<font face='Courier'>cache_hits_total</font> / <font face='Courier'>cache_misses_total</font> "
            "[label: cache] — emitted by every _TTLCache instance; distinguishes "
            "<font face='Courier'>sql</font> vs <font face='Courier'>rag</font> caches."),
          p("All metrics are scraped via <b>GET /metrics</b> (exposed automatically by "
            "<font face='Courier'>prometheus_fastapi_instrumentator</font>). "
            "Start the full observability stack with: "
            "<font face='Courier'>docker compose -f docker/docker-compose.yml up -d prometheus grafana</font>. "
            "Grafana is available at <b>http://localhost:3001</b> (default password: admin).")]
    s.append(PageBreak())

    # CH 7 ────────────────────────────────────────────────────────────────────
    s.append(h1("7. Agent Tools"))
    s.append(p("13 tools in <font face='Courier'>src/tools.py</font>, each decorated with @tool from LangChain. "
               "Tools returning tabular data use response_format=\"content_and_artifact\" for UI table rendering."))
    s.append(tbl([
        th("Tool","Parameters","Description"),
        [p("<font face='Courier'>query_data</font>",TD),
         p("<font face='Courier'>group_by, period</font>",BSML),
         p("Metric stats grouped by dimension and period. Calls store.compute_stats().", BSML)],
        [p("<font face='Courier'>get_threshold_alerts</font>",TD),
         p("<font face='Courier'>threshold=75.0</font>",BSML),
         p("Entities below threshold ordered by metric_rate ascending.", BSML)],
        [p("<font face='Courier'>get_summary</font>",TD),
         p("(none)",BSML),
         p("High-level overview: total_records, entity_count, date_range, metric_rate, dimensions.", BSML)],
        [p("<font face='Courier'>update_dashboard_view</font>",TD),
         p("<font face='Courier'>segments, period, view</font>",BSML),
         p("Emits dashboard_filter SSE event to update React state without page reload.", BSML)],
        [p("<font face='Courier'>run_sql_query</font>",TD),
         p("<font face='Courier'>sql, database=\"\"</font>",BSML),
         p("Ad-hoc T-SQL SELECT via _query() guard. Auto-adds TOP 200. Returns up to 200 rows.", BSML)],
        [p("<font face='Courier'>compare_periods</font>",TD),
         p("<font face='Courier'>period_a, period_b</font>",BSML),
         p("Side-by-side metric rate table with delta column for two time periods.", BSML)],
        [p("<font face='Courier'>compare_segments</font>",TD),
         p("<font face='Courier'>segment_a, segment_b</font>",BSML),
         p("Metric statistics for two segment values side by side.", BSML)],
        [p("<font face='Courier'>retrieve_schema</font>",TD),
         p("<font face='Courier'>query</font>",BSML),
         p("Vector search of excelsis_schema ChromaDB collection (top-6 chunks). Use before SQL.", BSML)],
        [p("<font face='Courier'>retrieve_policy</font>",TD),
         p("<font face='Courier'>query</font>",BSML),
         p("Vector search of excelsis_policy ChromaDB collection (top-4 chunks).", BSML)],
        [p("<font face='Courier'>statistical_summary</font>",TD),
         p("<font face='Courier'>group_by</font>",BSML),
         p("Distribution stats (mean, std, min, percentiles, max) of metric_rate across groups.", BSML)],
        [p("<font face='Courier'>detect_anomalies</font>",TD),
         p("<font face='Courier'>group_by, sigma=2.0</font>",BSML),
         p("Groups deviating more than sigma std deviations from the mean, with z-scores.", BSML)],
        [p("<font face='Courier'>get_top_n</font>",TD),
         p("<font face='Courier'>group_by, n=10, ascending</font>",BSML),
         p("Top or bottom N groups ranked by metric_rate.", BSML)],
        [p("<font face='Courier'>analyze_trend</font>",TD),
         p("(none)",BSML),
         p("Week-over-week trend: direction (improving/declining/stable), slope, weekly breakdown.", BSML)],
    ], [3.8*cm, 4.2*cm, cw-8.0*cm]))
    s.append(PageBreak())

    # CH 8 ────────────────────────────────────────────────────────────────────
    s.append(h1("8. REST API"))
    s += [p("FastAPI backend at http://localhost:8000. Interactive docs at http://localhost:8000/docs. "
            "All endpoints except /auth/login and /health require a valid Bearer JWT."),
          h2("8.1 Endpoints")]
    s.append(tbl([
        th("Method","Path","Auth","Description"),
        td("POST",   "/auth/login",            "None",    "Username + password → JWT (24h TTL)"),
        td("GET",    "/auth/me",               "Any",     "Current user's username"),
        td("GET",    "/auth/users",            "Admin",   "List all registered usernames"),
        td("POST",   "/auth/users",            "Admin",   "Create a new user account"),
        td("DELETE", "/auth/users/{username}", "Admin",   "Delete a user (cannot delete 'admin')"),
        td("POST",   "/chat/stream",           "Any",     "SSE streaming chat → ExcelsisAgent.astream_events()"),
        td("GET",    "/data/summary",          "Any",     "Data overview"),
        td("GET",    "/data/alerts",           "Any",     "Entities below metric threshold"),
        td("GET",    "/data/stats",            "Any",     "Aggregated stats by group/period"),
        td("GET",    "/data/trends",           "Any",     "Current + prior 30-day weekly stats"),
        td("GET",    "/data/sparklines",       "Any",     "Weekly rates for entity IDs (ids= CSV)"),
        td("GET",    "/health",                "None",    '{"status": "ok", "rag_ready": bool}'),
        td("GET",    "/metrics",              "None",    "Prometheus scrape endpoint (prometheus_fastapi_instrumentator)"),
    ], [1.5*cm, 4.8*cm, 1.8*cm, cw-8.1*cm]))
    s += [h2("8.2 Rate Limiting"),
          p("POST /chat/stream is limited to 10 req/min per user (authenticated) or IP (unauthenticated). "
            "Set <font face='Courier'>REDIS_URI</font> to share counters across Uvicorn workers. "
            "Leave empty for per-process in-memory counters (single-worker). Returns HTTP 429 + Retry-After on exceed."),
          h2("8.3 CORS"),
          p("Configured via ALLOWED_ORIGINS (default: localhost:5173 + localhost:3000). "
            "In production, serve the built React app via FastAPI StaticFiles — CORS becomes unnecessary."),
          h2("8.4 Application Lifecycle"),
          p("On startup: ensure_default_admin(); instantiate SQLDataStore, ExcelsisRAGStore, and "
            "ExcelsisAgent (with SqliteSaver checkpointer); start background RAG ingestion thread; "
            "validate Ollama + SQL Server connectivity; refuse start if JWT_SECRET is the insecure default.")]
    s.append(PageBreak())

    # CH 9 ────────────────────────────────────────────────────────────────────
    s.append(h1("9. Authentication & User Management"))
    s += [h2("9.1 User Store"),
          p("Users stored in <font face='Courier'>api/users.json</font> as username → bcrypt hash. "
            "File writes use atomic write-then-rename to prevent corruption."),
          pre('{\n  "admin":      { "hashed_password": "$2b$12$..." },\n'
              '  "ms_johnson": { "hashed_password": "$2b$12$..." }\n}'),
          h2("9.2 JWT Tokens"),
          p("HS256 JWTs signed with JWT_SECRET. Claims: <b>sub</b> (username) and <b>exp</b> (24h). "
            "decode_token() reconstructs UserContext on every authenticated request. No refresh flow."),
          h2("9.3 UserContext"),
          p("Minimal dataclass with user_id field. Used as thread_id for SqliteSaver history. "
            "Supports per-user data filtering if added to store methods."),
          h2("9.4 Admin Operations"),
          p("Only admin can access /auth/users endpoints. Admin cannot be deleted. "
            "No password reset flow — delete and recreate to reset.")]
    s.append(PageBreak())

    # CH 10 ───────────────────────────────────────────────────────────────────
    s.append(h1("10. React Web Interface"))
    s.append(p("React 18 SPA built with Vite + Tailwind CSS v4. Two-column layout (sidebar + main content)."))
    s.append(h2("10.1 Pages"))
    s.append(tbl([
        th("Page","Access","Description"),
        td("Login (/login)",         "Public",        "POSTs to /auth/login, stores JWT in localStorage"),
        td("Chat (/chat)",           "Authenticated", "Streams agent responses token-by-token with tool-use badges"),
        td("Dashboard (/dashboard)", "Authenticated", "KPI cards + 5 charts + at-risk table + drilldown. Embedded chat updates filters live"),
        td("Users (/users)",         "Admin only",    "List, create, and delete user accounts"),
    ], [3.5*cm, 2.5*cm, cw-6.0*cm]))
    s.append(h2("10.2 Key Components"))
    s.append(tbl([
        th("Component","Description"),
        td("Sidebar",              "Left navigation: Chat, Dashboard, Users (admin), logout"),
        td("MessageBubble",        "Renders chat turn with markdown, tool badges, and interactive data tables"),
        td("ChatPanel",            "Embedded chat on Dashboard; passes dashboard_filter events to parent"),
        td("FilterBar",            "Group multi-select + period dropdown; triggers fresh data fetch on change"),
        td("Breadcrumb",           "Overview → Group → Entity drill navigation"),
        td("DrilldownPanel",       "Group or entity detail with sparkline trend charts"),
        td("MetricByGroupChart",   "Horizontal bar; single-click cross-filters, double-click drills down"),
        td("WeeklyTrendChart",     "Line chart; click a week to filter all dashboard data"),
        td("MetricBreakdownChart", "Donut of positive/negative outcome proportions"),
        td("WeekdayBarChart",      "Bar chart of metric rate by day of week"),
        td("TrendComparisonChart", "Grouped bar: current vs prior 30-day periods"),
        td("ProtectedRoute",       "HOC redirecting unauthenticated users to /login"),
    ], [4.5*cm, cw-4.5*cm]))
    s.append(h2("10.3 Design System"))
    s.append(tbl([
        th("Token","Hex","Usage"),
        td("carbon",     "#0d0d0d","Primary text, headings, icons"),
        td("snow",       "#ffffff","Page backgrounds, card surfaces"),
        td("fog",        "#f9f9f9","Sidebar, secondary backgrounds"),
        td("arctic-mist","#ececec","Borders, dividers, hover backgrounds"),
        td("pewter",     "#5d5d5d","Secondary text, placeholders"),
        td("link-blue",  "#007aff","Focus rings, interactive accents"),
    ], [3.0*cm, 2.5*cm, cw-5.5*cm]))
    s += [h2("10.4 SSE Client"),
          p("Uses Fetch API + ReadableStream (not EventSource — which can't POST). "
            "<font face='Courier'>streamChat()</font> in web/src/api/client.ts reads chunks, splits on "
            "newlines, strips 'data: ' prefix. Timeout: 270 s (matches 240 s backend + 30 s buffer). "
            "Auth header via shared <font face='Courier'>getAuthHeader()</font> helper — single localStorage read.")]
    s.append(PageBreak())

    # CH 11 ───────────────────────────────────────────────────────────────────
    s.append(h1("11. MCP Server"))
    s += [p("stdio-based FastMCP process. Initialises SQLDataStore, ExcelsisRAGStore, and ExcelsisAgent "
            "(with SqliteSaver checkpointer). Identity fixed via MCP_USER_ID."),
          h2("11.1 Exposed Tools")]
    s.append(tbl([
        th("Tool","Description"),
        td("ask_analyst(query)",               "Full ReAct loop: agent selects tools, reasons, and returns a complete answer"),
        td("data_summary()",                   "JSON overview: record count, entity count, date range, overall metric rate"),
        td("threshold_alerts(threshold)",      "Entities below threshold as a formatted table"),
        td("group_statistics(group_by,period)","Metric stats grouped by a dimension and period"),
        td("schema_lookup(query)",             "Vector search of table/column metadata — use before writing SQL"),
        td("knowledge_lookup(query)",          "Vector search of policy and rule documents"),
    ], [5.5*cm, cw-5.5*cm]))
    s.append(h2("11.2 Starting the MCP Server"))
    s.append(pre("MCP_USER_ID=ms_johnson python -m src.mcp_server\n# Or with default user:\npython -m src.mcp_server"))
    s.append(PageBreak())

    # CH 12 ───────────────────────────────────────────────────────────────────
    s.append(h1("12. Jupyter Notebook"))
    s += [p("Excelsis.ipynb shares the same src/ Python backend as the web application."),
          h2("12.1 Notebook Cells")]
    s.append(tbl([
        th("Cell","Name","Description"),
        td("1","Setup & imports",    "Load env vars, import src modules"),
        td("2","Connectivity check", "Verify Ollama is running; fail fast if not"),
        td("3","Connect to SQL",     "Instantiate SQLDataStore and print summary"),
        td("4","Data summary",       "Call store.summary() and display as dict"),
        td("5","Set identity",       "CURRENT_USER = UserContext(user_id='...')"),
        td("6","Agent setup",        "Instantiate ExcelsisAgent(store=store, rag_store=rag_store)"),
        td("7","Chat interface",     "agent.ask(query, user=CURRENT_USER)"),
        td("8","Direct tool calls",  "Call individual tools bypassing the LLM"),
        td("9","Visualisations",     "Plotly/matplotlib charts from store data"),
    ], [1.2*cm, 3.8*cm, cw-5.0*cm]))
    s.append(PageBreak())

    # CH 13 ───────────────────────────────────────────────────────────────────
    s.append(h1("13. Configuration Reference"))
    s.append(tbl([
        th("Variable","Required","Default","Description"),
        td("SQL_SERVER",          "Yes",       "—",                           "SQL Server hostname, IP, or named instance"),
        td("SQL_DATABASES",       "Yes",       "—",                           "Comma-separated list of allowed databases"),
        td("SQL_USERNAME",        "sql auth",  "—",                           "SQL Server login username"),
        td("SQL_PASSWORD",        "sql auth",  "—",                           "SQL Server login password"),
        td("SQL_PRIMARY_DB",      "No",        "first in SQL_DATABASES",      "Default database for queries"),
        td("SQL_AUTH_METHOD",     "No",        "sql",                         "sql | windows | azure_ad"),
        td("SQL_DRIVER",          "No",        "{ODBC Driver 18 for SQL Server}", "ODBC driver string"),
        td("SQL_POOL_SIZE",       "No",        "5",                           "SQLAlchemy QueuePool base connection count per database"),
        td("SQL_QUERY_TIMEOUT",   "No",        "30",                          "Per-query connection timeout in seconds"),
        td("JWT_SECRET",          "Yes (prod)","change-me-in-production",     "JWT signing key — MUST be changed before production"),
        td("ADMIN_PASSWORD",      "No",        "admin123",                    "Initial admin password (first startup only)"),
        td("CHAT_DB",             "No",        "./chat.db",                   "SQLite file for LangGraph SqliteSaver conversation history"),
        td("REDIS_URI",           "No",        "(empty)",                     "Redis URI for shared rate-limit counters; in-memory fallback when unset"),
        td("MODEL",               "No",        "qwen2.5:14b",                 "Ollama model for the ReAct agent"),
        td("OLLAMA_BASE_URL",     "No",        "http://localhost:11434",      "Ollama server base URL"),
        td("OLLAMA_API_KEY",      "No",        "(empty)",                     "Bearer token for authenticated Ollama instances"),
        td("AT_RISK_THRESHOLD",   "No",        "75.0",                        "Default metric % threshold for flagging"),
        td("MCP_USER_ID",         "No",        "mcp_user",                    "Username used by the MCP server process"),
        td("PRIMARY_TABLE",       "No",        "attendance",                  "Primary SQL table"),
        td("METRIC_COLUMN",       "No",        "status",                      "Column holding the measured metric"),
        td("POSITIVE_VALUE",      "No",        "active",                      "Value counted as a positive outcome"),
        td("DATE_COLUMN",         "No",        "date",                        "Date column for time-based filtering"),
        td("ENTITY_COLUMN",       "No",        "entity_id",                   "Primary entity key column"),
        td("ENTITY_NAME_COLUMN",  "No",        "entity_name",                 "Human-readable entity name column"),
        td("GROUP_COLUMNS",       "No",        "(empty)",                     "Comma-separated grouping dimension columns"),
        td("CHROMA_PATH",         "No",        ".chroma",                     "Persistent ChromaDB directory path"),
        td("EMBED_MODEL",         "No",        "BAAI/bge-small-en-v1.5",     "HuggingFace embedding model — auto-downloaded on first run"),
        td("DOCS_PATH",           "No",        "docs",                        "Directory scanned for policy PDFs and Markdown files"),
        td("RAG_CACHE_TTL",       "No",        "3600",                        "TTL in seconds for RAG query result cache"),
        td("MAX_MESSAGE_LEN",     "No",        "2000",                        "Maximum characters per chat message"),
        td("MAX_PROMPT_TOKENS",   "No",        "2048",                        "Maximum estimated tokens before rejection"),
        td("ALLOWED_ORIGINS",     "No",        "http://localhost:5173,…",     "Comma-separated CORS allowed origins"),

    ], [3.8*cm, 2.0*cm, 3.5*cm, cw-9.3*cm]))
    s.append(PageBreak())

    # CH 14 ───────────────────────────────────────────────────────────────────
    s.append(h1("14. Security Model"))
    s.append(h2("14.1 What Is Enforced"))
    s += [
        b("<b>SQL read-only enforcement</b> — sqlglot AST rejects non-SELECT statements; applied exclusively "
          "to LLM-provided SQL via _query()."),
        b("<b>Internal/external boundary</b> — hardcoded internal SQL uses _exec() (no overhead); "
          "LLM-provided SQL must pass _query() with the sqlglot guard."),
        b("<b>Database allowlist</b> — only SQL_DATABASES databases can be queried."),
        b("<b>SQL injection prevention</b> — user-supplied values parameterised; group-by from hardcoded allow-list."),
        b("<b>JWT authentication</b> — all endpoints except /auth/login and /health require a valid JWT."),
        b("<b>Password hashing</b> — bcrypt with per-password salts."),
        b("<b>Rate limiting</b> — 10 req/min/user; Redis-backed across workers when REDIS_URI is set."),
        b("<b>Local inference</b> — all LLM inference on localhost via Ollama; data never leaves the network."),
        b("<b>Timeout enforcement</b> — 240 s backend + 270 s frontend SSE timeout."),
        b("<b>Startup secret check</b> — server refuses to start if JWT_SECRET is still the default."),
    ]
    s.append(h2("14.2 What Is Not Enforced"))
    s.append(note(
        "• No row-level security — all authenticated users see all data.<br/>"
        "• users.json is not encrypted — protect with filesystem permissions (chmod 600).<br/>"
        "• No HTTPS — put Nginx or Caddy in front with TLS termination in production.<br/>"
        "• No audit log — no record of who asked what or ran which SQL queries.<br/>"
        "• No CSRF protection — stateless JWT API; tighten CORS allow-list in production."
    ))
    s.append(PageBreak())

    # CH 15 ───────────────────────────────────────────────────────────────────
    s.append(h1("15. Running the Stack"))
    s.append(h2("15.1 Prerequisites"))
    s += [b("Python 3.11 or later"), b("Node.js 18 or later + npm"),
          b("Ollama installed and running (https://ollama.com)"),
          b("SQL Server accessible from the host machine"),
          b("ODBC Driver 18 for SQL Server installed on the host")]
    s.append(h2("15.2 First-Time Setup"))
    s.append(pre(
        "# 1. Pull the LLM (one-time)\n"
        "ollama pull qwen2.5:14b           # ~8 GB\n"
        "# BAAI/bge-small-en-v1.5 embeddings are auto-downloaded from HuggingFace on first run\n\n"
        "# 2. Configure environment\n"
        "cp .env.example .env\n"
        "# Edit .env: SQL_SERVER, SQL_DATABASES, SQL_USERNAME, SQL_PASSWORD, JWT_SECRET\n\n"
        "# 3. Python virtual environment\n"
        "python -m venv .venv && source .venv/bin/activate\n"
        "pip install -r requirements.lock\n\n"
        "# 4. Frontend\n"
        "cd web && npm install && cd .."
    ))
    s.append(h2("15.3 Starting Both Servers"))
    s.append(pre("bash start.sh\n# FastAPI → http://localhost:8000\n# React   → http://localhost:5173"))
    s.append(h2("15.4 Multi-Worker Deployment"))
    s.append(pre(
        "# SqliteSaver writes to CHAT_DB — all workers share history\n"
        "# Set REDIS_URI to share rate-limit counters:\n"
        "REDIS_URI=redis://localhost:6379 uvicorn api.main:app --workers 4"
    ))
    s.append(PageBreak())

    # CH 16 ───────────────────────────────────────────────────────────────────
    s.append(h1("16. Test Suite"))
    s += [p("Tests in <font face='Courier'>tests/test_qa.py</font>. Two classes:"),
          h2("16.1 Unit Tests — TestZeroKnowledge"),
          p("Call tools directly with a synthetic SampleDataStore. No Ollama, no SQL Server, no network. "
            "Runs in under a second."),
          pre("pytest tests/test_qa.py -v"),
          h2("16.2 Integration Tests — TestModelStress"),
          p("Require a live Ollama instance with qwen2.5:14b. Verify complex queries complete within 120 s "
            "and greetings do not trigger tool calls."),
          pre("pytest tests/test_qa.py -v -m integration\npytest tests/test_qa.py -v --run-all"),
          h2("16.3 Security Tests — test_security.py"),
          p("352-line security-focused test suite in <font face='Courier'>tests/test_security.py</font>. "
            "Covers prompt guard (injection patterns, length cap, token budget), SQL guard "
            "(_assert_select_only: DML rejection, system-schema blocking, multi-statement attacks), "
            "and auth (JWT sign/verify, bcrypt hashing, token expiry). No network or Ollama required."),
          pre("pytest tests/test_security.py -v")]
    s.append(PageBreak())

    # CH 17 ───────────────────────────────────────────────────────────────────
    s.append(h1("17. Extending the System"))
    s += [h2("17.1 Adding a New Database"),
          b("Add to SQL_DATABASES in .env. The RAG ingestor auto-indexes its INFORMATION_SCHEMA on next startup."),
          b("The agent can immediately query it via run_sql_query(sql=..., database='new_db')."),
          h2("17.2 Adding a New Agent Tool")]
    s.append(pre(
        "@tool\ndef my_tool(param: str, config: RunnableConfig = None) -> str:\n"
        '    """Describe the tool — shown to the LLM."""\n'
        "    store = _store(config)\n    ...\n    return result_string"
    ))
    s += [b("Add to ALL_TOOLS in src/tools.py."),
          b("Add description to the Tool usage section of SYSTEM_PROMPT in src/agent.py."),
          h2("17.3 Changing the LLM"),
          p("Set MODEL in .env to any Ollama model supporting tool calling. "
            "Alternatives: llama3.1:8b (faster), mistral-small (smaller context)."),
          h2("17.4 Adding a New Frontend Page"),
          b("Create web/src/pages/MyPage.tsx following existing page patterns."),
          b("Add a route in web/src/App.tsx and a link in Sidebar.tsx."),
          b("If data is needed, add an endpoint in api/routers/ and include_router() in api/main.py."),
          h2("17.5 Adding Per-User Data Filtering"),
          p("UserContext (user_id) is available to all agent calls. To add filtering:"),
          b("Add a user→group mapping table to SQL Server."),
          b("Read user_id from the store or rag_store references in the tool's config dict."),
          b("Pass allowed groups as an additional filter to store methods."),
          h2("17.6 Production Deployment"),
          b("Set JWT_SECRET: <font face='Courier'>openssl rand -hex 32</font>"),
          b("Set ADMIN_PASSWORD to a strong password."),
          b("Build React: <font face='Courier'>cd web && npm run build</font>. Mount via FastAPI StaticFiles."),
          b("Set CHAT_DB to a persistent path: e.g. <font face='Courier'>CHAT_DB=/data/chat.db</font>"),
          b("Set REDIS_URI for shared rate limiting: <font face='Courier'>REDIS_URI=redis://localhost:6379</font>"),
          b("Run: <font face='Courier'>uvicorn api.main:app --workers 4</font> — all workers share SqliteSaver history and Redis rate counters."),
          b("Put Nginx or Caddy in front for TLS."),
          b("<font face='Courier'>chmod 600 api/users.json</font>")]

    doc.build(s, onFirstPage=_tmpl, onLaterPages=_tmpl)
    print("✓  Generated: Excelsis 360 Analyst Agent.pdf")


if __name__ == "__main__":
    build()
