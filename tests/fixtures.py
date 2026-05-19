from __future__ import annotations

import logging
import time
import uuid
from datetime import timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

VALID_STATUSES = {"present", "absent", "late", "excused"}
_GLOB_PATTERNS = ("*.csv", "*.xlsx", "*.xls", "*.parquet")


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

    def clear(self) -> None:
        self._store.clear()


class AttendanceDataStore:
    """In-memory pandas-backed store used exclusively as a test fixture."""

    def __init__(self, data_path: str | None = None) -> None:
        self._datasets: dict[str, dict] = {}
        self._cache = _TTLCache(ttl=300)
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
                logger.warning("Could not load %s: %s", p, ex)

    def ingest_df(self, df: pd.DataFrame, name: str = "uploaded") -> dict:
        did = str(uuid.uuid4())
        df = df.copy()
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["date"]        = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
        df["status"]      = df["status"].str.strip().str.lower()
        df                = df[df["status"].isin(VALID_STATUSES)].copy()
        df["is_present"]  = df["status"] == "present"
        df["is_absent"]   = df["status"] == "absent"
        df["is_late"]     = df["status"] == "late"
        df["week"]        = df["date"].dt.to_period("W").astype(str)
        df["month"]       = df["date"].dt.to_period("M").astype(str)
        df["day_of_week"] = df["date"].dt.day_name()
        self._datasets[did] = {"name": name, "df": df}
        self._cache.clear()
        logger.info("Ingested '%s': %d rows → id=%s", name, len(df), did[:8])
        return {"dataset_id": did, "rows": len(df), "columns": list(df.columns)}

    def merged(self) -> pd.DataFrame:
        if not self._datasets:
            return pd.DataFrame()
        return pd.concat([v["df"] for v in self._datasets.values()], ignore_index=True)

    def get_threshold_alerts(
        self,
        threshold: float = 75.0,
        classes=None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> pd.DataFrame:
        cache_key = f"at_risk:{threshold}:{','.join(sorted(classes or []))}:{date_from or ''}:{date_to or ''}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        df = self.merged()
        if df.empty:
            return pd.DataFrame()
        if classes and "class" in df.columns:
            df = df[df["class"].isin(classes)]
        if date_from:
            df = df[df["date"] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df["date"] <= pd.to_datetime(date_to)]
        if df.empty:
            return pd.DataFrame()

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
        result = agg[agg["attendance_rate"] < threshold].sort_values("attendance_rate")
        self._cache.set(cache_key, result)
        return result

    def compute_stats(
        self,
        group_by: str = "class",
        period: str = "all",
        classes=None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> pd.DataFrame:
        cache_key = f"stats:{group_by}:{period}:{','.join(sorted(classes or []))}:{date_from or ''}:{date_to or ''}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        df = self.merged()
        if df.empty:
            return pd.DataFrame()
        if classes and "class" in df.columns:
            df = df[df["class"].isin(classes)]
            if df.empty:
                return pd.DataFrame()

        if date_from or date_to:
            if date_from:
                df = df[df["date"] >= pd.to_datetime(date_from)]
            if date_to:
                df = df[df["date"] <= pd.to_datetime(date_to)]
        else:
            ref = df["date"].max()  # anchor to latest date in dataset, not wall clock
            if period == "last_7_days":
                df = df[df["date"] >= ref - timedelta(days=7)]
            elif period == "last_30_days":
                df = df[df["date"] >= ref - timedelta(days=30)]
            elif period == "prior_30_days":
                cutoff = ref - timedelta(days=30)
                df = df[(df["date"] < cutoff) & (df["date"] >= cutoff - timedelta(days=30))]

        if df.empty:
            return pd.DataFrame()

        col = group_by if group_by in df.columns else ("class" if "class" in df.columns else "student_id")
        g = df.groupby(col).agg(
            total=("status",     "count"),
            present=("is_present", "sum"),
            absent=("is_absent",  "sum"),
            late=("is_late",    "sum"),
        ).reset_index()
        g["attendance_rate"] = (g["present"] / g["total"] * 100).round(1)
        self._cache.set(cache_key, g)
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
            sid: [None if pd.isna(v) else float(v) for v in pivot.loc[sid]]
            if sid in pivot.index else [None] * len(all_weeks)
            for sid in student_ids
        }

    def summary(self) -> dict:
        df = self.merged()
        if df.empty:
            return {"status": "no_data"}
        return {
            "total_records":         len(df),
            "entity_count":          int(df["student_id"].nunique()),
            "date_range": {
                "from": str(df["date"].min().date()),
                "to":   str(df["date"].max().date()),
            },
            "metric_rate":           round(float(df["is_present"].mean() * 100), 1),
            "below_threshold_count": int((~df["is_present"]).sum()),
            "dimensions":            df["class"].unique().tolist() if "class" in df.columns else [],
        }
