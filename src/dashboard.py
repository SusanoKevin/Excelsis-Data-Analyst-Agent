"""
Dashboard generation extracted from Excelsis.ipynb Cell 4.
Imported by both the notebook and the FastAPI backend.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend safe for server use

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
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


def build_modern_static_dashboard(store, period: str = "all", save: bool = True) -> plt.Figure:
    """
    Generate a 4-panel attendance dashboard.

    Parameters
    ----------
    store   : AttendanceDataStore
    period  : 'all' | 'last_7_days' | 'last_30_days'
    save    : if True, write PNG to data/dashboards/attendance_dashboard_modern.png

    Returns the matplotlib Figure (caller can savefig to a custom path).
    """
    import pandas as pd

    _theme()
    summ = store.summary()

    if summ.get("status") == "no_data":
        fig, ax = plt.subplots(figsize=(9, 2.5))
        ax.text(0.5, 0.5, "No attendance data loaded.",
                ha="center", va="center", fontsize=14, color=COLORS["primary"])
        ax.axis("off")
        plt.tight_layout()
        return fig

    df_class = store.compute_stats("class",      period)
    df_week  = store.compute_stats("week",       period)
    df_dow   = store.compute_stats("day_of_week", period)

    if not df_week.empty:
        wk_col = "week" if "week" in df_week.columns else df_week.columns[0]
        df_week = df_week.sort_values(wk_col)

    if not df_dow.empty and "day_of_week" in df_dow.columns:
        df_dow = df_dow.copy()
        df_dow["day_of_week"] = pd.Categorical(
            df_dow["day_of_week"], categories=_DAY_ORDER, ordered=True
        )
        df_dow = df_dow.sort_values("day_of_week")

    rate = summ.get("overall_attendance_rate", 0)
    dr   = summ.get("date_range", {})

    fig = plt.figure(figsize=(15, 11), constrained_layout=True)
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
        ("Attendance rate", f"{rate}%",                              COLORS["success"]),
        ("Records",         f"{summ.get('total_records', 0):,}",     COLORS["accent"]),
        ("Students",        f"{summ.get('unique_students', 0):,}",   "#38bdf8"),
        ("Absences",        f"{summ.get('total_absences', 0):,}",    COLORS["danger"]),
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
        gcol = "class" if "class" in df_class.columns else df_class.columns[0]
        plot_c = df_class.sort_values("attendance_rate")
        sns.barplot(data=plot_c, y=gcol, x="attendance_rate",
                    palette="crest", hue=gcol, dodge=False, legend=False, ax=ax1)
        ax1.axvline(75,   color=COLORS["danger"],  linestyle="--", linewidth=1, alpha=0.85, label="At-risk (75%)")
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
        ax3.set_xticklabels(
            [t.get_text()[:3] for t in ax3.get_xticklabels()],
            rotation=0, ha="center", fontsize=9,
        )
        ax3.set_title("By weekday", loc="left", fontsize=12, fontweight="600",
                      color=COLORS["primary"], pad=12)
        ax3.set_xlabel("")
        ax3.set_ylabel("Rate (%)")

    # Status-mix donut
    ax4   = fig.add_subplot(gs[3, 2:])
    df_raw = store.merged()
    if not df_raw.empty and "status" in df_raw.columns:
        sc   = df_raw["status"].value_counts()
        cmap = {"present": COLORS["success"], "absent": COLORS["danger"],
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
