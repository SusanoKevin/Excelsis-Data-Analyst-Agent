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
import os
from typing import Optional

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

    p = parse_attendance_query(query)
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
    vec = config["configurable"].get("vector_store")
    if vec is None:
        return "Vector store not initialised."

    if collection == "records":
        security.require(user, Permission.READ_OWN_CLASSES, "vector_records")
        allowed = user.allowed_classes if user.allowed_classes else None
        docs = vec.search_records(query, k=4, allowed_classes=allowed)
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

    # Restrict visible classes for non-admin users
    if user.allowed_classes and "classes" in summary:
        summary["classes"] = [c for c in summary["classes"] if c in user.allowed_classes]

    return json.dumps(summary, indent=2)


# ---------------------------------------------------------------------------
# Tool: web_search
# ---------------------------------------------------------------------------

@tool
def web_search(query: str, config: RunnableConfig = None) -> str:
    """
    Search the web for attendance best practices, interventions, or research.
    Use this when you need external knowledge not in the local database.
    """
    user = _user(config)
    security.require(user, Permission.WEB_SEARCH, "tavily")

    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        return "TAVILY_API_KEY not set — web search unavailable."

    from langchain_community.tools.tavily_search import TavilySearchResults

    results = TavilySearchResults(api_key=key, max_results=3).invoke(query)
    if not results:
        return "No results found."
    return "\n---\n".join(
        f"{r.get('url', '')}\n{r.get('content', '')[:500]}" for r in results
    )


# ---------------------------------------------------------------------------
# Exported tool list
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    query_attendance,
    get_at_risk_students,
    search_knowledge_base,
    get_summary,
    web_search,
]
