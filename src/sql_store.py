from __future__ import annotations

import os
import time

import pandas as pd
import pyodbc
import sqlglot
from sqlglot import exp

_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
    exp.Alter, exp.TruncateTable, exp.Merge, exp.Command,
)

_GROUP_EXPR: dict[str, tuple[str, str]] = {
    "class":       ("class", "class"),
    "grade":       ("grade", "grade"),
    "student_id":  ("CAST(student_id AS NVARCHAR(20))", "student_id"),
    "week": (
        "CONVERT(NVARCHAR(10),DATEADD(dd,1-DATEPART(dw,date),date),23)"
        "+'/'+"
        "CONVERT(NVARCHAR(10),DATEADD(dd,7-DATEPART(dw,date),date),23)",
        "week",
    ),
    "month":       ("FORMAT(date,'yyyy-MM')", "month"),
    "day_of_week": ("DATENAME(dw,date)",      "day_of_week"),
}


def _assert_select_only(sql: str) -> None:
    try:
        trees = [t for t in sqlglot.parse(sql, dialect="tsql") if t is not None]
    except Exception as e:
        raise ValueError(f"Could not parse SQL: {e}") from e
    if not trees:
        raise ValueError("Empty SQL statement.")
    if len(trees) > 1:
        raise PermissionError("Read-only store: only a single SELECT statement is permitted.")
    if not isinstance(trees[0], exp.Select):
        raise PermissionError("Read-only store: only SELECT statements are permitted.")
    for node in trees[0].walk():
        if isinstance(node, _FORBIDDEN):
            raise PermissionError(f"Read-only store: {type(node).__name__} statements are not permitted.")


def _build_conn_str(database: str) -> str:
    server   = os.environ["SQL_SERVER"]
    driver   = os.environ.get("SQL_DRIVER", "{ODBC Driver 18 for SQL Server}")
    username = os.environ["SQL_USERNAME"]
    password = os.environ["SQL_PASSWORD"]
    return (
        f"DRIVER={driver};SERVER={server};DATABASE={database};"
        f"UID={username};PWD={password};TrustServerCertificate=yes;"
    )


class _TTLCache:
    def __init__(self, ttl: int = 300) -> None:
        self._store: dict = {}
        self._ttl = ttl

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires = entry
        if time.monotonic() > expires:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)


def _ph(n: int) -> str:
    """Return n comma-separated '?' placeholders."""
    return ",".join(["?"] * n)


class SQLAttendanceStore:
    """
    Read-only SQL Server backend.
    Table: attendance(student_id, student_name, class, grade, date DATE, status VARCHAR)
    status values: 'present' | 'absent' | 'late' | 'excused'
    """

    def __init__(self) -> None:
        self._primary_db = os.environ.get("SQL_PRIMARY_DB", "attendance_db")
        self._databases: list[str] = [
            d.strip()
            for d in os.environ.get("SQL_DATABASES", self._primary_db).split(",")
            if d.strip()
        ]
        self._cache = _TTLCache(ttl=300)

    def _query(self, sql: str, params: tuple = (), database: str | None = None) -> pd.DataFrame:
        _assert_select_only(sql)
        target_db = database or self._primary_db
        if target_db not in self._databases:
            raise PermissionError(f"Database '{target_db}' is not in the configured allowlist.")
        conn = pyodbc.connect(_build_conn_str(target_db), autocommit=True)
        try:
            return pd.read_sql(sql, conn, params=params or None)
        finally:
            conn.close()

    def summary(self) -> dict:
        df = self._query("""
        SELECT
            COUNT(*)                                                          AS total_records,
            COUNT(DISTINCT student_id)                                        AS unique_students,
            CONVERT(NVARCHAR(10),MIN(date),23)                                AS date_from,
            CONVERT(NVARCHAR(10),MAX(date),23)                                AS date_to,
            ROUND(100.0*SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)
                /NULLIF(COUNT(*),0),1)                                        AS overall_rate,
            COUNT(CASE WHEN status='absent' THEN 1 END)                      AS total_absences
        FROM attendance
        WHERE status IN ('present','absent','late','excused')
        """)
        if df.empty or int(df["total_records"].iloc[0]) == 0:
            return {"status": "no_data"}

        classes_df = self._query(
            "SELECT DISTINCT class FROM attendance WHERE class IS NOT NULL ORDER BY class"
        )
        row = df.iloc[0]
        return {
            "total_records":           int(row["total_records"]),
            "unique_students":         int(row["unique_students"]),
            "date_range":              {"from": str(row["date_from"]), "to": str(row["date_to"])},
            "overall_attendance_rate": float(row["overall_rate"]),
            "total_absences":          int(row["total_absences"]),
            "classes":                 classes_df["class"].tolist() if not classes_df.empty else [],
        }

    def compute_stats(
        self,
        group_by:  str = "class",
        period:    str = "all",
        classes:   list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        cache_key = f"stats:{group_by}:{period}:{','.join(sorted(classes or []))}:{date_from or ''}:{date_to or ''}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        col_expr, col_alias = _GROUP_EXPR.get(group_by, _GROUP_EXPR["class"])
        params: list = []

        # Explicit date bounds take precedence over period shorthand.
        # Using parameterized queries to prevent SQL injection.
        if date_from or date_to:
            period_parts = []
            if date_from:
                period_parts.append("AND date >= ?")
                params.append(date_from)
            if date_to:
                period_parts.append("AND date <= ?")
                params.append(date_to)
            period_clause = " ".join(period_parts)
        elif period == "last_7_days":
            period_clause = "AND date >= (SELECT DATEADD(dd,-7,MAX(date)) FROM attendance)"
        elif period == "last_30_days":
            period_clause = "AND date >= (SELECT DATEADD(dd,-30,MAX(date)) FROM attendance)"
        elif period == "prior_30_days":
            period_clause = (
                "AND date >= (SELECT DATEADD(dd,-60,MAX(date)) FROM attendance) "
                "AND date <  (SELECT DATEADD(dd,-30,MAX(date)) FROM attendance)"
            )
        else:
            period_clause = ""

        class_clause = ""
        if classes:
            class_clause = f"AND class IN ({_ph(len(classes))})"
            params.extend(classes)

        result = self._query(f"""
        SELECT
            {col_expr}  AS [{col_alias}],
            COUNT(*)                                                     AS total,
            SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)           AS present,
            SUM(CASE WHEN status='absent'  THEN 1 ELSE 0 END)           AS absent,
            SUM(CASE WHEN status='late'    THEN 1 ELSE 0 END)           AS late,
            ROUND(100.0*SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)
                /NULLIF(COUNT(*),0),1)                                   AS attendance_rate
        FROM attendance
        WHERE status IN ('present','absent','late','excused')
        {period_clause}
        {class_clause}
        GROUP BY {col_expr}
        """, params=tuple(params))
        self._cache.set(cache_key, result)
        return result

    def get_at_risk(
        self,
        threshold: float = 75.0,
        classes:   list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        cache_key = f"at_risk:{threshold}:{','.join(sorted(classes or []))}:{date_from or ''}:{date_to or ''}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params: list = []
        class_clause = ""
        if classes:
            class_clause = f"AND class IN ({_ph(len(classes))})"
            params.extend(classes)

        # Parameterized date bounds prevent SQL injection on user-supplied dates.
        date_clause = ""
        if date_from:
            date_clause += "AND date >= ? "
            params.append(date_from)
        if date_to:
            date_clause += "AND date <= ? "
            params.append(date_to)

        params.append(threshold)

        result = self._query(f"""
        SELECT
            student_id,
            MAX(student_name)                                              AS name,
            MAX(class)                                                     AS cls,
            COUNT(*)                                                       AS total,
            SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)             AS present,
            SUM(CASE WHEN status='absent'  THEN 1 ELSE 0 END)             AS absent,
            SUM(CASE WHEN status='late'    THEN 1 ELSE 0 END)             AS late,
            ROUND(100.0*SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)
                /NULLIF(COUNT(*),0),1)                                     AS attendance_rate
        FROM attendance
        WHERE status IN ('present','absent','late','excused')
        {class_clause}
        {date_clause}
        GROUP BY student_id
        HAVING ROUND(100.0*SUM(CASE WHEN status='present' THEN 1 ELSE 0 END)
            /NULLIF(COUNT(*),0),1) < ?
        ORDER BY attendance_rate ASC
        """, params=tuple(params))
        self._cache.set(cache_key, result)
        return result

    def student_weekly_rates(self, student_ids: list, weeks: int = 6) -> dict:
        if not student_ids:
            return {}
        df = self._query(f"""
        SELECT
            student_id,
            CONVERT(NVARCHAR(10),DATEADD(dd,1-DATEPART(dw,date),date),23)
                +'/'
                +CONVERT(NVARCHAR(10),DATEADD(dd,7-DATEPART(dw,date),date),23) AS week,
            COUNT(*)                                           AS total,
            SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) AS present
        FROM attendance
        WHERE status IN ('present','absent','late','excused')
          AND student_id IN ({_ph(len(student_ids))})
        GROUP BY
            student_id,
            CONVERT(NVARCHAR(10),DATEADD(dd,1-DATEPART(dw,date),date),23)
                +'/'
                +CONVERT(NVARCHAR(10),DATEADD(dd,7-DATEPART(dw,date),date),23)
        ORDER BY week ASC
        """, params=tuple(student_ids))
        if df.empty:
            return {}

        all_weeks = sorted(df["week"].unique())[-weeks:]
        df        = df[df["week"].isin(all_weeks)].copy()
        df["rate"] = (df["present"] / df["total"] * 100).round(1)
        pivot = (
            df.pivot(index="student_id", columns="week", values="rate")
            .reindex(columns=all_weeks)
        )
        return {
            int(sid): [None if pd.isna(v) else float(v) for v in pivot.loc[sid]]
            if sid in pivot.index else [None] * len(all_weeks)
            for sid in student_ids
        }
