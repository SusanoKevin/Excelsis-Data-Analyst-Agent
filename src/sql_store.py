from __future__ import annotations

import os
import time
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import sqlglot
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlglot import exp

_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
    exp.Alter, exp.TruncateTable, exp.Merge, exp.Command,
)


def _assert_select_only(sql: str) -> None:
    try:
        trees = [t for t in sqlglot.parse(sql.replace("?", "NULL"), dialect="tsql") if t is not None]
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


def _build_engine(database: str) -> Engine:
    server    = os.environ["SQL_SERVER"]
    driver    = os.environ.get("SQL_DRIVER", "{ODBC Driver 18 for SQL Server}")
    username  = os.environ["SQL_USERNAME"]
    password  = os.environ["SQL_PASSWORD"]
    pool_size = int(os.environ.get("SQL_POOL_SIZE", "5"))
    timeout   = int(os.environ.get("SQL_QUERY_TIMEOUT", "30"))
    dsn = (
        f"DRIVER={driver};SERVER={server};DATABASE={database};"
        f"UID={username};PWD={password};TrustServerCertificate=yes;"
    )
    url = f"mssql+pyodbc:///?odbc_connect={quote_plus(dsn)}"
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={"timeout": timeout},
    )


class _TTLCache:
    def __init__(self, ttl: int = 300, maxsize: int = 0) -> None:
        self._store: dict = {}
        self._ttl = ttl
        self._maxsize = maxsize

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
        if self._maxsize > 0 and len(self._store) >= self._maxsize and key not in self._store:
            oldest = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest]
        self._store[key] = (value, time.monotonic() + self._ttl)


def _ph(n: int) -> str:
    return ",".join(["?"] * n)


class SQLDataStore:
    def __init__(self) -> None:
        self._primary_db = os.environ.get("SQL_PRIMARY_DB", "")
        self._databases: list[str] = [
            d.strip()
            for d in os.environ.get("SQL_DATABASES", self._primary_db).split(",")
            if d.strip()
        ]
        self._table           = os.environ.get("PRIMARY_TABLE",       "")
        self._metric_col      = os.environ.get("METRIC_COLUMN",       "status")
        self._positive_val    = os.environ.get("POSITIVE_VALUE",      "active")
        self._date_col        = os.environ.get("DATE_COLUMN",         "date")
        self._entity_col      = os.environ.get("ENTITY_COLUMN",       "entity_id")
        self._entity_name_col = os.environ.get("ENTITY_NAME_COLUMN",  "entity_name")
        self._group_cols: list[str] = [
            c.strip()
            for c in os.environ.get("GROUP_COLUMNS", "").split(",")
            if c.strip()
        ]
        self._group_expr = self._build_group_expr()
        self._engines: dict[str, Engine] = {db: _build_engine(db) for db in self._databases}
        self._cache = _TTLCache(ttl=300)

    def _build_group_expr(self) -> dict[str, tuple[str, str]]:
        dc = self._date_col
        expr: dict[str, tuple[str, str]] = {}
        for col in self._group_cols:
            expr[col] = (col, col)
        expr[self._entity_col] = (f"CAST({self._entity_col} AS NVARCHAR(50))", self._entity_col)
        expr["week"] = (
            f"CONVERT(NVARCHAR(10),DATEADD(dd,1-DATEPART(dw,{dc}),{dc}),23)"
            f"+'/'+"
            f"CONVERT(NVARCHAR(10),DATEADD(dd,7-DATEPART(dw,{dc}),{dc}),23)",
            "week",
        )
        expr["month"]       = (f"FORMAT({dc},'yyyy-MM')", "month")
        expr["day_of_week"] = (f"DATENAME(dw,{dc})",     "day_of_week")
        return expr

    @property
    def databases(self) -> list[str]:
        return list(self._databases)

    @property
    def primary_db(self) -> str:
        return self._primary_db

    def _require_table(self) -> str:
        if not self._table:
            raise RuntimeError("PRIMARY_TABLE is not configured. Set PRIMARY_TABLE in your .env file.")
        return self._table

    def _query(self, sql: str, params: tuple = (), database: str | None = None) -> pd.DataFrame:
        _assert_select_only(sql)
        target_db = database or self._primary_db
        if target_db not in self._databases:
            raise PermissionError(f"Database '{target_db}' is not in the configured allowlist.")
        conn = self._engines[target_db].raw_connection()
        try:
            return pd.read_sql(sql, conn, params=params or None)
        finally:
            conn.close()

    def ping(self, database: str | None = None) -> bool:
        try:
            self._query("SELECT 1", database=database)
            return True
        except Exception:
            return False

    def close(self) -> None:
        for engine in self._engines.values():
            engine.dispose()

    def summary(self) -> dict:
        self._require_table()
        cached = self._cache.get("summary:all")
        if cached is not None:
            return cached

        t, mc, pv = self._table, self._metric_col, self._positive_val
        dc, ec    = self._date_col, self._entity_col
        df = self._query(f"""
        SELECT
            COUNT(*)                                                          AS total_records,
            COUNT(DISTINCT {ec})                                              AS entity_count,
            CONVERT(NVARCHAR(10),MIN({dc}),23)                               AS date_from,
            CONVERT(NVARCHAR(10),MAX({dc}),23)                               AS date_to,
            ROUND(100.0*SUM(CASE WHEN {mc}=? THEN 1 ELSE 0 END)
                /NULLIF(COUNT(*),0),1)                                        AS metric_rate,
            SUM(CASE WHEN {mc}<>? THEN 1 ELSE 0 END)                        AS below_threshold_count
        FROM {t}
        """, params=(pv, pv))

        if df.empty or int(df["total_records"].iloc[0]) == 0:
            return {"status": "no_data"}

        first_dim = self._group_cols[0] if self._group_cols else None
        dims_df = self._query(
            f"SELECT DISTINCT {first_dim} FROM {t} "
            f"WHERE {first_dim} IS NOT NULL ORDER BY {first_dim}"
        ) if first_dim else pd.DataFrame()

        row = df.iloc[0]
        result = {
            "total_records":         int(row["total_records"]),
            "entity_count":          int(row["entity_count"]),
            "date_range":            {"from": str(row["date_from"]), "to": str(row["date_to"])},
            "metric_rate":           float(row["metric_rate"]),
            "below_threshold_count": int(row["below_threshold_count"]),
            "dimensions":            dims_df[first_dim].tolist() if first_dim and not dims_df.empty else [],
        }
        self._cache.set("summary:all", result)
        return result

    def compute_stats(
        self,
        group_by:  str = "",
        period:    str = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        self._require_table()
        group_by  = group_by or (self._group_cols[0] if self._group_cols else self._entity_col)
        cache_key = f"stats:{group_by}:{period}:{','.join(sorted(segments or []))}:{date_from or ''}:{date_to or ''}"
        cached    = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if group_by not in self._group_expr:
            raise ValueError(f"Invalid group_by '{group_by}'. Valid: {', '.join(self._group_expr)}")
        col_expr, col_alias = self._group_expr[group_by]
        t, mc, pv, dc = self._table, self._metric_col, self._positive_val, self._date_col
        params: list = [pv, pv]

        if date_from or date_to:
            period_parts = []
            if date_from:
                period_parts.append(f"AND {dc} >= ?")
                params.append(date_from)
            if date_to:
                period_parts.append(f"AND {dc} <= ?")
                params.append(date_to)
            period_clause = " ".join(period_parts)
        elif period == "last_7_days":
            period_clause = f"AND {dc} >= (SELECT DATEADD(dd,-7,MAX({dc})) FROM {t})"
        elif period == "last_30_days":
            period_clause = f"AND {dc} >= (SELECT DATEADD(dd,-30,MAX({dc})) FROM {t})"
        elif period == "prior_30_days":
            period_clause = (
                f"AND {dc} >= (SELECT DATEADD(dd,-60,MAX({dc})) FROM {t}) "
                f"AND {dc} <  (SELECT DATEADD(dd,-30,MAX({dc})) FROM {t})"
            )
        else:
            period_clause = ""

        segment_clause = ""
        if segments and self._group_cols:
            segment_clause = f"AND {self._group_cols[0]} IN ({_ph(len(segments))})"
            params.extend(segments)

        result = self._query(f"""
        SELECT
            {col_expr}  AS [{col_alias}],
            COUNT(*)                                                          AS total,
            SUM(CASE WHEN {mc}=? THEN 1 ELSE 0 END)                         AS positive_count,
            ROUND(100.0*SUM(CASE WHEN {mc}=? THEN 1 ELSE 0 END)
                /NULLIF(COUNT(*),0),1)                                        AS metric_rate
        FROM {t}
        WHERE 1=1
        {period_clause}
        {segment_clause}
        GROUP BY {col_expr}
        """, params=tuple(params))
        if group_by in self._group_cols and col_alias != "class":
            result = result.rename(columns={col_alias: "class"})
        self._cache.set(cache_key, result)
        return result

    def get_threshold_alerts(
        self,
        threshold: float = 75.0,
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        self._require_table()
        cache_key = f"alerts:{threshold}:{','.join(sorted(segments or []))}:{date_from or ''}:{date_to or ''}"
        cached    = self._cache.get(cache_key)
        if cached is not None:
            return cached

        t, mc, pv, dc = self._table, self._metric_col, self._positive_val, self._date_col
        ec, enc       = self._entity_col, self._entity_name_col
        grp0          = self._group_cols[0] if self._group_cols else None
        params: list  = [pv, pv]

        segment_clause = ""
        if segments and grp0:
            segment_clause = f"AND {grp0} IN ({_ph(len(segments))})"
            params.extend(segments)

        date_clause = ""
        if date_from:
            date_clause += f"AND {dc} >= ? "
            params.append(date_from)
        if date_to:
            date_clause += f"AND {dc} <= ? "
            params.append(date_to)

        params.append(pv)
        params.append(threshold)

        result = self._query(f"""
        SELECT
            {ec}                                                              AS entity_id,
            MAX({enc})                                                        AS label,
            {f"MAX({grp0})" if grp0 else "NULL"}                             AS group_name,
            COUNT(*)                                                          AS total,
            SUM(CASE WHEN {mc}=? THEN 1 ELSE 0 END)                         AS positive_count,
            ROUND(100.0*SUM(CASE WHEN {mc}=? THEN 1 ELSE 0 END)
                /NULLIF(COUNT(*),0),1)                                        AS metric_rate
        FROM {t}
        WHERE 1=1
        {segment_clause}
        {date_clause}
        GROUP BY {ec}
        HAVING ROUND(100.0*SUM(CASE WHEN {mc}=? THEN 1 ELSE 0 END)
            /NULLIF(COUNT(*),0),1) < ?
        ORDER BY metric_rate ASC
        """, params=tuple(params))
        self._cache.set(cache_key, result)
        return result

    def entity_weekly_rates(self, entity_ids: list, weeks: int = 6) -> dict:
        if not entity_ids:
            return {}
        self._require_table()
        cache_key = f"weekly:{','.join(str(e) for e in sorted(entity_ids))}:{weeks}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        t, mc, pv, dc, ec = self._table, self._metric_col, self._positive_val, self._date_col, self._entity_col
        week_expr = (
            f"CONVERT(NVARCHAR(10),DATEADD(dd,1-DATEPART(dw,{dc}),{dc}),23)"
            f"+'/'+"
            f"CONVERT(NVARCHAR(10),DATEADD(dd,7-DATEPART(dw,{dc}),{dc}),23)"
        )
        df = self._query(f"""
        SELECT
            {ec}                                        AS entity_id,
            {week_expr}                                 AS week,
            COUNT(*)                                    AS total,
            SUM(CASE WHEN {mc}=? THEN 1 ELSE 0 END)    AS positive_count
        FROM {t}
        WHERE {ec} IN ({_ph(len(entity_ids))})
        GROUP BY {ec}, {week_expr}
        ORDER BY week ASC
        """, params=(pv, *entity_ids))

        if df.empty:
            return {}

        all_weeks = sorted(df["week"].unique())[-weeks:]
        df        = df[df["week"].isin(all_weeks)].copy()
        df["rate"] = (df["positive_count"] / df["total"] * 100).round(1)
        pivot = (
            df.pivot(index="entity_id", columns="week", values="rate")
            .reindex(columns=all_weeks)
        )
        result = {
            eid: [None if pd.isna(v) else float(v) for v in pivot.loc[eid]]
            if eid in pivot.index else [None] * len(all_weeks)
            for eid in entity_ids
        }
        self._cache.set(cache_key, result)
        return result

    def compute_statistical_summary(
        self,
        group_by:  str = "",
        period:    str = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> dict:
        df = self.compute_stats(group_by, period, segments, date_from, date_to)
        if df.empty or "metric_rate" not in df.columns:
            return {"error": "No data available."}
        return df["metric_rate"].describe().round(1).to_dict()

    def detect_anomalies(
        self,
        group_by:  str   = "",
        sigma:     float = 2.0,
        period:    str   = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        df = self.compute_stats(group_by, period, segments, date_from, date_to).copy()
        if df.empty or "metric_rate" not in df.columns:
            return pd.DataFrame()
        mean = df["metric_rate"].mean()
        std  = df["metric_rate"].std()
        if std == 0:
            return pd.DataFrame()
        df["z_score"] = ((df["metric_rate"] - mean) / std).round(2)
        return df[df["z_score"].abs() > sigma].sort_values("z_score").reset_index(drop=True)

    def get_top_n(
        self,
        group_by:  str  = "",
        n:         int  = 10,
        ascending: bool = True,
        period:    str  = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        df = self.compute_stats(group_by, period, segments, date_from, date_to)
        if df.empty or "metric_rate" not in df.columns:
            return pd.DataFrame()
        return (
            df.nsmallest(n, "metric_rate") if ascending
            else df.nlargest(n, "metric_rate")
        ).reset_index(drop=True)

    def analyze_weekly_trend(
        self,
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> dict:
        cache_key = f"trend:{','.join(sorted(segments or []))}:{date_from or ''}:{date_to or ''}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        df = self.compute_stats("week", "all", segments, date_from, date_to)
        if df.empty or "metric_rate" not in df.columns or len(df) < 2:
            return {"direction": "unknown", "slope_per_week": 0.0, "weeks": []}
        df    = df.sort_values("week").reset_index(drop=True)
        rates = df["metric_rate"].values.astype(float)
        slope = float(np.polyfit(range(len(rates)), rates, 1)[0])
        if   slope >  0.1: direction = "improving"
        elif slope < -0.1: direction = "declining"
        else:              direction = "stable"
        result = {
            "direction":      direction,
            "slope_per_week": round(slope, 2),
            "weeks":          df.to_dict(orient="records"),
        }
        self._cache.set(cache_key, result)
        return result
