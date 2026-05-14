from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path

import pandas as pd

VALID_STATUSES = {"present", "absent", "late", "excused"}
_GLOB_PATTERNS = ("*.csv", "*.xlsx", "*.xls", "*.parquet")


def parse_attendance_query(question: str) -> dict:
    q = question.lower()

    group_by = "class"
    if "week"      in q: group_by = "week"
    elif "month"   in q: group_by = "month"
    elif "day"     in q: group_by = "day_of_week"
    elif "student" in q: group_by = "student_id"
    elif "grade"   in q: group_by = "grade"

    period = "all"
    if "last 7" in q or "this week"  in q: period = "last_7_days"
    elif "last 30" in q or "this month" in q: period = "last_30_days"

    return {"group_by": group_by, "period": period}


class AttendanceDataStore:
    def __init__(self, data_path: str | None = None) -> None:
        self._datasets: dict[str, dict] = {}
        if data_path is not None:
            self._load_from_path(Path(data_path))

    def _load_from_path(self, root: Path) -> None:
        if not root.exists():
            return
        paths = [root] if root.is_file() else sorted(p for g in _GLOB_PATTERNS for p in root.glob(g))
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

    def merged(self) -> pd.DataFrame:
        if not self._datasets:
            return pd.DataFrame()
        return pd.concat([v["df"] for v in self._datasets.values()], ignore_index=True)

    def get_at_risk(self, threshold: float = 75.0, classes=None) -> pd.DataFrame:
        df = self.merged()
        if df.empty:
            return pd.DataFrame()
        if classes and "class" in df.columns:
            df = df[df["class"].isin(classes)]
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

    def compute_stats(self, group_by: str = "class", period: str = "all", classes=None) -> pd.DataFrame:
        df = self.merged()
        if df.empty:
            return pd.DataFrame()
        if classes and "class" in df.columns:
            df = df[df["class"].isin(classes)]
            if df.empty:
                return pd.DataFrame()
        ref = df["date"].max()  # anchor to latest date in dataset, not wall clock
        if period == "last_7_days":
            df = df[df["date"] >= ref - timedelta(days=7)]
        elif period == "last_30_days":
            df = df[df["date"] >= ref - timedelta(days=30)]
        col = group_by if group_by in df.columns else ("class" if "class" in df.columns else "student_id")
        g = df.groupby(col).agg(
            total=("status",     "count"),
            present=("is_present", "sum"),
            absent=("is_absent",  "sum"),
            late=("is_late",    "sum"),
        ).reset_index()
        g["attendance_rate"] = (g["present"] / g["total"] * 100).round(1)
        return g

    def student_weekly_rates(self, student_ids: list, weeks: int = 6) -> dict:
        df = self.merged()
        if df.empty or not student_ids:
            return {}
        df = df[df["student_id"].isin(student_ids)]
        if df.empty:
            return {}
        all_weeks = sorted(df["week"].unique())[-weeks:]
        df = df[df["week"].isin(all_weeks)]
        grp = (
            df.groupby(["student_id", "week"])
            .agg(total=("status", "count"), present=("is_present", "sum"))
            .reset_index()
        )
        grp["rate"] = (grp["present"] / grp["total"] * 100).round(1)
        pivot = grp.pivot(index="student_id", columns="week", values="rate").reindex(columns=all_weeks)
        return {
            int(sid): [None if pd.isna(v) else float(v) for v in pivot.loc[sid]]
            if sid in pivot.index else [None] * len(all_weeks)
            for sid in student_ids
        }

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
