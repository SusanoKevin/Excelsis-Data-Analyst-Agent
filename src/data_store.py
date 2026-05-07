"""
AttendanceDataStore — extracted from Excelsis.ipynb Cell 3.
Import this in the notebook instead of redefining the class inline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

VALID_STATUSES = {"present", "absent", "late", "excused"}


def parse_attendance_query(question: str) -> dict:
    q = question.lower()

    chart_type = "bar"
    if "line"   in q: chart_type = "line"
    elif "pie"  in q: chart_type = "pie"
    elif "heat" in q: chart_type = "heatmap"

    group_by = "class"
    if "week"    in q: group_by = "week"
    elif "month" in q: group_by = "month"
    elif "day"   in q: group_by = "day_of_week"
    elif "student" in q: group_by = "student_id"
    elif "grade" in q: group_by = "grade"

    period = "all"
    if "last 7" in q or "this week"  in q: period = "last_7_days"
    elif "last 30" in q or "this month" in q: period = "last_30_days"

    threshold = 75.0
    for word in q.split():
        try:
            val = float(word.strip("%"))
            if 40 < val < 100:
                threshold = val
        except ValueError:
            pass

    use_at_risk = any(
        w in q for w in ["at risk", "at-risk", "below", "missing", "absent", "low attendance"]
    )

    return {
        "group_by":   group_by,
        "period":     period,
        "chart_type": chart_type,
        "threshold":  threshold,
        "use_at_risk": use_at_risk,
    }


class AttendanceDataStore:
    def __init__(self, data_path: Optional[str] = None) -> None:
        self._datasets: dict[str, dict] = {}
        if data_path is not None:
            self._load_from_path(Path(data_path))

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def _load_from_path(self, root: Path) -> None:
        if not root.exists():
            return
        paths = (
            [root]
            if root.is_file()
            else sorted(
                list(root.glob("*.csv"))
                + list(root.glob("*.xlsx"))
                + list(root.glob("*.xls"))
                + list(root.glob("*.parquet"))
            )
        )
        for p in paths:
            if not p.is_file():
                continue
            try:
                suf = p.suffix.lower()
                if suf == ".csv":
                    raw = pd.read_csv(p)
                elif suf in (".xlsx", ".xls"):
                    raw = pd.read_excel(p)
                elif suf == ".parquet":
                    raw = pd.read_parquet(p)
                else:
                    continue
                self.ingest_df(raw, name=p.stem)
            except Exception as ex:
                print(f"Could not load {p}: {ex}")

    def ingest_df(self, df: pd.DataFrame, name: str = "uploaded") -> dict:
        did = str(uuid.uuid4())
        df = df.copy()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["date"]   = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        df["status"] = df["status"].str.strip().str.lower()
        df = df[df["status"].isin(VALID_STATUSES)].copy()
        df["is_present"]  = df["status"] == "present"
        df["is_absent"]   = df["status"] == "absent"
        df["is_late"]     = df["status"] == "late"
        df["week"]        = df["date"].dt.to_period("W").astype(str)
        df["month"]       = df["date"].dt.to_period("M").astype(str)
        df["day_of_week"] = df["date"].dt.day_name()
        self._datasets[did] = {"name": name, "df": df}
        print(f"Ingested '{name}': {len(df):,} rows → id={did[:8]}")
        return {"dataset_id": did, "rows": len(df), "columns": list(df.columns)}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def merged(self) -> pd.DataFrame:
        if not self._datasets:
            return pd.DataFrame()
        return pd.concat([v["df"] for v in self._datasets.values()], ignore_index=True)

    def dataset_names(self) -> list[str]:
        return [v["name"] for v in self._datasets.values()]

    def get_at_risk(self, threshold: float = 75.0, grade: str = "all") -> pd.DataFrame:
        df = self.merged()
        if df.empty:
            return pd.DataFrame()
        if grade != "all" and "class" in df.columns:
            df = df[df["class"].str.upper() == grade.upper()]
        agg_cols: dict = {
            "total":   ("status",     "count"),
            "present": ("is_present", "sum"),
            "absent":  ("is_absent",  "sum"),
            "late":    ("is_late",    "sum"),
        }
        if "student_name" in df.columns:
            agg_cols["name"] = ("student_name", "first")
        if "class" in df.columns:
            agg_cols["cls"] = ("class", "first")
        agg = df.groupby("student_id").agg(**agg_cols).reset_index()
        agg["attendance_rate"] = (agg["present"] / agg["total"] * 100).round(1)
        return agg[agg["attendance_rate"] < threshold].sort_values("attendance_rate")

    def compute_stats(self, group_by: str = "class", period: str = "all") -> pd.DataFrame:
        df = self.merged()
        if df.empty:
            return pd.DataFrame()
        if period in ("last_7_days", "this_week"):
            df = df[df["date"] >= datetime.utcnow() - timedelta(days=7)]
        elif period in ("last_30_days", "this_month"):
            df = df[df["date"] >= datetime.utcnow() - timedelta(days=30)]
        col = group_by if group_by in df.columns else ("class" if "class" in df.columns else "student_id")
        g = df.groupby(col).agg(
            total=("status",     "count"),
            present=("is_present", "sum"),
            absent=("is_absent",  "sum"),
            late=("is_late",    "sum"),
        ).reset_index()
        g["attendance_rate"] = (g["present"] / g["total"] * 100).round(1)
        return g

    def summary(self) -> dict:
        df = self.merged()
        if df.empty:
            return {"status": "no_data"}
        return {
            "total_records":           len(df),
            "unique_students":         int(df["student_id"].nunique()),
            "date_range": {
                "from": str(df["date"].min().date()),
                "to":   str(df["date"].max().date()),
            },
            "overall_attendance_rate": round(float(df["is_present"].mean() * 100), 1),
            "total_absences":          int(df["is_absent"].sum()),
            "classes":                 df["class"].unique().tolist() if "class" in df.columns else [],
        }

    def query_to_df(self, query: str) -> pd.DataFrame:
        p = parse_attendance_query(query)
        if p["use_at_risk"]:
            return self.get_at_risk(p["threshold"], "all")
        return self.compute_stats(p["group_by"], p["period"])
