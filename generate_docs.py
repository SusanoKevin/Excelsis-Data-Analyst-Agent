"""
Generate Excelsis 360 documentation PDF using ReportLab.
Run: python generate_docs.py
Output: Excelsis_360_Documentation.pdf
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Preformatted,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import ListFlowable, ListItem

# ── Colour palette ────────────────────────────────────────────────────────────
CARBON     = colors.HexColor("#0d0d0d")
SNOW       = colors.HexColor("#ffffff")
FOG        = colors.HexColor("#f5f5f5")
PEWTER     = colors.HexColor("#5d5d5d")
STONE      = colors.HexColor("#8f8f8f")
LINK_BLUE  = colors.HexColor("#007aff")
ACCENT     = colors.HexColor("#1a1a2e")
MUTED_BLUE = colors.HexColor("#e8f0fe")
BORDER     = colors.HexColor("#e0e0e0")
CODE_BG    = colors.HexColor("#f0f0f0")
WARN       = colors.HexColor("#fff3cd")
WARN_BORD  = colors.HexColor("#ffc107")

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm

# ── Style sheet ──────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

Title = S("DocTitle",
    fontSize=28, leading=34, textColor=CARBON,
    fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_CENTER)

Subtitle = S("DocSubtitle",
    fontSize=13, leading=18, textColor=PEWTER,
    fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4)

ChapterTitle = S("ChapterTitle",
    fontSize=20, leading=26, textColor=CARBON,
    fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=8,
    borderPadding=(0, 0, 6, 0))

SectionTitle = S("SectionTitle",
    fontSize=14, leading=20, textColor=CARBON,
    fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)

SubSection = S("SubSection",
    fontSize=11, leading=16, textColor=CARBON,
    fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)

Body = S("DocBody",
    fontSize=10, leading=15, textColor=CARBON,
    fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6)

BodyLeft = S("BodyLeft",
    fontSize=10, leading=15, textColor=CARBON,
    fontName="Helvetica", alignment=TA_LEFT, spaceAfter=5)

Note = S("Note",
    fontSize=9, leading=13, textColor=PEWTER,
    fontName="Helvetica-Oblique", spaceAfter=4)

CodeStyle = S("Code",
    fontSize=8.5, leading=12, textColor=CARBON,
    fontName="Courier", backColor=CODE_BG,
    leftIndent=12, rightIndent=12,
    borderPadding=(6, 8, 6, 8), spaceAfter=8)

BulletStyle = S("Bullet",
    fontSize=10, leading=15, textColor=CARBON,
    fontName="Helvetica", leftIndent=14, spaceAfter=3)

TableHeader = S("TH",
    fontSize=9, leading=12, textColor=SNOW,
    fontName="Helvetica-Bold", alignment=TA_LEFT)

TableCell = S("TC",
    fontSize=9, leading=13, textColor=CARBON,
    fontName="Helvetica", alignment=TA_LEFT)

TableCellMono = S("TCM",
    fontSize=8.5, leading=12, textColor=CARBON,
    fontName="Courier", alignment=TA_LEFT)

# ── Helpers ──────────────────────────────────────────────────────────────────

def sp(h=8):
    return Spacer(1, h)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8, spaceBefore=4)

def chapter(text):
    return [PageBreak(), Paragraph(text, ChapterTitle), hr()]

def section(text):
    return [Paragraph(text, SectionTitle)]

def subsection(text):
    return [Paragraph(text, SubSection)]

def body(text):
    return Paragraph(text, Body)

def body_left(text):
    return Paragraph(text, BodyLeft)

def note(text):
    return Paragraph(f"<i>{text}</i>", Note)

def bullet_list(items):
    bullets = []
    for item in items:
        bullets.append(Paragraph(f"• {item}", BulletStyle))
    return bullets

def code_block(text):
    return Preformatted(text, CodeStyle)

def simple_table(header, rows, col_widths=None):
    data = [[Paragraph(h, TableHeader) for h in header]]
    for row in rows:
        data.append([Paragraph(str(c), TableCellMono if i == 0 else TableCell)
                     for i, c in enumerate(row)])
    w = col_widths or ([3.5*cm] + [(PAGE_W - MARGIN*2 - 3.5*cm) / (len(header)-1)] * (len(header)-1))
    t = Table(data, colWidths=w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  CARBON),
        ("TEXTCOLOR",   (0,0), (-1,0),  SNOW),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [SNOW, FOG]),
        ("GRID",        (0,0), (-1,-1), 0.35, BORDER),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING",(0,0), (-1,-1), 6),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ]))
    return t

def info_box(title, items, bg=MUTED_BLUE, border=LINK_BLUE):
    content = [Paragraph(f"<b>{title}</b>", BodyLeft)]
    for item in items:
        content.append(Paragraph(f"• {item}", BulletStyle))
    t = Table([[content]], colWidths=[PAGE_W - MARGIN*2])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), bg),
        ("BOX",         (0,0), (-1,-1), 1, border),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING",(0,0), (-1,-1), 10),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
    ]))
    return t

# ── Page template callbacks ───────────────────────────────────────────────────

def header_footer(canvas, doc):
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(CARBON)
    canvas.setLineWidth(0.8)
    canvas.line(MARGIN, PAGE_H - 1.4*cm, PAGE_W - MARGIN, PAGE_H - 1.4*cm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(CARBON)
    canvas.drawString(MARGIN, PAGE_H - 1.2*cm, "Excelsis 360 — Attendance Analyst Agent")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(PEWTER)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 1.2*cm, "Technical Documentation")
    # Footer
    canvas.setLineWidth(0.4)
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN, 1.5*cm, PAGE_W - MARGIN, 1.5*cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(PEWTER)
    canvas.drawString(MARGIN, 1.1*cm, "Confidential · Internal Use")
    canvas.drawRightString(PAGE_W - MARGIN, 1.1*cm, f"Page {doc.page}")
    canvas.restoreState()

def first_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(CARBON)
    canvas.rect(0, PAGE_H - 5.5*cm, PAGE_W, 5.5*cm, fill=1, stroke=0)
    canvas.setFillColor(SNOW)
    canvas.setFont("Helvetica-Bold", 32)
    canvas.drawCentredString(PAGE_W/2, PAGE_H - 2.8*cm, "Excelsis 360")
    canvas.setFont("Helvetica", 14)
    canvas.setFillColor(colors.HexColor("#aaaaaa"))
    canvas.drawCentredString(PAGE_W/2, PAGE_H - 3.5*cm, "Attendance Analyst Agent")
    canvas.setFont("Helvetica", 10)
    canvas.drawCentredString(PAGE_W/2, PAGE_H - 4.3*cm, "Technical Documentation  ·  v1.0")
    # Footer
    canvas.setFillColor(PEWTER)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(PAGE_W/2, 1.2*cm, f"Page {doc.page}")
    canvas.restoreState()

# ── Document content ──────────────────────────────────────────────────────────

def build():
    out = "Excelsis 360 Analyst Agent.pdf"
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.4*cm, bottomMargin=2.2*cm,
        title="Excelsis 360 — Technical Documentation",
        author="Excelsis 360 Engineering",
    )

    story = []

    # ── Cover ────────────────────────────────────────────────────────────────
    story += [
        sp(180),
        Paragraph("Technical Documentation", Subtitle),
        sp(6),
        Paragraph("An AI-powered attendance analysis platform for schools,<br/>built on locally-hosted LLMs, SQL Server, and a React web interface.", Subtitle),
        sp(20),
        hr(),
        sp(6),
        Paragraph("Version 1.0  ·  May 2026", Note),
        PageBreak(),
    ]

    # ── TOC ──────────────────────────────────────────────────────────────────
    story += chapter("Table of Contents")
    toc_items = [
        ("1", "Project Overview", "What Excelsis 360 is, its purpose, and its key capabilities"),
        ("2", "Use Cases", "Scenarios the system is designed to support"),
        ("3", "System Architecture", "High-level design and data flow"),
        ("4", "Technology Stack", "Every library and tool used and why"),
        ("5", "Data Backend — SQLAttendanceStore", "SQL Server integration, caching, and SQL safety"),
        ("6", "AI Agent — ExcelsisAgent", "LangGraph ReAct loop, tools, and streaming"),
        ("7", "Agent Tools", "All 7 tools exposed to the LLM"),
        ("8", "REST API", "FastAPI endpoints, auth, rate limiting, and SSE"),
        ("9", "Authentication & User Management", "JWT, bcrypt, and users.json"),
        ("10", "React Web Interface", "Pages, components, and the design system"),
        ("11", "MCP Server", "Claude Code integration via FastMCP"),
        ("12", "Jupyter Notebook", "Interactive analysis environment"),
        ("13", "Configuration Reference", "All environment variables"),
        ("14", "Security Model", "What is enforced and what is not"),
        ("15", "Running the Stack", "Installation, setup, and operation"),
        ("16", "Test Suite", "Unit and integration tests"),
        ("17", "Extending the System", "How to add databases, tools, and pages"),
    ]
    toc_data = [["#", "Chapter", "Summary"]]
    for num, title, desc in toc_items:
        toc_data.append([num, title, desc])
    story.append(simple_table(
        ["#", "Chapter", "Summary"],
        [(n, t, d) for n, t, d in toc_items],
        col_widths=[1*cm, 5.5*cm, PAGE_W - MARGIN*2 - 6.5*cm]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 1: Project Overview
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("1. Project Overview")

    story.append(body(
        "The Excelsis 360 Analyst Agent is an AI-powered attendance analysis tool built for the Excelsis 360 "
        "platform. It extends the platform's existing data infrastructure with a reasoning AI layer — "
        "combining a locally-hosted large language model (LLM), direct access to Excelsis 360's SQL Server "
        "attendance data, and a dedicated web interface — to give school staff a conversational way to "
        "interrogate attendance records without writing reports or navigating complex dashboards."
    ))
    story.append(sp())
    story.append(body(
        "Where the Excelsis 360 platform manages attendance records and surfaces pre-built reports, the "
        "Analyst Agent sits on top of that data and answers questions in plain English. A teacher can ask "
        "\"which students in 10A are at risk this month?\" and the agent reasons across the data, selects "
        "the right query strategy, and streams back a specific, cited answer — without any hard-coded "
        "report logic and without the user needing to know SQL or navigate pivot tables."
    ))
    story.append(sp())

    story += section("1.1  Core Principles")
    story += bullet_list([
        "<b>Privacy-first.</b> All inference runs locally via Ollama — no attendance data ever leaves the school network.",
        "<b>Read-only data access.</b> The SQL layer enforces SELECT-only queries through both AST-level SQL parsing and allow-listed databases. The AI agent cannot modify, insert, or delete any records.",
        "<b>Transparent reasoning.</b> The streaming interface shows each tool call as it happens, letting staff see exactly which data sources the agent consulted before producing an answer.",
        "<b>Zero speculative statistics.</b> The system prompt instructs the model never to fabricate data — if the data is not in the store, the agent says so explicitly.",
        "<b>Minimal footprint.</b> No cloud dependencies at inference time. The only external service is Ollama running on localhost.",
    ])
    story.append(sp())

    story += section("1.2  Key Features")
    features = [
        ["Natural-language chat", "Ask questions in plain English; the agent reasons and streams the answer token-by-token"],
        ["ReAct reasoning loop", "The model decides which tools to call, in what order, across multiple steps"],
        ["At-risk detection", "Automatic flagging of students below a configurable attendance threshold (default 75%)"],
        ["Ad-hoc SQL", "The agent can write and run T-SQL SELECT queries against any configured database"],
        ["Live dashboard", "Interactive charts: class attendance, weekly trend, status donut, day-of-week bar, trend comparison"],
        ["Agent ↔ dashboard link", "Asking the agent to show a chart updates the dashboard in real time (SSE event)"],
        ["User management", "Admin-controlled user accounts with bcrypt-hashed passwords and JWT tokens"],
        ["MCP server", "Exposes attendance tools directly to Claude Code via the Model Context Protocol"],
        ["Jupyter notebook", "Full interactive analysis environment sharing the same Python backend"],
        ["Rate limiting", "Chat endpoint limited to 10 requests per minute per IP via SlowAPI"],
    ]
    story.append(simple_table(
        ["Feature", "Description"],
        features,
        col_widths=[5*cm, PAGE_W - MARGIN*2 - 5*cm]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 2: Use Cases
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("2. Use Cases")

    story.append(body(
        "Excelsis 360 is built around several concrete workflows that school staff encounter daily. Each "
        "use case maps to one or more agent tools and front-end views."
    ))
    story.append(sp())

    use_cases = [
        (
            "2.1  Daily Attendance Check",
            "A homeroom teacher wants a quick overview of which classes underperformed today or this week.",
            [
                "Open the Chat page and type: \"Which classes had the lowest attendance this week?\"",
                "The agent calls query_attendance with period=last_7_days, group_by=class.",
                "Results are streamed back as a ranked table of classes with attendance rates.",
                "The agent flags any class below 75% as at-risk.",
            ]
        ),
        (
            "2.2  At-Risk Student Identification",
            "A school counsellor needs to identify students who are chronically absent and may need intervention.",
            [
                "Ask: \"List all students below 70% attendance in class 10A.\"",
                "The agent calls get_at_risk_students with threshold=70.0.",
                "A table is returned with student IDs, names, class, total sessions, and attendance rate.",
                "The Dashboard's at-risk panel also shows this data with sparkline trend charts per student.",
            ]
        ),
        (
            "2.3  Trend Analysis",
            "A deputy principal wants to know if attendance has improved or declined over the past month compared to the prior month.",
            [
                "Ask: \"How does attendance this month compare to the previous month?\"",
                "The agent calls compare_periods(period_a='last_30_days', period_b='prior_30_days').",
                "A side-by-side table with a delta column is returned, highlighting classes that improved or declined.",
                "The TrendComparisonChart on the Dashboard visualises this automatically.",
            ]
        ),
        (
            "2.4  Class Comparison",
            "A head of year wants to benchmark two specific classes against each other.",
            [
                "Ask: \"Compare 10A and 10B attendance.\"",
                "The agent calls compare_classes(class_a='10A', class_b='10B').",
                "Both classes are presented side by side with present, absent, late counts and overall rate.",
            ]
        ),
        (
            "2.5  Ad-hoc Reporting",
            "An administrator needs a custom report — for example, absences on Monday across all grades.",
            [
                "Ask: \"Which day of the week has the most absences?\"",
                "The agent calls query_attendance with group_by=day_of_week.",
                "For more complex needs, the agent writes a T-SQL query via run_sql_query.",
                "Example: SELECT DATENAME(dw,date) AS day, COUNT(*) AS absences FROM attendance WHERE status='absent' GROUP BY DATENAME(dw,date) ORDER BY absences DESC",
            ]
        ),
        (
            "2.6  Dashboard-Driven Exploration",
            "A staff member wants to explore data visually rather than through chat.",
            [
                "Navigate to the Dashboard page.",
                "Use the FilterBar to select specific classes and time periods.",
                "Click a bar in the Attendance by Class chart to highlight that class across all charts.",
                "Double-click to drill down to student-level data for that class.",
                "Click a student row to inspect their weekly trend sparkline.",
                "Use 'Ask Excelsis' to open the embedded chat panel and ask follow-up questions — the agent can update the dashboard view directly.",
            ]
        ),
        (
            "2.7  Policy Knowledge",
            "A teacher asks about best-practice intervention strategies for chronic absenteeism.",
            [
                "The agent answers conversationally from its training knowledge without calling any tools.",
                "Responses include evidence-based approaches such as early warning systems, family engagement, and attendance contracts.",
                "This requires no data and demonstrates the dual role of the model: data analyst and domain expert.",
            ]
        ),
        (
            "2.8  Claude Code Integration (MCP)",
            "A developer or power user wants to query attendance data directly from Claude Code.",
            [
                "Start the MCP server: python -m src.mcp_server",
                "Configure Claude Code to connect to the stdio server.",
                "Claude Code can now call ask_analyst, attendance_summary, at_risk_students, and class_statistics as tools.",
                "This enables attendance analysis within AI-assisted development workflows.",
            ]
        ),
    ]

    for title, desc, steps in use_cases:
        story += section(title)
        story.append(body(desc))
        story.append(sp(4))
        story += bullet_list([f"Step {i+1}: {s}" for i, s in enumerate(steps)])
        story.append(sp(6))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 3: System Architecture
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("3. System Architecture")

    story += section("3.1  Request Flow")
    story.append(body(
        "Every user interaction follows the same path through the system. Understanding this flow "
        "is key to understanding how all the components fit together."
    ))
    story.append(sp(6))

    flow_data = [
        ["Layer", "Component", "Technology", "Role"],
        ["1. Browser", "React App", "React 18 + Vite", "Renders UI, manages auth token, opens SSE stream"],
        ["2. HTTP/SSE", "Fetch / Axios", "Browser Fetch API", "POST /chat/stream → EventSource-style reader"],
        ["3. API Gateway", "FastAPI", "Python / Uvicorn", "JWT validation, rate limiting, request routing"],
        ["4. Agent", "ExcelsisAgent", "LangGraph ReAct", "Maintains conversation history, streams LLM events"],
        ["5. LLM", "phi4:14b", "Ollama / ChatOllama", "Reasons about which tools to call and in what order"],
        ["6. Tools", "7 LangGraph tools", "Python functions", "Execute SQL queries and compute statistics"],
        ["7. Data Store", "SQLAttendanceStore", "pyodbc / SQL Server", "Read-only T-SQL queries with TTL cache"],
        ["8. Database", "SQL Server", "ODBC Driver 18", "Primary attendance table + optional extra databases"],
    ]
    story.append(simple_table(
        ["Layer", "Component", "Technology", "Role"],
        [r[1:] for r in flow_data[1:]],
        col_widths=[3.5*cm, 3.5*cm, 3.5*cm, PAGE_W - MARGIN*2 - 10.5*cm]
    ))
    story.append(sp(8))

    story += section("3.2  Component Diagram (textual)")
    story.append(code_block(
"""Browser (React :5173)
  │
  │  POST /chat/stream  (Bearer JWT)
  │  GET  /data/summary, /data/at-risk, /data/stats …
  ▼
FastAPI (:8000)
  ├── /auth/*        JWT sign/verify, user CRUD
  ├── /chat/stream   SSE — delegates to ExcelsisAgent.astream_events()
  └── /data/*        Direct SQLAttendanceStore queries (no LLM)

ExcelsisAgent  (LangGraph ReAct)
  ├── ChatOllama ─── phi4:14b @ http://localhost:11434
  ├── Conversation history (last 10 turns)
  └── 7 tools ──────────────────────────────────────────────────────────┐
                                                                        │
SQLAttendanceStore (read-only)                           Tools          │
  ├── _assert_select_only()  ← sqlglot AST guard         ◄─────────────┘
  ├── _TTLCache (5-min TTL)
  └── pyodbc ─── SQL Server
        ├── primary_db  (attendance table)
        └── extra_db_1, extra_db_2, …  (allowlisted)

MCP Server (stdio)
  └── FastMCP ─── ExcelsisAgent + SQLAttendanceStore
        ├── ask_analyst()
        ├── attendance_summary()
        ├── at_risk_students()
        └── class_statistics()
"""
    ))

    story += section("3.3  Streaming Architecture")
    story.append(body(
        "The chat endpoint uses Server-Sent Events (SSE) to stream the agent's output to the browser "
        "incrementally. The event types emitted are:"
    ))
    events = [
        ["{\"type\": \"token\", \"content\": \"…\"}", "One LLM output token — appended to the current message bubble"],
        ["{\"type\": \"tool_start\", \"tool\": \"…\"}", "An agent tool call has started — UI shows a spinner badge"],
        ["{\"type\": \"tool_end\", \"tool\": \"…\"}", "The tool call returned — spinner removed"],
        ["{\"type\": \"dashboard_filter\", …}", "Agent called update_dashboard_view — Dashboard state updates live"],
        ["{\"type\": \"error\", \"message\": \"…\"}", "Timeout or model error — displayed as an error message"],
        ["{\"type\": \"done\"}", "Stream complete — UI unlocks the input field"],
    ]
    story.append(simple_table(
        ["SSE Event", "Frontend Action"],
        events,
        col_widths=[8*cm, PAGE_W - MARGIN*2 - 8*cm]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 4: Technology Stack
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("4. Technology Stack")

    story.append(body(
        "Every library in the stack was chosen for a specific reason. The guiding principle was "
        "to keep the dependency surface small while covering all required functionality."
    ))
    story.append(sp(6))

    stack = [
        ["phi4:14b", "Ollama", "LLM", "14B parameter model; strong tool-calling and instruction-following; fits on a single consumer GPU or Apple Silicon Mac"],
        ["LangGraph", "langgraph", "Agent framework", "ReAct loop with built-in conversation state, tool routing, and async event streaming"],
        ["langchain-ollama", "langchain-ollama", "LLM bridge", "ChatOllama wraps Ollama's HTTP API with LangChain's standard interface"],
        ["FastAPI", "fastapi", "Web framework", "Async, schema-validated, auto-docs; minimal boilerplate for REST + SSE"],
        ["pyodbc", "pyodbc", "SQL driver", "ODBC 18 for SQL Server; cross-platform; supports Windows Auth, SQL Auth, and Azure AD"],
        ["sqlglot", "sqlglot", "SQL parser", "AST-level SELECT-only enforcement; rejects INSERT/UPDATE/DELETE/DDL at parse time"],
        ["pandas", "pandas", "Data wrangling", "DataFrames used for all intermediate computation (stats, pivots, merges)"],
        ["python-jose", "python-jose", "JWT", "HS256 token signing and verification; 24-hour token TTL"],
        ["bcrypt", "bcrypt", "Password hashing", "bcrypt with per-password salt; stored in users.json"],
        ["SlowAPI", "slowapi", "Rate limiting", "10 chat requests/minute/IP; wraps FastAPI with Redis-free in-memory limiter"],
        ["FastMCP", "mcp", "MCP server", "stdio-based Model Context Protocol server for Claude Code tool integration"],
        ["React 18", "react", "Frontend framework", "Component-based UI with hooks; Vite for build and HMR"],
        ["Tailwind CSS v4", "tailwindcss", "Styling", "Utility-first CSS; custom design tokens (carbon, snow, fog, pewter)"],
        ["Recharts", "recharts", "Charts", "Responsive SVG charts: bar, line, donut, area"],
        ["Axios", "axios", "HTTP client", "Auto-attaches JWT; 401 → redirect to login"],
        ["React Router v6", "react-router-dom", "Client routing", "SPA navigation; ProtectedRoute component enforces auth"],
    ]
    story.append(simple_table(
        ["Library", "Package", "Layer", "Why chosen"],
        stack,
        col_widths=[3*cm, 3.5*cm, 2.5*cm, PAGE_W - MARGIN*2 - 9*cm]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 5: Data Backend
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("5. Data Backend — SQLAttendanceStore")

    story.append(body(
        "SQLAttendanceStore is the single source of truth for all attendance data. It is a read-only "
        "wrapper around a SQL Server database that provides four public methods used by both the API "
        "routes and the agent tools. It lives in src/sql_store.py."
    ))
    story.append(sp())

    story += section("5.1  Database Schema")
    story.append(body(
        "The store expects a primary table named attendance in the configured primary database. "
        "Additional databases can be queried via the database parameter of run_sql_query."
    ))
    story.append(code_block(
"""CREATE TABLE attendance (
    student_id   INT           NOT NULL,
    student_name NVARCHAR(200),
    class        NVARCHAR(50),
    grade        NVARCHAR(20),
    date         DATE          NOT NULL,
    status       VARCHAR(10)   NOT NULL   -- 'present' | 'absent' | 'late' | 'excused'
);"""
    ))
    story.append(body(
        "The schema is flexible — the agent will adapt its T-SQL to whatever schema it discovers "
        "at runtime via run_sql_query. The structured tools (query_attendance, get_at_risk_students) "
        "assume the column names above."
    ))
    story.append(sp())

    story += section("5.2  SQL Safety")
    story.append(body(
        "Every query executed by the store passes through _assert_select_only(), which uses sqlglot "
        "to parse the SQL into an abstract syntax tree (AST) and reject any statement that is not "
        "a single SELECT. The following statement types are explicitly blocked:"
    ))
    story += bullet_list([
        "INSERT — cannot add records",
        "UPDATE — cannot modify records",
        "DELETE — cannot remove records",
        "DROP — cannot remove tables or databases",
        "CREATE — cannot create objects",
        "ALTER — cannot change schema",
        "TRUNCATE — cannot clear tables",
        "MERGE — blocked to prevent upsert-style attacks",
        "Command — raw EXEC/xp_cmdshell etc. blocked",
        "Multiple statements — only a single SELECT per call",
    ])
    story.append(sp(4))
    story.append(body(
        "Additionally, every database accessed must be explicitly listed in the SQL_DATABASES "
        "environment variable. Queries against unlisted databases raise a PermissionError."
    ))
    story.append(sp())
    story.append(info_box(
        "SQL Injection Prevention",
        [
            "All user-supplied values (class names, date bounds, thresholds) are passed as parameterized query parameters via pyodbc — never string-interpolated into SQL.",
            "Only the group-by column expression is built from a hardcoded allow-list dict (_GROUP_EXPR) — never from user input.",
            "The sqlglot AST check catches multi-statement attacks (SELECT 1; DROP TABLE …) even if the parameterization were somehow bypassed.",
        ]
    ))
    story.append(sp())

    story += section("5.3  TTL Cache")
    story.append(body(
        "SQLAttendanceStore includes a simple in-process TTL cache (_TTLCache) with a 5-minute "
        "expiry. Both compute_stats() and get_at_risk() check the cache before hitting SQL Server. "
        "The cache key encodes all query parameters (group_by, period, classes, date bounds) so "
        "different filter combinations are cached independently. This reduces SQL Server load when "
        "multiple users view the same dashboard simultaneously."
    ))
    story.append(sp())

    story += section("5.4  Public Methods")
    methods = [
        ["summary()", "Returns a dict with total_records, unique_students, date_range, overall_attendance_rate, total_absences, and classes list"],
        ["compute_stats(group_by, period, classes, date_from, date_to)", "Returns a DataFrame aggregated by the requested dimension and period; used by query_attendance, compare_periods, compare_classes, and the /data/stats endpoint"],
        ["get_at_risk(threshold, classes, date_from, date_to)", "Returns a DataFrame of students below the threshold, ordered by attendance rate ascending"],
        ["student_weekly_rates(student_ids, weeks)", "Returns a dict mapping student_id → list of weekly attendance rates (last N weeks); used for sparkline charts"],
    ]
    story.append(simple_table(
        ["Method", "Description"],
        methods,
        col_widths=[5.5*cm, PAGE_W - MARGIN*2 - 5.5*cm]
    ))

    story += section("5.5  Connection Management")
    story.append(body(
        "Each call to _query() opens a new pyodbc connection and closes it in a finally block. "
        "This avoids connection pool state issues across async workers but means one SQL Server "
        "round-trip per query. For high-traffic deployments, a connection pool (e.g. SQLAlchemy "
        "with pool_size) should be considered, but this is not needed for typical school-size loads."
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 6: AI Agent
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("6. AI Agent — ExcelsisAgent")

    story.append(body(
        "ExcelsisAgent is the intelligence layer of Excelsis 360. It wraps a LangGraph ReAct "
        "(Reasoning + Acting) agent powered by phi4:14b running locally via Ollama. The agent "
        "decides which tools to call, in what order, based on the user's question and the "
        "results of previous tool calls."
    ))
    story.append(sp())

    story += section("6.1  The ReAct Loop")
    story.append(body(
        "ReAct is a prompting pattern that interleaves Reasoning (thinking about what to do) and "
        "Acting (calling a tool or producing output). LangGraph implements this as a graph with "
        "two nodes — llm and tools — that alternate until the model decides to stop:"
    ))
    story.append(code_block(
"""User message
    │
    ▼
LLM node  (phi4:14b)
    │ Decides to call a tool?
    ├── YES ──► Tools node  (runs the tool, returns result)
    │               │
    │               └──────► LLM node  (sees tool result, decides again)
    │
    └── NO  ──► Final answer  (streamed token-by-token to the browser)"""
    ))
    story.append(sp(6))
    story.append(body(
        "This loop repeats until the model emits a final AIMessage with no further tool calls. "
        "LangGraph manages the message list automatically, including injecting tool results as "
        "ToolMessage objects."
    ))
    story.append(sp())

    story += section("6.2  System Prompt")
    story.append(body(
        "The agent receives a fixed system prompt that defines its persona, responsibilities, and "
        "tool usage rules. Key instructions include:"
    ))
    story += bullet_list([
        "Identity: \"Expert School Attendance Analyst for Excelsis 360\"",
        "Data integrity: never fabricate statistics; say so if data is unavailable",
        "Threshold: flag any class or student below 75% as at-risk",
        "Efficiency: call tools immediately — never narrate a tool call before making it",
        "SQL rules: T-SQL syntax only; SELECT-only; use TOP, DATEPART, FORMAT, CONVERT, ISNULL",
        "Dashboard rules: call update_dashboard_view when the user asks to see a chart or visual",
        "Conversation: answer greetings and general questions directly without calling tools",
    ])
    story.append(sp())

    story += section("6.3  Conversation History")
    story.append(body(
        "ExcelsisAgent maintains a rolling conversation history of up to 10 turns (20 messages: "
        "10 human + 10 AI). The last 10 messages are prepended to every new request, giving the "
        "model context for follow-up questions. History can be cleared via the 'Clear history' "
        "button in the Chat UI, which calls reset_history()."
    ))
    story.append(sp())

    story += section("6.4  Timeout Handling")
    story.append(body(
        "Both the synchronous ask() method and the async astream_events() generator enforce a "
        "90-second timeout. If the LLM does not complete within this window, the request fails "
        "gracefully with a user-facing message rather than hanging indefinitely. The synchronous "
        "path uses a daemon thread + threading.Event; the async path uses asyncio.timeout()."
    ))
    story.append(sp())

    story += section("6.5  LLM Configuration")
    story.append(body("The ChatOllama instance is configured with:"))
    llm_config = [
        ["model", "phi4:14b (default; overridden by MODEL env var)"],
        ["base_url", "http://localhost:11434 (Ollama's default port)"],
        ["temperature", "0.1 (low temperature for consistent, factual responses)"],
        ["num_ctx", "8192 tokens context window"],
        ["keep_alive", "10 minutes (model stays loaded in VRAM between requests)"],
    ]
    story.append(simple_table(
        ["Parameter", "Value / Description"],
        llm_config,
        col_widths=[4*cm, PAGE_W - MARGIN*2 - 4*cm]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 7: Agent Tools
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("7. Agent Tools")

    story.append(body(
        "The agent has access to 7 tools defined in src/tools.py. Each tool is a Python function "
        "decorated with @tool from LangChain. The docstring is the tool description shown to the LLM. "
        "All tools receive a RunnableConfig from LangGraph that carries the SQLAttendanceStore instance."
    ))
    story.append(sp())

    tools_detail = [
        (
            "query_attendance",
            "Answer a natural-language question about attendance statistics.",
            "query: str",
            "Parses the question for group_by (class, week, month, day_of_week, student_id, grade) and period (all, last_7_days, last_30_days) keywords, then calls store.compute_stats(). Returns a formatted DataFrame string.",
            ["\"attendance by class\"", "\"weekly trend last 30 days\"", "\"which grade has lowest rate?\""],
        ),
        (
            "get_at_risk_students",
            "Return students whose attendance rate is below a threshold.",
            "threshold: float = 75.0",
            "Calls store.get_at_risk(threshold). Returns a table of student_id, name, class, total, present, absent, late, attendance_rate ordered by rate ascending.",
            ["get_at_risk_students(threshold=70.0)"],
        ),
        (
            "get_summary",
            "Return a high-level overview of all attendance data.",
            "(none)",
            "Calls store.summary() and returns the result as a JSON string. Includes total_records, unique_students, date_range, overall_attendance_rate, total_absences, classes.",
            ["get_summary()"],
        ),
        (
            "update_dashboard_view",
            "Update the live dashboard to show a specific view or filter.",
            "classes: list[str], period: str, view: str",
            "Validates and returns a JSON payload. The SSE layer in ExcelsisAgent detects this tool's output and emits a dashboard_filter event to the browser, which updates the React dashboard state without any page reload.",
            ["update_dashboard_view(classes=[\"10A\"], view=\"class\")", "update_dashboard_view(period=\"last_30_days\", view=\"overview\")"],
        ),
        (
            "run_sql_query",
            "Execute an ad-hoc T-SQL SELECT query.",
            "sql: str, database: str = \"\"",
            "Passes the SQL through _assert_select_only() and the database allowlist check, then executes via store._query(). Automatically adds TOP 200 if no TOP clause is present. Returns up to 200 rows as a formatted table.",
            ["SELECT TOP 10 class, COUNT(*) AS absences FROM attendance WHERE status='absent' GROUP BY class ORDER BY absences DESC"],
        ),
        (
            "compare_periods",
            "Compare attendance rates between two time periods.",
            "period_a: str, period_b: str",
            "Calls compute_stats() twice (once per period), merges on class, and computes a delta column. Returns a side-by-side table.",
            ["compare_periods(period_a='last_7_days', period_b='last_30_days')"],
        ),
        (
            "compare_classes",
            "Compare attendance statistics for two classes side by side.",
            "class_a: str, class_b: str",
            "Calls compute_stats() with classes=[class_a, class_b]. Returns a table showing total, present, absent, late, and rate for each class.",
            ["compare_classes(class_a='10A', class_b='10B')"],
        ),
    ]

    for tool_name, purpose, params, impl, examples in tools_detail:
        story += subsection(tool_name)
        story.append(body(f"<b>Purpose:</b> {purpose}"))
        story.append(body(f"<b>Parameters:</b> {params}"))
        story.append(body(f"<b>Implementation:</b> {impl}"))
        if examples:
            story.append(body("<b>Example calls:</b>"))
            for ex in examples:
                story.append(code_block(ex))
        story.append(sp(4))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 8: REST API
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("8. REST API")

    story.append(body(
        "The FastAPI backend is available at http://localhost:8000. Interactive OpenAPI docs are "
        "at http://localhost:8000/docs. All endpoints except /auth/login and /health require a "
        "valid Bearer JWT in the Authorization header."
    ))
    story.append(sp())

    story += section("8.1  Endpoints")
    endpoints = [
        ["POST", "/auth/login", "None", "Username + password → JWT access token (24h TTL)"],
        ["GET", "/auth/me", "Any user", "Returns current user's username"],
        ["GET", "/auth/users", "Admin", "List all registered usernames"],
        ["POST", "/auth/users", "Admin", "Create a new user account"],
        ["DELETE", "/auth/users/{username}", "Admin", "Delete a user (cannot delete 'admin')"],
        ["POST", "/chat/stream", "Any user", "SSE streaming chat — delegates to ExcelsisAgent.astream_events()"],
        ["GET", "/data/summary", "Any user", "Attendance data overview (calls store.summary())"],
        ["GET", "/data/at-risk", "Any user", "At-risk student list (threshold, classes, date_from, date_to params)"],
        ["GET", "/data/stats", "Any user", "Aggregated stats (group_by, period, classes, date_from, date_to params)"],
        ["GET", "/data/trends", "Any user", "Current and prior 30-day weekly stats for trend comparison chart"],
        ["GET", "/data/sparklines", "Any user", "Weekly rates for a list of student IDs (ids= CSV param)"],
        ["GET", "/health", "None", "Returns {\"status\": \"ok\"} — liveness probe"],
    ]
    story.append(simple_table(
        ["Method", "Path", "Auth", "Description"],
        endpoints,
        col_widths=[1.5*cm, 5*cm, 2.5*cm, PAGE_W - MARGIN*2 - 9*cm]
    ))

    story.append(sp(8))
    story += section("8.2  Rate Limiting")
    story.append(body(
        "The POST /chat/stream endpoint is limited to 10 requests per minute per IP address "
        "using SlowAPI (a FastAPI-compatible port of Flask-Limiter). Exceeding the limit returns "
        "HTTP 429 with a Retry-After value. The rate limiter is in-process (no Redis required) — "
        "counters reset when the server restarts."
    ))
    story.append(sp())

    story += section("8.3  CORS")
    story.append(body(
        "CORS is configured to allow requests from http://localhost:5173 (Vite dev server) and "
        "http://localhost:3000. In production, the React app is served as static files by FastAPI "
        "itself (via StaticFiles mount), eliminating the CORS requirement entirely."
    ))
    story.append(sp())

    story += section("8.4  Application Lifecycle")
    story.append(body(
        "FastAPI's lifespan context manager handles startup and shutdown. On startup:"
    ))
    story += bullet_list([
        "ensure_default_admin() creates the admin account in users.json if it doesn't exist.",
        "SQLAttendanceStore() is instantiated and stored on app.state.store.",
        "ExcelsisAgent(store=store) is instantiated and stored on app.state.agent.",
        "_validate_startup() checks Ollama reachability and SQL Server connectivity, printing a status table.",
    ])
    story.append(body(
        "The store and agent are shared across all requests via app.state — there is one instance "
        "per process. The agent's conversation history is shared across users in single-process "
        "deployments (this is intentional for a single-school use case)."
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 9: Authentication & User Management
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("9. Authentication & User Management")

    story += section("9.1  User Store")
    story.append(body(
        "Users are stored in api/users.json as a flat dict mapping username → bcrypt hash. "
        "On first startup, ensure_default_admin() creates the admin account with the password "
        "from the ADMIN_PASSWORD env var (default: admin123). File writes use an atomic "
        "write-then-rename pattern (write to .tmp, then os.replace) to prevent corruption under concurrent writes."
    ))
    story.append(sp())
    story.append(code_block(
"""{
  "admin": {
    "hashed_password": "$2b$12$..."
  },
  "ms_johnson": {
    "hashed_password": "$2b$12$..."
  }
}"""
    ))
    story.append(sp())

    story += section("9.2  JWT Tokens")
    story.append(body(
        "Tokens are HS256 JWTs signed with JWT_SECRET. They contain two claims:"
    ))
    story += bullet_list([
        "sub — the username (used to reconstruct UserContext on each request)",
        "exp — expiry timestamp (24 hours from issuance)",
    ])
    story.append(body(
        "decode_token() reconstructs a UserContext(user_id=username) from the token on every "
        "authenticated request. There is no token refresh mechanism — the user must re-login after 24 hours."
    ))
    story.append(sp())

    story += section("9.3  UserContext")
    story.append(body(
        "UserContext is a minimal Python dataclass with a single field: user_id (the username string). "
        "It is threaded through all agent and tool calls via LangGraph's RunnableConfig so that "
        "tools can theoretically filter data by user. In the current implementation, there is no "
        "row-level filtering — all authenticated users see all data. The UserContext exists to make "
        "adding per-user filtering straightforward in the future."
    ))
    story.append(sp())

    story += section("9.4  Admin Operations")
    story.append(body(
        "The 'admin' account is the only user that can access the Users management page and the "
        "/auth/users endpoints. The admin account cannot be deleted. New users can be created or "
        "deleted by the admin at any time. There is no password reset flow — an admin must delete "
        "and recreate the account."
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 10: React Web Interface
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("10. React Web Interface")

    story.append(body(
        "The frontend is a React 18 single-page application built with Vite and styled with "
        "Tailwind CSS v4. It follows a clean two-column layout (sidebar + main content) inspired "
        "by modern productivity tools."
    ))
    story.append(sp())

    story += section("10.1  Pages")
    pages = [
        ["Login (/login)", "Public", "Username + password form. POSTs to /auth/login, stores JWT in localStorage, redirects to /dashboard."],
        ["Chat (/chat)", "Authenticated", "Natural-language chat interface. Streams responses token-by-token. Shows tool-use indicators. Displays contextual suggestion chips on first load."],
        ["Dashboard (/dashboard)", "Authenticated", "KPI cards + 5 interactive charts + at-risk student table + drilldown panel. Embeddable chat panel ('Ask Excelsis') can update dashboard filters live."],
        ["Users (/users)", "Admin only", "List, create, and delete user accounts. Admin cannot delete themselves."],
    ]
    story.append(simple_table(
        ["Page", "Access", "Description"],
        pages,
        col_widths=[3.5*cm, 2.5*cm, PAGE_W - MARGIN*2 - 6*cm]
    ))
    story.append(sp(8))

    story += section("10.2  Key Components")
    components = [
        ["Sidebar", "Left navigation with links to Chat, Dashboard, Users (admin only), and a logout button"],
        ["MessageBubble", "Renders a single chat turn. User messages align right; agent messages align left with markdown rendering. Shows tool-use badges (e.g. 'Querying attendance data…')."],
        ["ChatPanel", "Embedded chat panel on the Dashboard page. Same functionality as the Chat page but in a slide-in panel. Passes dashboard_filter events to the parent Dashboard."],
        ["FilterBar", "Class multi-select and period dropdown. Changing either triggers a fresh data fetch for all dashboard charts."],
        ["Breadcrumb", "Shows the current drill level (Overview → Class → Student). Click to navigate back up."],
        ["DrilldownPanel", "Renders class-level or student-level detail depending on drill state. Student view shows a sparkline trend chart."],
        ["AttendanceByClassChart", "Horizontal bar chart of attendance rate by class. Single-click filters; double-click drills down."],
        ["WeeklyTrendChart", "Line chart of weekly attendance rate over the selected period."],
        ["StatusDonutChart", "Donut chart of present / absent / late / excused proportions."],
        ["WeekdayBarChart", "Bar chart of attendance rate by day of week."],
        ["TrendComparisonChart", "Grouped bar chart comparing current vs prior 30-day periods per class."],
        ["ProtectedRoute", "HOC that redirects unauthenticated users to /login."],
    ]
    story.append(simple_table(
        ["Component", "Description"],
        components,
        col_widths=[4.5*cm, PAGE_W - MARGIN*2 - 4.5*cm]
    ))
    story.append(sp(8))

    story += section("10.3  Design System")
    story.append(body(
        "The UI uses a minimal achromatic palette with a single accent colour. All design tokens "
        "are defined as Tailwind CSS custom properties:"
    ))
    design_tokens = [
        ["carbon", "#0d0d0d", "Primary text, headings, icons, filled buttons"],
        ["snow", "#ffffff", "Page backgrounds, card surfaces"],
        ["fog", "#f9f9f9", "Secondary backgrounds, sidebar, input fields, chart cards"],
        ["arctic-mist", "#ececec", "Borders, dividers, hover backgrounds"],
        ["pewter", "#5d5d5d", "Secondary text, placeholders, captions"],
        ["stone", "#8f8f8f", "Tertiary text, inactive icons"],
        ["link-blue", "#007aff", "Focus rings, interactive accents"],
    ]
    story.append(simple_table(
        ["Token", "Hex", "Usage"],
        design_tokens,
        col_widths=[3*cm, 2.5*cm, PAGE_W - MARGIN*2 - 5.5*cm]
    ))
    story.append(sp(6))

    story += section("10.4  SSE Client Implementation")
    story.append(body(
        "The browser does not use the EventSource API (which doesn't support POST requests). "
        "Instead, streamChat() in web/src/api/client.ts uses the Fetch API with response.body "
        "as a ReadableStream. It reads chunks, splits on newlines, strips the 'data: ' prefix, "
        "and dispatches each event type to the appropriate callback."
    ))
    story.append(sp())

    story += section("10.5  Authentication Flow")
    story += bullet_list([
        "JWT is stored in localStorage under the key 'token'.",
        "The Axios instance (api/client.ts) automatically attaches it as 'Authorization: Bearer …' on every request.",
        "On 401 responses, the interceptor clears localStorage and redirects to /login.",
        "ProtectedRoute reads the token from localStorage — if absent, it redirects to /login immediately without hitting the server.",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 11: MCP Server
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("11. MCP Server")

    story.append(body(
        "The Model Context Protocol (MCP) server exposes Excelsis 360's capabilities to AI-assisted "
        "development tools — primarily Claude Code. It runs as a stdio-based process, meaning it "
        "reads from stdin and writes to stdout using the MCP wire protocol. Identity is set at "
        "process startup via the MCP_USER_ID environment variable."
    ))
    story.append(sp())

    story += section("11.1  Exposed Tools")
    mcp_tools = [
        ["ask_analyst(query)", "Ask the full ExcelsisAgent a natural-language question. The agent reasons across all 7 internal tools and returns a comprehensive answer. This is the most powerful MCP tool."],
        ["attendance_summary()", "Returns a JSON summary (record count, students, date range, overall rate, classes). Fast — no LLM involved."],
        ["at_risk_students(threshold)", "Lists students below the given attendance threshold as a formatted table. Default threshold: 75%."],
        ["class_statistics(group_by, period)", "Returns attendance stats grouped by class, week, month, day_of_week, student_id, or grade, for the specified period."],
    ]
    story.append(simple_table(
        ["Tool Signature", "Description"],
        mcp_tools,
        col_widths=[5*cm, PAGE_W - MARGIN*2 - 5*cm]
    ))
    story.append(sp(8))

    story += section("11.2  Starting the MCP Server")
    story.append(code_block(
"""# From the project root with .venv active:
MCP_USER_ID=ms_johnson python -m src.mcp_server

# Or with the default user (mcp_user):
python -m src.mcp_server"""
    ))
    story.append(body(
        "The server uses the same .env configuration as the web stack — SQL_SERVER, SQL_DATABASES, "
        "SQL_USERNAME, SQL_PASSWORD, and MODEL must all be set."
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 12: Jupyter Notebook
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("12. Jupyter Notebook")

    story.append(body(
        "Excelsis.ipynb provides a fully interactive analysis environment. It shares the same "
        "src/ Python backend as the web application, so analysts get the same tools and agent "
        "but in a cell-by-cell exploration format."
    ))
    story.append(sp())

    story += section("12.1  Notebook Cells")
    cells = [
        ["1", "Setup & imports", "Load environment variables, import src modules"],
        ["2", "Connectivity check", "Verify Ollama is running at http://localhost:11434; fail fast if not"],
        ["3", "Connect to SQL Server", "Instantiate SQLAttendanceStore and print summary"],
        ["4", "Data summary", "Call store.summary() and display as a formatted dict"],
        ["5", "Set analyst identity", "Set CURRENT_USER = UserContext(user_id='...') — determines the identity used for all agent calls"],
        ["6", "Agent setup", "Instantiate ExcelsisAgent(store=store) with the SQL backend"],
        ["7", "Chat interface", "Call agent.ask(query, user=CURRENT_USER) for natural-language queries"],
        ["8", "Tool calls directly", "Call individual tools (query_attendance, get_at_risk_students, etc.) bypassing the LLM"],
        ["9", "Visualisations", "Generate Plotly charts and matplotlib dashboards from the store data"],
    ]
    story.append(simple_table(
        ["Cell", "Name", "Description"],
        cells,
        col_widths=[1.2*cm, 4*cm, PAGE_W - MARGIN*2 - 5.2*cm]
    ))
    story.append(sp(8))

    story += section("12.2  Changing the Analyst Identity")
    story.append(body(
        "Edit CURRENT_USER in Cell 5 to simulate a different staff member:"
    ))
    story.append(code_block(
"""CURRENT_USER = UserContext(user_id="ms_johnson")
# or
CURRENT_USER = UserContext(user_id="admin")"""
    ))
    story.append(body(
        "In the current implementation, all users see all data. Setting CURRENT_USER primarily "
        "affects the agent's conversation context and would enable per-user data filtering if "
        "such logic were added to the tools."
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 13: Configuration Reference
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("13. Configuration Reference")

    story.append(body(
        "All configuration is via environment variables, typically set in .env (loaded by "
        "python-dotenv at startup). The .env.example file documents all variables."
    ))
    story.append(sp(6))

    env_vars = [
        ["SQL_SERVER", "Yes", "—", "SQL Server hostname, IP, or named instance (e.g. myserver\\SQLEXPRESS)"],
        ["SQL_DATABASES", "Yes", "—", "Comma-separated list of databases the agent is allowed to query"],
        ["SQL_USERNAME", "If sql auth", "—", "SQL Server login username"],
        ["SQL_PASSWORD", "If sql auth", "—", "SQL Server login password"],
        ["SQL_PRIMARY_DB", "No", "First in SQL_DATABASES", "Default database for queries that don't specify one"],
        ["SQL_AUTH_METHOD", "No", "sql", "Authentication method: sql | windows | azure_ad"],
        ["SQL_DRIVER", "No", "{ODBC Driver 18 for SQL Server}", "ODBC driver string"],
        ["JWT_SECRET", "Yes (prod)", "change-me-in-production", "Secret key for JWT signing — MUST be changed in production"],
        ["ADMIN_PASSWORD", "No", "admin123", "Initial password for the admin account (only used on first startup)"],
        ["MODEL", "No", "phi4:14b", "Ollama model name for the ReAct agent"],
        ["AT_RISK_THRESHOLD", "No", "75.0", "Default attendance percentage threshold for at-risk flagging"],
        ["MCP_USER_ID", "No", "mcp_user", "Username used by the MCP server process"],
    ]
    story.append(simple_table(
        ["Variable", "Required", "Default", "Description"],
        env_vars,
        col_widths=[4*cm, 2*cm, 3.5*cm, PAGE_W - MARGIN*2 - 9.5*cm]
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 14: Security Model
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("14. Security Model")

    story += section("14.1  What Is Enforced")
    story += bullet_list([
        "<b>SQL read-only enforcement</b> — sqlglot AST parsing rejects any non-SELECT statement at the store layer, before the query reaches SQL Server.",
        "<b>Database allowlist</b> — only databases listed in SQL_DATABASES can be queried; all others raise a PermissionError.",
        "<b>SQL injection prevention</b> — all user-supplied values are parameterized; group-by columns come from a hardcoded allow-list.",
        "<b>JWT authentication</b> — all API endpoints except /auth/login and /health require a valid, unexpired JWT.",
        "<b>Password hashing</b> — all passwords are bcrypt-hashed with per-password salts; plaintext passwords are never stored.",
        "<b>Rate limiting</b> — chat endpoint is limited to 10 requests/minute/IP to prevent abuse.",
        "<b>Local inference</b> — all LLM inference runs on localhost via Ollama; attendance data never leaves the network.",
        "<b>Timeout enforcement</b> — 90-second hard timeout on all agent calls prevents hanging requests.",
    ])
    story.append(sp())

    story += section("14.2  What Is Not Enforced")
    story.append(info_box(
        "Known Limitations",
        [
            "No row-level security — all authenticated users see all student data. There is no per-teacher or per-class access control.",
            "Shared agent history — a single ExcelsisAgent instance serves all users; conversation history is shared across sessions in single-process deployments.",
            "users.json is not encrypted — the file contains bcrypt hashes which are computationally expensive to crack, but the file should be protected by filesystem permissions.",
            "No HTTPS — the server runs plain HTTP by default. In production, put Nginx or Caddy in front with TLS termination.",
            "No audit log — there is no record of which user asked which questions or ran which SQL queries.",
            "JWT_SECRET default — the default 'change-me-in-production' secret must be changed before any production deployment.",
            "No CSRF protection — the API is stateless (JWT, no cookies) so traditional CSRF does not apply, but the CORS allow-list should be tightened in production.",
        ],
        bg=WARN, border=WARN_BORD
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 15: Running the Stack
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("15. Running the Stack")

    story += section("15.1  Prerequisites")
    story += bullet_list([
        "Python 3.11 or later",
        "Node.js 18 or later + npm",
        "Ollama installed and running (https://ollama.com)",
        "SQL Server accessible from the host machine",
        "ODBC Driver 18 for SQL Server installed on the host",
    ])
    story.append(sp())

    story += section("15.2  First-Time Setup")
    story.append(code_block(
"""# 1. Pull the LLM (one-time, ~8GB download)
ollama pull phi4:14b

# 2. Copy and configure environment
cp .env.example .env
# Edit .env: set SQL_SERVER, SQL_DATABASES, SQL_USERNAME, SQL_PASSWORD, JWT_SECRET

# 3. Python virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.lock   # use lock file for reproducible installs

# 4. Frontend dependencies
cd web && npm install && cd .."""
    ))
    story.append(sp())

    story += section("15.3  Starting Both Servers")
    story.append(code_block(
"""bash start.sh
# FastAPI  → http://localhost:8000
# React    → http://localhost:5173
# Press Ctrl-C to stop both"""
    ))
    story.append(sp())

    story += section("15.4  Starting Servers Individually")
    story.append(code_block(
"""# Backend only
source .venv/bin/activate
uvicorn api.main:app --reload

# Frontend only (separate terminal)
cd web && npm run dev"""
    ))
    story.append(sp())

    story += section("15.5  Default Login")
    story += bullet_list([
        "URL: http://localhost:5173",
        "Username: admin",
        "Password: value of ADMIN_PASSWORD in .env (default: admin123)",
    ])
    story.append(sp())

    story += section("15.6  Startup Validation Output")
    story.append(body(
        "On startup, the backend prints a validation summary:"
    ))
    story.append(code_block(
"""────────────────────────────────────────────────────
  Excelsis 360 — startup
  Model:      phi4:14b                 OK
  SQL Server: myserver                 OK
  Databases:  attendance_db,reports_db
────────────────────────────────────────────────────"""
    ))
    story.append(body(
        "UNREACHABLE indicates either Ollama is not running (check: ollama list) or "
        "SQL Server credentials are incorrect."
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 16: Test Suite
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("16. Test Suite")

    story.append(body(
        "Tests live in tests/test_qa.py. The suite is split into two classes with distinct "
        "requirements:"
    ))
    story.append(sp())

    story += section("16.1  Unit Tests — TestZeroKnowledge")
    story.append(body(
        "These tests call LangGraph tools directly with a synthetic AttendanceDataStore seeded "
        "from a pandas DataFrame. No Ollama, no SQL Server, no network required. They run in "
        "under a second and verify:"
    ))
    story += bullet_list([
        "query_attendance returns data containing expected class names",
        "get_summary returns JSON with required keys (total_records, overall_attendance_rate)",
        "Tools return a graceful message when no store is connected",
        "get_at_risk_students correctly identifies students below the threshold",
        "update_dashboard_view returns valid JSON with the expected payload shape",
    ])
    story.append(code_block("pytest tests/test_qa.py -v"))
    story.append(sp())

    story += section("16.2  Integration Tests — TestModelStress")
    story.append(body(
        "These tests require a live Ollama instance with phi4:14b loaded. They verify:"
    ))
    story += bullet_list([
        "A multi-part complex query completes within 120 seconds and returns >50 characters",
        "A greeting does not trigger tool calls and returns a conversational response",
    ])
    story.append(code_block(
"""pytest tests/test_qa.py -v -m integration   # integration tests only
pytest tests/test_qa.py -v --run-all         # everything"""
    ))

    # ════════════════════════════════════════════════════════════════════════
    # Chapter 17: Extending the System
    # ════════════════════════════════════════════════════════════════════════
    story += chapter("17. Extending the System")

    story += section("17.1  Adding a New Database")
    story += bullet_list([
        "Add the database name to SQL_DATABASES in .env (comma-separated).",
        "The agent can immediately query it via run_sql_query(sql=..., database='new_db').",
        "Update the system prompt in src/agent.py to tell the model what tables are available in the new database.",
    ])
    story.append(sp())

    story += section("17.2  Adding a New Agent Tool")
    story.append(body("1. Define a function in src/tools.py and decorate it with @tool:"))
    story.append(code_block(
"""@tool
def my_new_tool(param: str, config: RunnableConfig = None) -> str:
    \"\"\"Describe what the tool does — this is shown to the LLM.\"\"\"
    store = _store(config)
    ...
    return result_string"""
    ))
    story.append(body("2. Add it to ALL_TOOLS in src/tools.py."))
    story.append(body("3. Add a description to the Tool usage section of SYSTEM_PROMPT in src/agent.py."))
    story.append(sp())

    story += section("17.3  Changing the LLM")
    story.append(body(
        "Any Ollama-hosted model that supports tool calling can be used. "
        "Set MODEL in .env. The model must support function/tool calling — "
        "check the Ollama model page for 'tools' support. Recommended alternatives: "
        "llama3.1:8b (faster, less accurate), mistral-small (smaller context), qwen2.5:14b."
    ))
    story.append(sp())

    story += section("17.4  Adding a New Frontend Page")
    story += bullet_list([
        "Create web/src/pages/MyPage.tsx following the pattern of existing pages.",
        "Add a route in web/src/App.tsx: <Route path='/mypage' element={<ProtectedRoute><MyPage /></ProtectedRoute>} />",
        "Add a link in web/src/components/Sidebar.tsx.",
        "If the page needs data, add a new endpoint in api/routers/ and include_router() in api/main.py.",
    ])
    story.append(sp())

    story += section("17.5  Adding Per-User Data Filtering")
    story.append(body(
        "UserContext is already threaded through every tool call via RunnableConfig. "
        "To add per-user filtering:"
    ))
    story += bullet_list([
        "In SQLAttendanceStore, add a user_id column to the attendance table and a user→classes mapping.",
        "In each tool, extract user_id from config['configurable']['user_context'].user_id.",
        "Pass allowed classes as an additional filter to store._query().",
        "No changes to the agent or API layer are needed.",
    ])
    story.append(sp())

    story += section("17.6  Production Deployment")
    story += bullet_list([
        "Set JWT_SECRET to a long random string (e.g. openssl rand -hex 32).",
        "Set ADMIN_PASSWORD to a strong password.",
        "Build the React app: cd web && npm run build",
        "Mount the built files via FastAPI StaticFiles — remove the CORS middleware.",
        "Run uvicorn with --workers 4 (multiple workers share the same SQL store but have separate agent instances and conversation histories).",
        "Put Nginx or Caddy in front for TLS termination.",
        "Restrict users.json file permissions: chmod 600 api/users.json",
    ])

    # ── Build ────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=first_page, onLaterPages=header_footer)
    print(f"✓ PDF written to {out}")


if __name__ == "__main__":
    build()
