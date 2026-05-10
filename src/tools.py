"""
LangGraph tool definitions.

Each tool receives its UserContext through LangGraph's RunnableConfig:
    config["configurable"]["user_context"]

Security is enforced at two levels:
  1. Permission check  (SecurityManager.require)  — raises if the user lacks the right
  2. Data-level filter (SecurityManager.filter_df) — strips inaccessible rows before return
"""

from __future__ import annotations

import json

import pandas as pd
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from .security import (
    ADMIN_USER,
    Permission,
    UserContext,
    security,
)


# ---------------------------------------------------------------------------
# Helper: pull UserContext from LangGraph config
# ---------------------------------------------------------------------------

def _user(config: RunnableConfig) -> UserContext:
    return config.get("configurable", {}).get("user_context", ADMIN_USER)


def _df_to_text(df: pd.DataFrame, max_rows: int = 50) -> str:
    if df is None or df.empty:
        return "No data available."
    return df.head(max_rows).to_string(index=False)


# ---------------------------------------------------------------------------
# Tool: query_attendance
# ---------------------------------------------------------------------------

@tool
def query_attendance(
    query: str,
    config: RunnableConfig,
) -> str:
    """
    Answer a question about attendance statistics.
    Supports grouping by class, week, month, day_of_week, student, or grade.
    Supports periods: all, last_7_days, last_30_days.
    Examples: 'attendance by class', 'weekly trend last 30 days', 'which grade has lowest rate?'
    """
    from .data_store import parse_attendance_query

    user = _user(config)
    security.require(user, Permission.READ_OWN_CLASSES, "attendance_stats")

    store = config["configurable"].get("store")
    if store is None:
        return "No data store connected."

    p  = parse_attendance_query(query)
    df = store.compute_stats(p["group_by"], p["period"])
    df = security.filter_df(df, user)
    return _df_to_text(df)


# ---------------------------------------------------------------------------
# Tool: get_at_risk_students
# ---------------------------------------------------------------------------

@tool
def get_at_risk_students(
    threshold: float = 75.0,
    config: RunnableConfig = None,
) -> str:
    """
    Return students whose attendance rate is below the given threshold (default 75%).
    Includes student ID, name (if available), class, and attendance rate.
    """
    user = _user(config)
    security.require(user, Permission.READ_AT_RISK, "at_risk_list")

    store = config["configurable"].get("store")
    if store is None:
        return "No data store connected."

    df = store.get_at_risk(threshold=threshold, grade="all")
    df = security.filter_df(df, user)
    if df.empty:
        return f"No students below {threshold}% attendance threshold."
    return _df_to_text(df)


# ---------------------------------------------------------------------------
# Tool: search_knowledge_base
# ---------------------------------------------------------------------------

@tool
def search_knowledge_base(
    query: str,
    collection: str = "policies",
    config: RunnableConfig = None,
) -> str:
    """
    Semantic search over the vector knowledge base.
    collection='policies'  – intervention strategies and best practices (no auth required)
    collection='records'   – class attendance summaries (restricted to user's classes)
    """
    user = _user(config)
    vec  = config["configurable"].get("vector_store")
    if vec is None:
        return "Vector store not initialised."

    if collection == "records":
        security.require(user, Permission.READ_OWN_CLASSES, "vector_records")
        allowed = user.allowed_classes if user.allowed_classes else None
        docs    = vec.search_records(query, k=4, allowed_classes=allowed)
    else:
        docs = vec.search_policies(query, k=3)

    return vec.format_docs(docs)


# ---------------------------------------------------------------------------
# Tool: get_summary
# ---------------------------------------------------------------------------

@tool
def get_summary(config: RunnableConfig = None) -> str:
    """
    Return a high-level summary of all loaded attendance data:
    total records, unique students, date range, overall attendance rate, and classes.
    """
    user = _user(config)
    security.require(user, Permission.READ_OWN_CLASSES, "summary")

    store = config["configurable"].get("store")
    if store is None:
        return "No data store connected."

    summary = store.summary()
    if user.allowed_classes and "classes" in summary:
        summary["classes"] = [c for c in summary["classes"] if c in user.allowed_classes]

    return json.dumps(summary, indent=2)


# ---------------------------------------------------------------------------
# Tool: generate_dashboard
# ---------------------------------------------------------------------------

@tool
def generate_dashboard(
    chart_type: str = "full",
    group_by: str = "class",
    period: str = "all",
    title: str = "",
    config: RunnableConfig = None,
) -> str:
    """
    Generate a query-specific attendance chart and save it as a PNG.

    chart_type: 'full' (4-panel overview), 'class_bar', 'weekly_trend',
                'weekday_bar', 'status_donut', 'at_risk_bar', 'grade_bar'
    group_by:   column to group by — 'class' | 'week' | 'month' | 'day_of_week' | 'grade'
    period:     'all' | 'last_7_days' | 'last_30_days'
    title:      descriptive chart title (auto-generated if blank)

    Returns the URL path to the saved PNG, e.g. /dashboards/a1b2c3d4.png
    """
    import uuid as _uuid
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path as _Path
    from .dashboard import build_query_dashboard

    user = _user(config)
    security.require(user, Permission.GENERATE_DASHBOARD, "dashboard")

    store = config["configurable"].get("store")
    if store is None:
        return "No data store connected."

    classes = user.allowed_classes if user.allowed_classes else None
    fig = build_query_dashboard(
        store,
        chart_type=chart_type,
        group_by=group_by,
        period=period,
        title=title,
        classes=classes,
    )

    out_dir  = _Path("data/dashboards")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"dashboard_{_uuid.uuid4().hex[:8]}.png"
    fig.savefig(str(out_dir / filename), dpi=140, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)

    return f"/dashboards/{filename}"


# ---------------------------------------------------------------------------
# Exported tool list
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    query_attendance,
    get_at_risk_students,
    search_knowledge_base,
    get_summary,
    generate_dashboard,
]
