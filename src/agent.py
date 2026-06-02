from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import sqlite3
import threading

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

from .prompt_guard import check_token_budget
from .security import ADMIN_USER, UserContext
from .tools import ALL_TOOLS
from .tracker import QueryTracker

logger = logging.getLogger(__name__)

_INVALID_HISTORY_MARKERS = (
    "ToolMessage",
    "INVALID_CHAT_HISTORY",
    "tool_calls that do not have a corresponding",
)


def _is_invalid_history_error(exc: Exception) -> bool:
    msg = str(exc)
    return any(marker in msg for marker in _INVALID_HISTORY_MARKERS)


SYSTEM_PROMPT = """You are an expert Data Analyst for Excelsis 360.

Guidelines:
- Be specific: name groups and entities when data is available
- If you cannot find data, say so clearly — never fabricate statistics
- Think step-by-step: retrieve data first, then analyse
- For greetings or general questions, answer directly without calling tools

Tool usage:
- query_data           — metric statistics grouped by a configured dimension
                         (leave group_by empty for default, or specify 'week', 'month', 'day_of_week', entity column)
- get_threshold_alerts — entities below a metric threshold
- statistical_summary  — distribution stats (mean, std, min, max, percentiles) across all groups
- detect_anomalies     — groups/entities whose metric_rate deviates significantly from the mean
- get_top_n            — top or bottom N groups ranked by metric_rate
- analyze_trend        — week-over-week trend direction, slope, and weekly breakdown
- update_dashboard_view — update the live dashboard to show a specific view or filter
- get_summary          — quick data overview (total records, date range, overall metric rate)
- run_sql_query        — ad-hoc T-SQL SELECT against any configured database
- compare_periods      — compare metric rates between two time periods
- compare_segments     — compare metric statistics for two segments side by side
- retrieve_schema      — look up table and column definitions from the schema knowledge base
- retrieve_policy      — search policy and rule documents

Analytical approach:
- "What's wrong?" or "Where are issues?": start with detect_anomalies, then get_top_n(ascending=True)
- "Show the trend" or "Is it getting better/worse?": use analyze_trend
- "Give me a summary" or "Overview": use statistical_summary for distribution, get_summary for totals
- When a data tool returns results, they are shown as a table directly to the user. Do NOT list or repeat the data values in prose. Instead, provide brief analysis: highlight key patterns, outliers, or insights from the table.
- Always interpret results — name specific groups, state what the numbers mean, flag what needs attention
- For ad-hoc SQL: call retrieve_schema first to confirm table and column names, then run_sql_query

Schema and policy retrieval:
- Call retrieve_schema BEFORE run_sql_query — especially for non-primary databases.
- Call retrieve_policy when the user asks about rules, thresholds, consequences,
  exemptions, or procedures — any question whose answer is in a policy document.

Dashboard rules (update_dashboard_view):
- Call this when the user asks to see a chart, visual, or dashboard view
- segments: list of segment names to focus on (omit or [] for all)
- period:   'all' | 'last_7_days' | 'last_30_days'
- view:     'overview' | 'group' | 'entity'
- Examples:
    update_dashboard_view(segments=["segment_a"], view="group")
    update_dashboard_view(period="last_30_days", view="overview")

SQL query rules (run_sql_query):
- Write valid T-SQL (SQL Server syntax): use TOP, DATEPART, DATENAME, FORMAT, CONVERT, ISNULL
- Always use SELECT — never INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER
- Always call retrieve_schema first to confirm the primary table name and column names

CRITICAL: Call tools immediately — NEVER output text like "I will use X tool" or
"Let me call X" before calling it. Narrating a tool call instead of making one is
an error.
"""

_TIMEOUT = 240

_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_api_key  = os.environ.get("OLLAMA_API_KEY", "")

_llm = ChatOllama(
    model=os.environ.get("MODEL", "qwen2.5:14b"),
    base_url=_base_url,
    headers={"Authorization": f"Bearer {_api_key}"} if _api_key else {},
    temperature=0.1,
    num_ctx=8192,
    keep_alive="10m",
)


class ExcelsisAgent:
    def __init__(self, store=None, rag_store=None, checkpointer=None) -> None:
        if checkpointer is None:
            _conn = sqlite3.connect(os.getenv("CHAT_DB", "./chat.db"), check_same_thread=False)
            checkpointer = SqliteSaver(_conn)
        self._graph = create_react_agent(
            model=_llm,
            tools=ALL_TOOLS,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
            checkpointer=checkpointer,
        )
        self._store     = store
        self._rag_store = rag_store

    def _clear_thread(self, thread_id: str) -> None:
        """Delete all checkpoint rows for a thread to recover from corrupted state."""
        db_path = os.getenv("CHAT_DB", "./chat.db")
        tables = ("checkpoint_writes", "checkpoint_blobs", "checkpoints")
        with sqlite3.connect(db_path, timeout=10) as conn:
            for table in tables:
                try:
                    conn.execute(f"DELETE FROM {table} WHERE thread_id = ?", (thread_id,))
                except sqlite3.OperationalError:
                    pass
            conn.commit()
        logger.warning("Cleared corrupted checkpoint history for thread_id=%s", thread_id)

    def _build_config(self, user: UserContext) -> dict:
        return {
            "configurable": {
                "thread_id": user.user_id,
                "store":     self._store,
                "rag_store": self._rag_store,
            }
        }

    def _prepare(self, message: str, user: UserContext | None) -> tuple[dict, list]:
        user = user or ADMIN_USER
        check_token_budget(message)
        return self._build_config(user), [HumanMessage(content=message)]

    def ask(self, query: str, user: UserContext | None = None) -> str:
        config, messages = self._prepare(query, user)
        tracker = QueryTracker()
        tracker.start((user or ADMIN_USER).user_id, query)
        thread_id = config["configurable"]["thread_id"]
        result_q: queue.Queue = queue.Queue()

        def _run() -> None:
            try:
                result_q.put(("ok", self._graph.invoke({"messages": messages}, config=config)))
            except Exception as e:
                if _is_invalid_history_error(e):
                    self._clear_thread(thread_id)
                    try:
                        result_q.put(("ok", self._graph.invoke({"messages": messages}, config=config)))
                        return
                    except Exception as retry_exc:
                        result_q.put(("err", retry_exc))
                        return
                logger.exception("Agent invoke failed for user=%s", thread_id)
                result_q.put(("err", e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=_TIMEOUT)

        if t.is_alive():
            tracker.record_error()
            tracker.finish()
            return "Sorry, the request timed out. The model may be busy — please try again."

        status, value = result_q.get()
        if status == "err":
            tracker.record_error()
            tracker.finish()
            raise value

        final  = value["messages"][-1]
        answer = final.content if isinstance(final, AIMessage) else str(final)
        tracker.finish()
        return answer

    async def astream_events(self, message: str, user: UserContext | None = None):
        config, messages = self._prepare(message, user)
        tracker = QueryTracker()
        tracker.start((user or ADMIN_USER).user_id, message)
        thread_id = config["configurable"]["thread_id"]
        retried = False

        try:
            async with asyncio.timeout(_TIMEOUT):
                while True:
                    try:
                        async for event in self._graph.astream_events(
                            {"messages": messages},
                            config=config,
                            version="v2",
                        ):
                            kind = event.get("event", "")

                            if kind == "on_chat_model_stream":
                                chunk = event.get("data", {}).get("chunk")
                                if chunk and hasattr(chunk, "content") and chunk.content:
                                    yield {"type": "token", "content": chunk.content}

                            elif kind == "on_tool_start":
                                name = event.get("name", "")
                                tracker.record_tool(name)
                                yield {"type": "tool_start", "tool": name}

                            elif kind == "on_tool_end":
                                name = event.get("name", "")
                                yield {"type": "tool_end", "tool": name}
                                raw = event.get("data", {}).get("output")
                                if name == "update_dashboard_view":
                                    output = raw.content if hasattr(raw, "content") else str(raw)
                                    try:
                                        payload = json.loads(output)
                                        yield {
                                            "type":    "dashboard_filter",
                                            "classes": payload.get("segments", []),
                                            "period":  payload.get("period", "all"),
                                            "view":    payload.get("view", "overview"),
                                        }
                                    except (json.JSONDecodeError, AttributeError):
                                        pass
                                artifact = getattr(raw, "artifact", None)
                                if isinstance(artifact, dict) and "columns" in artifact:
                                    yield {"type": "tool_data", "tool": name, **artifact}
                        break  # stream completed successfully
                    except ValueError as exc:
                        if not retried and _is_invalid_history_error(exc):
                            retried = True
                            await asyncio.to_thread(self._clear_thread, thread_id)
                            logger.warning(
                                "Retrying after clearing invalid checkpoint for thread_id=%s",
                                thread_id,
                            )
                            continue
                        raise

        except asyncio.TimeoutError:
            tracker.record_error()
            yield {"type": "error", "message": "Request timed out. The model may be busy — please try again."}
            return

        finally:
            tracker.finish()
