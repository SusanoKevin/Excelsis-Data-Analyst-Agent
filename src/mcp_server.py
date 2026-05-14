"""
Excelsis 360 MCP server. Identity is set at process start via env var:
  MCP_USER_ID — default "mcp_user"
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from src.agent import ExcelsisAgent
from src.security import UserContext
from src.sql_store import SQLAttendanceStore

MCP_USER = UserContext(user_id=os.getenv("MCP_USER_ID", "mcp_user"))

store = SQLAttendanceStore()
agent = ExcelsisAgent(store=store)

mcp = FastMCP(
    name="Excelsis 360 Attendance Analyst",
    instructions=(
        "An AI attendance analyst for Excelsis 360. "
        "Provides attendance statistics and at-risk student lists. "
        f"Connected as user '{MCP_USER.user_id}'."
    ),
)


@mcp.tool()
def ask_analyst(query: str) -> str:
    """
    Ask the Excelsis attendance analyst a natural-language question.
    The agent will reason across multiple tools and return a comprehensive answer.
    Examples: 'Which class has the worst attendance?',
              'Show me at-risk students in 10A',
              'What are the top 5 classes by absences this month?'
    """
    return agent.ask(query, user=MCP_USER)


@mcp.tool()
def attendance_summary() -> str:
    """
    Return a JSON summary of all attendance data:
    record count, unique students, date range, overall rate, and class list.
    """
    return json.dumps(store.summary(), indent=2)


@mcp.tool()
def at_risk_students(threshold: float = 75.0) -> str:
    """
    List students whose attendance rate is below the given threshold (default 75%).
    Returns a table with student ID, name, class, and attendance rate.
    """
    df = store.get_at_risk(threshold=threshold)
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
    df = store.compute_stats(group_by=group_by, period=period)
    return df.to_string(index=False) if not df.empty else "No data available."


if __name__ == "__main__":
    print(f"Starting Excelsis MCP server as '{MCP_USER.user_id}'")
    mcp.run()
