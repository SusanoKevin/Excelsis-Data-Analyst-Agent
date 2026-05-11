"""
Excelsis 360 MCP server. Identity is set at process start via env vars:
  MCP_USER_ID        – default "mcp_user"
  MCP_USER_ROLE      – admin|teacher|counselor|viewer  (default: "viewer")
  MCP_ALLOWED_CLASSES – pipe-separated classes, e.g. "10A|10B"  (default: all)
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

# Add project root to path so `src.*` imports work when called with -m
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from src.agent import ExcelsisAgent
from src.data_store import AttendanceDataStore
from src.security import AccessDeniedError, Role, UserContext, security, Permission
from src.vector_store import AttendanceVectorStore

def _build_mcp_user() -> UserContext:
    uid   = os.getenv("MCP_USER_ID", "mcp_user")
    role  = os.getenv("MCP_USER_ROLE", "viewer").lower()
    classes_raw = os.getenv("MCP_ALLOWED_CLASSES", "")
    allowed = [c.strip() for c in classes_raw.split("|") if c.strip()]
    try:
        r = Role(role)
    except ValueError:
        r = Role.VIEWER
    return UserContext(user_id=uid, role=r, allowed_classes=allowed)


MCP_USER = _build_mcp_user()

_DATA_PATH = os.getenv("ATTENDANCE_DATA_PATH", "./data/attendance")
_CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma_db")

store = AttendanceDataStore(data_path=_DATA_PATH if Path(_DATA_PATH).exists() else None)
vec   = AttendanceVectorStore(persist_dir=_CHROMA_PATH)
vec.index_store_summaries(store)
agent = ExcelsisAgent(store=store, vector_store=vec)

mcp = FastMCP(
    name="Excelsis 360 Attendance Analyst",
    instructions=(
        "An AI attendance analyst for Excelsis 360. "
        "Provides attendance statistics, at-risk student lists, "
        "intervention recommendations, and dashboard generation. "
        f"Connected as user '{MCP_USER.user_id}' with role '{MCP_USER.role.value}'."
    ),
)


def _check(permission: Permission, resource: str = "") -> None:
    """Raise RuntimeError (surfaced as MCP error) if access is denied."""
    try:
        security.require(MCP_USER, permission, resource)
    except AccessDeniedError as e:
        raise RuntimeError(str(e)) from e


@mcp.tool()
def ask_analyst(query: str) -> str:
    """
    Ask the Excelsis attendance analyst a natural-language question.
    The agent will reason across multiple tools and return a comprehensive answer.
    Examples: 'Which class has the worst attendance?',
              'Show me at-risk students in 10A',
              'What interventions work for chronic absenteeism?'
    """
    _check(Permission.READ_OWN_CLASSES, "ask_analyst")
    return agent.ask(query, user=MCP_USER)


@mcp.tool()
def attendance_summary() -> str:
    """
    Return a JSON summary of all loaded attendance data:
    record count, unique students, date range, overall rate, and class list.
    """
    _check(Permission.READ_OWN_CLASSES, "summary")
    summary = store.summary()
    if MCP_USER.allowed_classes and "classes" in summary:
        summary["classes"] = [c for c in summary["classes"] if c in MCP_USER.allowed_classes]
    return json.dumps(summary, indent=2)


@mcp.tool()
def at_risk_students(threshold: float = 75.0) -> str:
    """
    List students whose attendance rate is below the given threshold (default 75%).
    Returns a table with student ID, name, class, and attendance rate.
    """
    _check(Permission.READ_AT_RISK, "at_risk")
    df = store.get_at_risk(threshold=threshold, grade="all")
    df = security.filter_df(df, MCP_USER)
    if df.empty:
        return f"No students below {threshold}% threshold."
    return df.to_string(index=False)


@mcp.tool()
def class_statistics(group_by: str = "class", period: str = "all") -> str:
    """
    Return attendance statistics grouped by a dimension.
    group_by options : class | week | month | day_of_week | student_id | grade
    period options   : all | last_7_days | last_30_days
    """
    _check(Permission.READ_OWN_CLASSES, f"stats:{group_by}")
    df = store.compute_stats(group_by=group_by, period=period)
    df = security.filter_df(df, MCP_USER)
    return df.to_string(index=False) if not df.empty else "No data available."


@mcp.tool()
def search_policies(query: str) -> str:
    """
    Search the knowledge base for attendance policies, interventions, and best practices.
    Example queries: 'chronic absenteeism strategies', 'parent engagement tips'
    """
    docs = vec.search_policies(query, k=3)
    return vec.format_docs(docs)


@mcp.tool()
def search_attendance_records(query: str) -> str:
    """
    Semantic search over indexed class attendance summaries.
    Results are restricted to classes the current user may access.
    """
    _check(Permission.READ_OWN_CLASSES, "vector_records")
    allowed = MCP_USER.allowed_classes if MCP_USER.allowed_classes else None
    docs = vec.search_records(query, k=4, allowed_classes=allowed)
    return vec.format_docs(docs)


@mcp.tool()
def audit_log() -> str:
    """
    Return the security audit log (admin only).
    Shows every data access attempt with timestamp, user, permission, and result.
    """
    _check(Permission.VIEW_AUDIT_LOG, "audit_log")
    entries = security.audit_log()
    if not entries:
        return "No audit entries."
    lines = ["timestamp            | user      | role      | perm                  | resource  | granted"]
    lines += ["-" * 90]
    for e in entries[-100:]:
        ts = datetime.datetime.fromtimestamp(e["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(
            f"{ts} | {e['user']:<9} | {e['role']:<9} | {e['perm']:<21} | {e['resource']:<9} | {e['granted']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Starting Excelsis MCP server as '{MCP_USER.user_id}' ({MCP_USER.role.value})")
    mcp.run()
