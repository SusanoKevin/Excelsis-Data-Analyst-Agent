from __future__ import annotations

import json
import re

import pandas as pd
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool


def parse_attendance_query(question: str) -> dict:
    q = question.lower()
    group_by = "class"
    if "week"    in q: group_by = "week"
    elif "month" in q: group_by = "month"
    elif "day"   in q: group_by = "day_of_week"
    elif "student" in q: group_by = "student_id"
    elif "grade" in q: group_by = "grade"
    period = "all"
    if "last 7" in q or "this week"  in q: period = "last_7_days"
    elif "last 30" in q or "this month" in q: period = "last_30_days"
    return {"group_by": group_by, "period": period}


def _df_to_text(df: pd.DataFrame, max_rows: int = 50) -> str:
    if df.empty:
        return "No data available."
    return df.head(max_rows).to_string(index=False)


def _store(config: RunnableConfig):
    return config["configurable"].get("store")


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
    store = _store(config)
    if store is None:
        return "No data store connected."

    p  = parse_attendance_query(query)
    df = store.compute_stats(p["group_by"], p["period"])
    return _df_to_text(df)


@tool
def get_at_risk_students(
    threshold: float = 75.0,
    config: RunnableConfig = None,
) -> str:
    """
    Return students whose attendance rate is below the given threshold (default 75%).
    Includes student ID, name (if available), class, and attendance rate.
    """
    store = _store(config)
    if store is None:
        return "No data store connected."

    df = store.get_at_risk(threshold=threshold)
    if df.empty:
        return f"No students below {threshold}% attendance threshold."
    return _df_to_text(df)


@tool
def get_summary(config: RunnableConfig = None) -> str:
    """
    Return a high-level summary of all loaded attendance data:
    total records, unique students, date range, overall attendance rate, and classes.
    """
    store = _store(config)
    if store is None:
        return "No data store connected."

    return json.dumps(store.summary(), indent=2)


@tool
def update_dashboard_view(
    classes: list[str] | None = None,
    period: str = "all",
    view: str = "overview",
    config: RunnableConfig = None,
) -> str:
    """
    Update the live dashboard to show a specific view.

    classes: list of class names to filter by (empty list = all classes)
    period:  'all' | 'last_7_days' | 'last_30_days'
    view:    'overview' | 'class' | 'student'

    Examples:
      update_dashboard_view(classes=["10A"], view="class")
      update_dashboard_view(period="last_30_days")
    """
    safe_period = period if period in {"all", "last_7_days", "last_30_days"} else "all"
    safe_view   = view   if view   in {"overview", "class", "student"}      else "overview"
    return json.dumps({"classes": classes or [], "period": safe_period, "view": safe_view})


@tool
def run_sql_query(
    sql: str,
    database: str = "",
    config: RunnableConfig = None,
) -> str:
    """
    Execute an ad-hoc T-SQL SELECT query against a named database.
    Only SELECT statements are permitted — DML and DDL are blocked.
    Results are capped at 200 rows.

    database: one of the configured database names (leave blank for the primary attendance_db).
    sql:      a valid T-SQL SELECT statement using SQL Server syntax.

    Use this when the built-in tools cannot answer a specific question.
    Example:
        SELECT TOP 10 class, COUNT(*) AS absences
        FROM attendance WHERE status='absent'
        GROUP BY class ORDER BY absences DESC
    """
    store = _store(config)
    if store is None:
        return "No data store connected."

    sql_clean = sql.strip().rstrip(";")
    if not re.search(r"\bTOP\s+\d+\b", sql_clean, re.IGNORECASE):
        sql_clean = re.sub(r"(?i)^\s*SELECT\b", "SELECT TOP 200", sql_clean, count=1)

    try:
        df = store._query(sql_clean, database=database or None)
    except PermissionError as e:
        return f"Query blocked: {e}"
    except Exception as e:
        return f"Query failed: {e}"

    if df.empty:
        return "Query returned no rows."
    return _df_to_text(df, max_rows=200)


@tool
def compare_periods(
    period_a: str = "last_7_days",
    period_b: str = "last_30_days",
    config: RunnableConfig = None,
) -> str:
    """
    Compare attendance rates between two time periods across all classes.
    Returns a side-by-side table with a delta column.
    period_a, period_b: 'all' | 'last_7_days' | 'last_30_days'
    Example: compare_periods(period_a='last_7_days', period_b='last_30_days')
    """
    store = _store(config)
    if store is None:
        return "No data store connected."

    df_a = store.compute_stats("class", period_a)
    df_b = store.compute_stats("class", period_b)

    if df_a.empty and df_b.empty:
        return "No data available for either period."

    df_a = df_a[["class", "attendance_rate"]].rename(columns={"attendance_rate": f"rate_{period_a}"})
    df_b = df_b[["class", "attendance_rate"]].rename(columns={"attendance_rate": f"rate_{period_b}"})

    merged = df_a.merge(df_b, on="class", how="outer").fillna(0)
    delta = (merged[f"rate_{period_b}"] - merged[f"rate_{period_a}"]).round(1)
    merged["delta"] = delta.apply(lambda d: f"+{d}" if d > 0 else str(d))

    return _df_to_text(merged)


@tool
def compare_classes(
    class_a: str,
    class_b: str,
    config: RunnableConfig = None,
) -> str:
    """
    Compare attendance statistics for two specific classes side by side.
    Returns total, present, absent, late, and attendance rate for each class.
    Example: compare_classes(class_a='10A', class_b='10B')
    """
    store = _store(config)
    if store is None:
        return "No data store connected."

    df = store.compute_stats("class", "all", classes=[class_a, class_b])
    if df.empty:
        return f"No data found for classes '{class_a}' or '{class_b}'."
    return _df_to_text(df)


ALL_TOOLS = [
    query_attendance,
    get_at_risk_students,
    get_summary,
    update_dashboard_view,
    run_sql_query,
    compare_periods,
    compare_classes,
]
