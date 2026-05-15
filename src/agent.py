from __future__ import annotations

import json
import os

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .security import ADMIN_USER, UserContext
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an expert School Attendance Analyst for Excelsis 360.

Guidelines:
- Always flag any class or student below 75% as "at-risk"
- Be specific: name classes and students when data is available
- If you cannot find data, say so clearly — never fabricate statistics
- Think step-by-step: retrieve data first, then analyse
- For greetings or general questions, answer directly without calling tools

Tool usage:
- query_attendance       — attendance statistics grouped by class, grade, week, month, or day
- get_at_risk_students   — students below an attendance threshold
- update_dashboard_view  — update the live dashboard to show a specific view or filter
- get_summary            — quick data overview (total records, date range, overall rate)
- run_sql_query          — ad-hoc T-SQL SELECT against any configured database

Dashboard rules (update_dashboard_view):
- Call this when the user asks to see a chart, visual, or dashboard view
- classes: list of class names to focus on (omit or [] for all classes)
- period:  'all' | 'last_7_days' | 'last_30_days'
- view:    'overview' | 'class' | 'student'
- Examples:
    update_dashboard_view(classes=["10A"], view="class")
    update_dashboard_view(period="last_30_days", view="overview")

SQL query rules (run_sql_query):
- Write valid T-SQL (SQL Server syntax): use TOP, DATEPART, DATENAME, FORMAT, CONVERT, ISNULL
- Always use SELECT — never INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER
- Primary attendance table: `attendance`
  Columns: student_id, student_name, class, grade, date (DATE), status ('present'|'absent'|'late'|'excused')
- Other databases available via the `database` parameter
- Example: SELECT TOP 20 class, COUNT(*) AS absences
           FROM attendance WHERE status='absent' AND date >= DATEADD(dd,-30,GETDATE())
           GROUP BY class ORDER BY absences DESC

CRITICAL: Call tools immediately — NEVER output text like "I will use X tool" or
"Let me call X" before calling it. Narrating a tool call instead of making one is
an error.
"""


_llm = ChatOllama(
    model=os.environ.get("MODEL", "mistral-small:22b"),
    base_url="http://localhost:11434",
    temperature=0.1,
    num_ctx=8192,
    keep_alive="10m",
)


class ExcelsisAgent:
    def __init__(self, store=None, max_history: int = 10) -> None:
        self._graph = create_react_agent(
            model=_llm,
            tools=ALL_TOOLS,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        self._store       = store
        self._history: list = []
        self._max_history  = max_history

    def _build_config(self, user: UserContext) -> dict:
        return {
            "configurable": {
                "user_context": user,
                "store":        self._store,
            }
        }

    def _append_history(self, human: str, ai: str) -> None:
        self._history.append(HumanMessage(content=human))
        self._history.append(AIMessage(content=ai))
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2):]

    def ask(self, query: str, user: UserContext | None = None) -> str:
        user     = user or ADMIN_USER
        config   = self._build_config(user)
        messages = list(self._history[-self._max_history:]) + [HumanMessage(content=query)]
        result   = self._graph.invoke({"messages": messages}, config=config)
        final    = result["messages"][-1]
        answer   = final.content if isinstance(final, AIMessage) else str(final)
        self._append_history(query, answer)
        return answer

    async def astream_events(self, message: str, user: UserContext | None = None):
        """
        Async generator yielding SSE-ready dicts.

        Event types:
          {"type": "token",     "content": "..."}
          {"type": "tool_start","tool":    "..."}
          {"type": "tool_end",  "tool":    "..."}
          {"type": "dashboard_filter", "classes": [...], "period": "...", "view": "..."}
        """
        user     = user or ADMIN_USER
        config   = self._build_config(user)
        messages = list(self._history[-self._max_history:]) + [HumanMessage(content=message)]
        full     = ""

        async for event in self._graph.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full += chunk.content
                    yield {"type": "token", "content": chunk.content}

            elif kind == "on_tool_start":
                yield {"type": "tool_start", "tool": event.get("name", "")}

            elif kind == "on_tool_end":
                name = event.get("name", "")
                yield {"type": "tool_end", "tool": name}
                if name == "update_dashboard_view":
                    raw = event.get("data", {}).get("output", "")
                    output = raw.content if hasattr(raw, "content") else str(raw)
                    try:
                        payload = json.loads(output)
                        yield {
                            "type":    "dashboard_filter",
                            "classes": payload.get("classes", []),
                            "period":  payload.get("period", "all"),
                            "view":    payload.get("view", "overview"),
                        }
                    except (json.JSONDecodeError, AttributeError):
                        pass

        self._append_history(message, full)

    def reset_history(self) -> None:
        self._history.clear()
