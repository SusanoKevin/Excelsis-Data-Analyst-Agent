"""
Dashboard generation for Excelsis 360.
Used by the FastAPI backend, the generate_dashboard tool, and the notebook.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

COLORS = {
    "primary": "#1a3c5e",
    "success": "#00a86b",
    "warning": "#f5a623",
    "danger":  "#e74c3c",
    "accent":  "#3498db",
}

_DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _theme():
    sns.set_theme(
        context="notebook",
        style="whitegrid",
        rc={
            "axes.facecolor":    "#f8fafc",
            "figure.facecolor":  "#eef2f7",
            "grid.color":        "#e2e8f0",
            "axes.edgecolor":    "#cbd5e1",
            "axes.labelcolor":   COLORS["primary"],
            "text.color":        COLORS["primary"],
            "xtick.color":       COLORS["primary"],
            "ytick.color":       COLORS["primary"],
            "font.family":       "sans-serif",
            "font.sans-serif":   ["Inter", "DejaVu Sans", "Arial", "sans-serif"],
            "figure.dpi":        120,
        },
    )


def _empty_fig(message: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 3))
    fig.patch.set_facecolor("#eef2f7")
    ax.text(0.5, 0.5, message, ha="center", va="center",
            fontsize=13, color=COLORS["primary"])
    ax.axis("off")
    return fig


def _compute_filtered(store, group_by: str, period: str, classes=None) -> pd.DataFrame:
    """Compute attendance stats with optional class filtering."""
    if not classes:
        return store.compute_stats(group_by, period)

    raw = store.merged()
    if raw.empty:
        return pd.DataFrame()
    if "class" in raw.columns:
        raw = raw[raw["class"].isin(classes)]
    if raw.empty:
        return pd.DataFrame()

    if period in ("last_7_days", "this_week"):
        raw = raw[raw["date"] >= datetime.utcnow() - timedelta(days=7)]
    elif period in ("last_30_days", "this_month"):
        raw = raw[raw["date"] >= datetime.utcnow() - timedelta(days=30)]

    col = group_by if group_by in raw.columns else (
        "class" if "class" in raw.columns else "student_id"
    )
    g = raw.groupby(col).agg(
        total=("status",     "count"),
        present=("is_present", "sum"),
        absent=("is_absent",  "sum"),
        late=("is_late",    "sum"),
    ).reset_index()
    g["attendance_rate"] = (g["present"] / g["total"] * 100).round(1)
    return g


# ---------------------------------------------------------------------------
# build_query_dashboard — focused, query-specific charts
# ---------------------------------------------------------------------------

def build_query_dashboard(
    store,
    chart_type: str = "full",
    group_by: str = "class",
    period: str = "all",
    title: str = "",
    classes: list = None,
) -> plt.Figure:
    """
    Generate a query-specific attendance chart.

    chart_type: 'full' | 'class_bar' | 'weekly_trend' | 'weekday_bar' |
                'status_donut' | 'at_risk_bar' | 'grade_bar'
    group_by:   column to group by (used for the fallback generic chart)
    period:     'all' | 'last_7_days' | 'last_30_days'
    title:      chart title (auto-generated if blank)
    classes:    restrict data to these classes (None = all)
    """
    _theme()
    summ = store.summary()
    if summ.get("status") == "no_data":
        return _empty_fig("No attendance data loaded.")

    rate       = summ.get("overall_attendance_rate", 0)
    auto_title = title or f"Attendance — {chart_type.replace('_', ' ').title()}"

    if chart_type == "full":
        return build_modern_static_dashboard(store, period=period, save=False)

    # ---- class_bar ---------------------------------------------------------
    if chart_type == "class_bar":
        df = _compute_filtered(store, "class", period, classes)
        if df.empty:
            return _empty_fig("No class data available.")
        gcol = "class" if "class" in df.columns else df.columns[0]
        df   = df.sort_values("attendance_rate")
        fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.55 + 1)))
        fig.patch.set_facecolor("#eef2f7")
        sns.barplot(data=df, y=gcol, x="attendance_rate",
                    palette="crest", hue=gcol, dodge=False, legend=False, ax=ax)
        ax.axvline(75,   color=COLORS["danger"], linestyle="--", linewidth=1.2, alpha=0.85, label="At-risk (75%)")
        ax.axvline(rate, color="#fbbf24",         linestyle="-.", linewidth=1.2, alpha=0.9,  label=f"Avg ({rate:.1f}%)")
        ax.set_xlim(max(45, df["attendance_rate"].min() - 5), 100)
        ax.set_title(auto_title, loc="left", fontsize=13, fontweight="600", color=COLORS["primary"])
        ax.set_xlabel("Attendance rate (%)")
        ax.legend(fontsize=9, framealpha=0.95)
        fig.tight_layout()
        return fig

    # ---- weekly_trend ------------------------------------------------------
    if chart_type == "weekly_trend":
        df = _compute_filtered(store, "week", period, classes)
        if df.empty:
            return _empty_fig("No weekly data available.")
        wcol = "week" if "week" in df.columns else df.columns[0]
        df   = df.sort_values(wcol)
        n, x = len(df), np.arange(len(df))
        fig, ax = plt.subplots(figsize=(12, 4.5))
        fig.patch.set_facecolor("#eef2f7")
        ax.plot(x, df["attendance_rate"], marker="o", linewidth=2.2, markersize=5, color=COLORS["accent"])
        ax.axhline(75, color=COLORS["danger"], linestyle="--", linewidth=1, alpha=0.75, label="At-risk (75%)")
        ax.fill_between(x, df["attendance_rate"], 75,
                        where=(df["attendance_rate"] < 75),
                        color=COLORS["danger"], alpha=0.12, interpolate=True)
        step     = max(1, int(np.ceil(n / 10)))
        tick_pos = x[::step]
        ax.set_xticks(tick_pos)
        ax.set_xticklabels([str(df[wcol].iloc[j]) for j in tick_pos], rotation=40, ha="right", fontsize=8)
        ax.set_xlim(-0.5, n - 0.5)
        ax.set_ylabel("Attendance rate (%)")
        ax.set_title(auto_title, loc="left", fontsize=13, fontweight="600", color=COLORS["primary"])
        ax.legend(fontsize=9, framealpha=0.95)
        fig.tight_layout()
        return fig

    # ---- weekday_bar -------------------------------------------------------
    if chart_type == "weekday_bar":
        df = _compute_filtered(store, "day_of_week", period, classes)
        if df.empty:
            return _empty_fig("No weekday data available.")
        if "day_of_week" in df.columns:
            df = df.copy()
            df["day_of_week"] = pd.Categorical(
                df["day_of_week"], categories=_DAY_ORDER, ordered=True
            )
            df = df.sort_values("day_of_week")
        gcol = "day_of_week" if "day_of_week" in df.columns else df.columns[0]
        fig, ax = plt.subplots(figsize=(9, 4.5))
        fig.patch.set_facecolor("#eef2f7")
        sns.barplot(data=df, x=gcol, y="attendance_rate",
                    color=COLORS["success"], alpha=0.88, ax=ax, edgecolor="white")
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels([str(df[gcol].iloc[j])[:3] for j in range(len(df))],
                           rotation=0, ha="center", fontsize=9)
        ax.axhline(75, color=COLORS["danger"], linestyle="--", linewidth=1, alpha=0.75)
        ax.set_title(auto_title, loc="left", fontsize=13, fontweight="600", color=COLORS["primary"])
        ax.set_xlabel("")
        ax.set_ylabel("Rate (%)")
        fig.tight_layout()
        return fig

    # ---- status_donut ------------------------------------------------------
    if chart_type == "status_donut":
        df_raw = store.merged()
        if classes and "class" in df_raw.columns:
            df_raw = df_raw[df_raw["class"].isin(classes)]
        if df_raw.empty or "status" not in df_raw.columns:
            return _empty_fig("No status data available.")
        sc      = df_raw["status"].value_counts()
        total_n = sc.sum()
        cmap    = {"present": COLORS["success"], "absent": COLORS["danger"],
                   "late": COLORS["warning"], "excused": "#8b5cf6"}
        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor("#eef2f7")
        wedges, _ = ax.pie(
            sc.values, labels=None, autopct=None,
            colors=[cmap.get(str(s).lower(), "#64748b") for s in sc.index],
            wedgeprops=dict(width=0.52, edgecolor="white", linewidth=1.5),
            startangle=90,
        )
        ax.set_title(auto_title, loc="left", fontsize=13, fontweight="600", color=COLORS["primary"])
        ax.legend(
            wedges,
            [f"{str(i).title():8}  {int(sc[i]):,}  ({100*sc[i]/total_n:.1f}%)" for i in sc.index],
            title="Status", loc="center left", bbox_to_anchor=(1.02, 0.5),
            fontsize=10, framealpha=0.95,
        )
        ax.set_aspect("equal")
        fig.tight_layout()
        return fig

    # ---- at_risk_bar -------------------------------------------------------
    if chart_type == "at_risk_bar":
        df = store.get_at_risk(threshold=75.0, grade="all")
        if classes:
            for col in ("cls", "class"):
                if col in df.columns:
                    df = df[df[col].isin(classes)]
                    break
        if df.empty:
            return _empty_fig("No at-risk students found.")
        df       = df.sort_values("attendance_rate")
        name_col = "name" if "name" in df.columns else "student_id"
        fig, ax  = plt.subplots(figsize=(10, max(4, len(df) * 0.35 + 2)))
        fig.patch.set_facecolor("#eef2f7")
        sns.barplot(data=df, y=name_col, x="attendance_rate",
                    color=COLORS["danger"], alpha=0.85, ax=ax, edgecolor="white")
        ax.axvline(75, color=COLORS["warning"], linestyle="--", linewidth=1.2, label="Threshold (75%)")
        ax.set_xlim(0, 82)
        ax.set_title(auto_title, loc="left", fontsize=13, fontweight="600", color=COLORS["primary"])
        ax.set_xlabel("Attendance rate (%)")
        ax.legend(fontsize=9, framealpha=0.95)
        fig.tight_layout()
        return fig

    # ---- grade_bar ---------------------------------------------------------
    if chart_type == "grade_bar":
        df = _compute_filtered(store, "grade", period, classes)
        if df.empty:
            return _empty_fig("No grade data available.")
        gcol = "grade" if "grade" in df.columns else df.columns[0]
        df   = df.sort_values("attendance_rate")
        fig, ax = plt.subplots(figsize=(9, 4.5))
        fig.patch.set_facecolor("#eef2f7")
        sns.barplot(data=df, x=gcol, y="attendance_rate",
                    palette="crest", hue=gcol, dodge=False, legend=False, ax=ax)
        ax.axhline(75,   color=COLORS["danger"], linestyle="--", linewidth=1.2, alpha=0.85, label="At-risk (75%)")
        ax.axhline(rate, color="#fbbf24",         linestyle="-.", linewidth=1.2, alpha=0.9,  label=f"Avg ({rate:.1f}%)")
        ax.set_title(auto_title, loc="left", fontsize=13, fontweight="600", color=COLORS["primary"])
        ax.set_ylabel("Attendance rate (%)")
        ax.set_xlabel("")
        ax.legend(fontsize=9, framealpha=0.95)
        fig.tight_layout()
        return fig

    # ---- fallback: generic group_by chart ----------------------------------
    df = _compute_filtered(store, group_by, period, classes)
    if df.empty:
        return _empty_fig("No data available.")
    gcol = group_by if group_by in df.columns else df.columns[0]
    df   = df.sort_values("attendance_rate")
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#eef2f7")
    sns.barplot(data=df, x=gcol, y="attendance_rate",
                palette="crest", hue=gcol, dodge=False, legend=False, ax=ax)
    ax.axhline(75, color=COLORS["danger"], linestyle="--", linewidth=1.2, alpha=0.85)
    ax.set_title(auto_title, loc="left", fontsize=13, fontweight="600", color=COLORS["primary"])
    ax.set_ylabel("Attendance rate (%)")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# build_modern_static_dashboard — full 4-panel overview
# ---------------------------------------------------------------------------

def build_modern_static_dashboard(store, period: str = "all", save: bool = True) -> plt.Figure:
    """
    Generate a 4-panel attendance dashboard.

    Parameters
    ----------
    store  : AttendanceDataStore
    period : 'all' | 'last_7_days' | 'last_30_days'
    save   : if True, write PNG to data/dashboards/attendance_dashboard_modern.png
    """
    _theme()
    summ = store.summary()

    if summ.get("status") == "no_data":
        fig, ax = plt.subplots(figsize=(9, 2.5))
        ax.text(0.5, 0.5, "No attendance data loaded.",
                ha="center", va="center", fontsize=14, color=COLORS["primary"])
        ax.axis("off")
        plt.tight_layout()
        return fig

    df_class = store.compute_stats("class",       period)
    df_week  = store.compute_stats("week",        period)
    df_dow   = store.compute_stats("day_of_week", period)

    if not df_week.empty:
        wk_col  = "week" if "week" in df_week.columns else df_week.columns[0]
        df_week = df_week.sort_values(wk_col)

    if not df_dow.empty and "day_of_week" in df_dow.columns:
        df_dow = df_dow.copy()
        df_dow["day_of_week"] = pd.Categorical(
            df_dow["day_of_week"], categories=_DAY_ORDER, ordered=True
        )
        df_dow = df_dow.sort_values("day_of_week")

    rate = summ.get("overall_attendance_rate", 0)
    dr   = summ.get("date_range", {})

    fig = plt.figure(figsize=(18, 13))
    gs  = fig.add_gridspec(nrows=4, ncols=4,
                           height_ratios=[0.11, 0.16, 1.0, 1.0],
                           hspace=0.42, wspace=0.28)

    # Header strip
    ax_head = fig.add_subplot(gs[0, :])
    ax_head.set_facecolor(COLORS["primary"])
    ax_head.axis("off")
    ax_head.text(0.03, 0.5, "Excelsis 360 — Attendance",
                 color="white", fontsize=16, fontweight="600", va="center",
                 transform=ax_head.transAxes)
    ax_head.text(0.97, 0.5,
                 f"{dr.get('from', '—')}  →  {dr.get('to', '—')}",
                 color="#cbd5e1", fontsize=11, ha="right", va="center",
                 transform=ax_head.transAxes)

    # KPI tiles
    kpis = [
        ("Attendance rate", f"{rate}%",                             COLORS["success"]),
        ("Records",         f"{summ.get('total_records', 0):,}",    COLORS["accent"]),
        ("Students",        f"{summ.get('unique_students', 0):,}",  "#38bdf8"),
        ("Absences",        f"{summ.get('total_absences', 0):,}",   COLORS["danger"]),
    ]
    for i, (lab, val, c) in enumerate(kpis):
        ax_k = fig.add_subplot(gs[1, i])
        ax_k.set_facecolor("#f1f5f9")
        for s in ax_k.spines.values():
            s.set_visible(False)
        ax_k.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        ax_k.text(0.5, 0.62, lab, ha="center", va="center",
                  fontsize=10, color="#64748b", transform=ax_k.transAxes)
        ax_k.text(0.5, 0.30, val, ha="center", va="center",
                  fontsize=15, fontweight="700", color=c, transform=ax_k.transAxes)

    # By-class bar
    ax1 = fig.add_subplot(gs[2, :2])
    if not df_class.empty:
        gcol   = "class" if "class" in df_class.columns else df_class.columns[0]
        plot_c = df_class.sort_values("attendance_rate")
        sns.barplot(data=plot_c, y=gcol, x="attendance_rate",
                    palette="crest", hue=gcol, dodge=False, legend=False, ax=ax1)
        ax1.axvline(75,   color=COLORS["danger"],  linestyle="--", linewidth=1,   alpha=0.85, label="At-risk (75%)")
        ax1.axvline(rate, color="#fbbf24",          linestyle="-.", linewidth=1.2, alpha=0.95, label=f"Avg ({rate:.1f}%)")
        ax1.set_xlim(max(45, plot_c["attendance_rate"].min() - 5), 100)
        ax1.set_title("By class", loc="left", fontsize=12, fontweight="600",
                      color=COLORS["primary"], pad=12)
        ax1.set_xlabel("Attendance rate (%)")
        ax1.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0),
                   fontsize=8, framealpha=0.95, borderaxespad=0)

    # Weekly trend line
    ax2 = fig.add_subplot(gs[2, 2:])
    if not df_week.empty:
        wcol  = "week" if "week" in df_week.columns else df_week.columns[0]
        x_idx = np.arange(len(df_week))
        ax2.plot(x_idx, df_week["attendance_rate"], marker="o",
                 linewidth=2.2, markersize=5, color=COLORS["accent"])
        ax2.axhline(75, color=COLORS["danger"], linestyle="--", linewidth=1, alpha=0.75)
        ax2.set_ylabel("Attendance rate (%)")
        ax2.set_title("Weekly trend", loc="left", fontsize=12, fontweight="600",
                      color=COLORS["primary"], pad=12)
        ax2.set_xlabel("")
        n    = len(df_week)
        step = max(1, int(np.ceil(n / 10)))
        tick_pos = x_idx[::step]
        ax2.set_xticks(tick_pos)
        ax2.set_xticklabels(
            [str(df_week[wcol].iloc[j]) for j in tick_pos],
            rotation=40, ha="right", fontsize=8,
        )
        ax2.set_xlim(-0.5, n - 0.5)

    # By-weekday bar
    ax3 = fig.add_subplot(gs[3, :2])
    if not df_dow.empty:
        gcol = "day_of_week" if "day_of_week" in df_dow.columns else df_dow.columns[0]
        sns.barplot(data=df_dow, x=gcol, y="attendance_rate",
                    color=COLORS["success"], alpha=0.88, ax=ax3, edgecolor="white")
        ax3.set_xticks(range(len(df_dow)))
        ax3.set_xticklabels(
            [str(df_dow[gcol].iloc[j])[:3] for j in range(len(df_dow))],
            rotation=0, ha="center", fontsize=9,
        )
        ax3.set_title("By weekday", loc="left", fontsize=12, fontweight="600",
                      color=COLORS["primary"], pad=12)
        ax3.set_xlabel("")
        ax3.set_ylabel("Rate (%)")

    # Status-mix donut
    ax4    = fig.add_subplot(gs[3, 2:])
    df_raw = store.merged()
    if not df_raw.empty and "status" in df_raw.columns:
        sc         = df_raw["status"].value_counts()
        cmap       = {"present": COLORS["success"], "absent": COLORS["danger"],
                      "late": COLORS["warning"], "excused": "#8b5cf6"}
        pie_colors = [cmap.get(str(s).lower(), "#64748b") for s in sc.index]
        total_n    = sc.sum()
        wedges, _  = ax4.pie(
            sc.values, labels=None, autopct=None, colors=pie_colors,
            wedgeprops=dict(width=0.52, edgecolor="white", linewidth=1.2),
            startangle=90,
        )
        ax4.set_title("Status mix", loc="left", fontsize=12, fontweight="600",
                      color=COLORS["primary"], pad=12)
        ax4.legend(
            wedges,
            [f"{str(i).title():8}  {int(sc[i]):,}  ({100*sc[i]/total_n:.1f}%)" for i in sc.index],
            title="Status", loc="center left", bbox_to_anchor=(1.02, 0.5),
            fontsize=9, framealpha=0.95, borderaxespad=0,
        )
        ax4.set_aspect("equal")

    fig.patch.set_facecolor("#eef2f7")

    if save:
        out = Path("data/dashboards/attendance_dashboard_modern.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out), dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())

    return fig
