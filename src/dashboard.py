"""
Excelsis 360 — interactive Plotly dashboard generation.

All charts use the app's dark-canvas colour tokens (matching web/tailwind.config.js),
Inter font, and are saved as self-contained interactive HTML files.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── colour tokens (mirror web/tailwind.config.js — light theme) ───────────────
CANVAS  = "#ffffff"   # snow
SURFACE = "#f9f9f9"   # fog
GRID    = "#ececec"   # arctic-mist
TEXT    = "#0d0d0d"   # carbon
MUTED   = "#5d5d5d"   # pewter
ACCENT  = "#007aff"   # link-blue
SUCCESS = "#00a86b"
WARNING = "#f5a623"
DANGER  = "#e74c3c"
PURPLE  = "#9b59b6"

STATUS_COLORS = {"present": SUCCESS, "late": WARNING, "excused": PURPLE, "absent": DANGER}


def _fmt_week(label: str) -> str:
    """'2024-01-08/2024-01-14'  →  'Jan 8'"""
    try:
        return datetime.strptime(label.split("/")[0], "%Y-%m-%d").strftime("%b %-d")
    except Exception:
        return label
_DAY_ORDER    = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
    "responsive": True,
}


def _rate_color(rate: float) -> str:
    if rate < 70:
        return DANGER
    if rate < 80:
        return WARNING
    return SUCCESS


def _base_layout(title: str = "", height: int = 480) -> dict:
    return dict(
        title=dict(
            text=title,
            font=dict(family="Plus Jakarta Sans, sans-serif", size=17, color=TEXT),
            x=0.02, xanchor="left", pad=dict(t=6, b=6),
        ),
        paper_bgcolor=CANVAS,
        plot_bgcolor=SURFACE,
        font=dict(family="Plus Jakarta Sans, sans-serif", color=TEXT, size=15),
        margin=dict(l=60, r=40, t=56 if title else 24, b=52),
        height=height,
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID,
                   tickfont=dict(size=13, color=TEXT), color=TEXT),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID,
                   tickfont=dict(size=13, color=TEXT), color=TEXT),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", bordercolor=GRID,
            font=dict(size=13, color=TEXT),
        ),
        hoverlabel=dict(
            bgcolor=SURFACE, bordercolor=GRID,
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color=TEXT),
        ),
        colorway=[ACCENT, SUCCESS, WARNING, DANGER, PURPLE],
    )


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color=TEXT, family="Plus Jakarta Sans, sans-serif"),
    )
    fig.update_layout(**_base_layout(height=300))
    return fig


def write_html(fig: go.Figure, title: str = "Excelsis 360") -> str:
    """Save an interactive Plotly figure as an HTML file; return the URL path."""
    out_dir  = Path("data/dashboards")
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"dashboard_{uuid.uuid4().hex[:8]}.html"
    path     = out_dir / filename

    body = fig.to_html(
        full_html=True,
        include_plotlyjs="cdn",
        config=_PLOTLY_CONFIG,
        div_id="chart",
    )
    # Inject Inter font and override body/chart to fill the iframe exactly
    inject = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600&display=swap"'
        ' rel="stylesheet">\n'
        f'<style>\n'
        f'  *{{box-sizing:border-box;margin:0;padding:0}}\n'
        f'  html,body{{background:{CANVAS};height:100%;overflow:hidden;margin:0}}\n'
        f'  #chart{{width:100%;height:100vh}}\n'
        f'</style>\n'
    )
    body = body.replace("</head>", inject + "</head>")
    path.write_text(body, encoding="utf-8")
    return f"/dashboards/{filename}"


def _compute_filtered(store, group_by: str, period: str, classes=None) -> pd.DataFrame:
    return store.compute_stats(group_by, period, classes=classes)


# ── individual chart builders ──────────────────────────────────────────────────

def _class_bar(store, period: str, classes, title: str) -> go.Figure:
    df = _compute_filtered(store, "class", period, classes)
    if df.empty:
        return _empty_fig("No class data available.")
    gcol = "class" if "class" in df.columns else df.columns[0]
    df   = df.sort_values("attendance_rate")
    avg  = df["attendance_rate"].mean()

    fig = go.Figure(go.Bar(
        x=df["attendance_rate"],
        y=df[gcol].astype(str),
        orientation="h",
        marker=dict(
            color=[_rate_color(r) for r in df["attendance_rate"]],
            line=dict(width=0),
        ),
        customdata=df[["present", "absent", "total"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Attendance: <b>%{x:.1f}%</b><br>"
            "Present: %{customdata[0]:,}  Absent: %{customdata[1]:,}<br>"
            "Records: %{customdata[2]:,}<extra></extra>"
        ),
    ))
    fig.add_vline(
        x=75, line=dict(color=DANGER, width=1.2, dash="dash"),
        annotation=dict(
            text="75% at-risk", font=dict(color=DANGER, size=11), bgcolor=CANVAS,
            borderpad=3, yanchor="bottom",
        ),
    )
    fig.add_vline(
        x=avg, line=dict(color=ACCENT, width=1, dash="dot"),
        annotation=dict(
            text=f"avg {avg:.1f}%", font=dict(color=ACCENT, size=11), bgcolor=CANVAS,
            borderpad=3, yanchor="top",
        ),
    )
    layout = _base_layout(title or "Attendance Rate by Class",
                          height=max(320, len(df) * 48 + 140))
    layout["xaxis"].update(
        title="Attendance rate (%)",
        range=[max(0, df["attendance_rate"].min() - 12), 102],
    )
    layout["yaxis"].update(title="")
    fig.update_layout(**layout)
    return fig


def _weekly_trend(store, period: str, classes, title: str) -> go.Figure:
    df = _compute_filtered(store, "week", period, classes)
    if df.empty:
        return _empty_fig("No weekly data available.")
    wcol = "week" if "week" in df.columns else df.columns[0]
    df   = df.sort_values(wcol)
    x_labels = [_fmt_week(str(v)) for v in df[wcol]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_labels, y=df["attendance_rate"],
        mode="lines+markers",
        line=dict(color=ACCENT, width=2.5),
        marker=dict(size=7, color=ACCENT, line=dict(width=1.5, color=CANVAS)),
        name="Attendance rate",
        customdata=df[["present", "absent", "total"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Rate: <b>%{y:.1f}%</b><br>"
            "Present: %{customdata[0]:,}  Absent: %{customdata[1]:,}<extra></extra>"
        ),
    ))
    fig.add_hline(
        y=75, line=dict(color=DANGER, width=1.2, dash="dash"),
        annotation=dict(
            text="75% threshold", font=dict(color=DANGER, size=11),
            bgcolor=CANVAS, borderpad=3, xanchor="right",
        ),
    )
    layout = _base_layout(title or "Weekly Attendance Trend", height=380)
    layout["xaxis"].update(title="", tickangle=-35, tickfont=dict(size=12, color=TEXT))
    layout["yaxis"].update(
        title="Attendance rate (%)",
        range=[max(0, df["attendance_rate"].min() - 8), 102],
    )
    fig.update_layout(**layout)
    return fig


def _weekday_bar(store, period: str, classes, title: str) -> go.Figure:
    df = _compute_filtered(store, "day_of_week", period, classes)
    if df.empty:
        return _empty_fig("No weekday data available.")
    gcol = "day_of_week" if "day_of_week" in df.columns else df.columns[0]
    if "day_of_week" in df.columns:
        df = df.copy()
        df["day_of_week"] = pd.Categorical(
            df["day_of_week"], categories=_DAY_ORDER, ordered=True
        )
        df = df.sort_values("day_of_week")

    fig = go.Figure(go.Bar(
        x=df[gcol].astype(str),
        y=df["attendance_rate"],
        marker=dict(
            color=[_rate_color(r) for r in df["attendance_rate"]],
            line=dict(width=0),
        ),
        hovertemplate="<b>%{x}</b><br>Rate: <b>%{y:.1f}%</b><extra></extra>",
    ))
    fig.add_hline(y=75, line=dict(color=DANGER, width=1.2, dash="dash"))
    layout = _base_layout(title or "Attendance by Day of Week", height=360)
    layout["yaxis"].update(
        title="Attendance rate (%)",
        range=[max(0, df["attendance_rate"].min() - 8), 102],
    )
    layout["xaxis"].update(title="")
    fig.update_layout(**layout)
    return fig


def _status_donut(store, classes, title: str) -> go.Figure:
    raw = store.merged()
    if classes and "class" in raw.columns:
        raw = raw[raw["class"].isin(classes)]
    if raw.empty or "status" not in raw.columns:
        return _empty_fig("No status data available.")
    sc     = raw["status"].value_counts()
    labels = [str(s) for s in sc.index]

    fig = go.Figure(go.Pie(
        labels=[l.title() for l in labels],
        values=sc.values,
        hole=0.52,
        marker=dict(
            colors=[STATUS_COLORS.get(s, MUTED) for s in labels],
            line=dict(color=CANVAS, width=2),
        ),
        textfont=dict(family="Plus Jakarta Sans, sans-serif", size=13, color=TEXT),
        hovertemplate="<b>%{label}</b><br>%{value:,} records  (%{percent})<extra></extra>",
    ))
    layout = _base_layout(title or "Attendance Status Distribution", height=400)
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)
    layout["legend"].update(orientation="v", x=1.02, y=0.5, yanchor="middle")
    fig.update_layout(**layout)
    return fig


def _at_risk_bar(store, threshold: float, classes, title: str) -> go.Figure:
    df = store.get_at_risk(threshold=threshold, grade="all")
    if classes:
        for col in ("cls", "class"):
            if col in df.columns:
                df = df[df[col].isin(classes)]
                break
    if df.empty:
        return _empty_fig(f"No students below {threshold:.0f}% threshold — great news!")
    df        = df.sort_values("attendance_rate")
    name_col  = "name" if "name" in df.columns else "student_id"
    class_col = next((c for c in ("cls", "class") if c in df.columns), None)
    custom    = (
        list(zip(df[class_col].astype(str), df["absent"], df["total"]))
        if class_col else
        list(zip(["—"] * len(df), df["absent"], df["total"]))
    )

    fig = go.Figure(go.Bar(
        x=df["attendance_rate"],
        y=df[name_col].astype(str),
        orientation="h",
        marker=dict(
            color=[_rate_color(r) for r in df["attendance_rate"]],
            line=dict(width=0),
        ),
        customdata=custom,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Class: %{customdata[0]}<br>"
            "Rate: <b>%{x:.1f}%</b><br>"
            "Absent: %{customdata[1]}  of %{customdata[2]}<extra></extra>"
        ),
    ))
    fig.add_vline(
        x=threshold, line=dict(color=WARNING, width=1.2, dash="dash"),
        annotation=dict(
            text=f"{threshold:.0f}%", font=dict(color=WARNING, size=11),
            bgcolor=CANVAS, borderpad=3,
        ),
    )
    layout = _base_layout(
        title or f"Students Below {threshold:.0f}% Attendance",
        height=max(320, len(df) * 34 + 140),
    )
    layout["xaxis"].update(
        title="Attendance rate (%)", range=[0, threshold + 10]
    )
    layout["yaxis"].update(title="")
    fig.update_layout(**layout)
    return fig


def _grade_bar(store, period: str, classes, title: str) -> go.Figure:
    df = _compute_filtered(store, "grade", period, classes)
    if df.empty:
        return _empty_fig("No grade data available.")
    gcol = "grade" if "grade" in df.columns else df.columns[0]
    df   = df.sort_values(gcol)

    fig = go.Figure(go.Bar(
        x=df[gcol].astype(str),
        y=df["attendance_rate"],
        marker=dict(
            color=[_rate_color(r) for r in df["attendance_rate"]],
            line=dict(width=0),
        ),
        hovertemplate="Grade <b>%{x}</b><br>Rate: <b>%{y:.1f}%</b><extra></extra>",
    ))
    fig.add_hline(y=75, line=dict(color=DANGER, width=1.2, dash="dash"))
    layout = _base_layout(title or "Attendance by Grade", height=360)
    layout["yaxis"].update(
        title="Attendance rate (%)",
        range=[max(0, df["attendance_rate"].min() - 8), 102],
    )
    layout["xaxis"].update(title="Grade")
    fig.update_layout(**layout)
    return fig


# ── full multi-panel overview ──────────────────────────────────────────────────

def build_full_dashboard(
    store,
    period: str = "all",
    classes=None,
    title: str = "",
) -> go.Figure:
    """4-panel interactive overview: class bar · weekly trend · weekday bar · status donut."""
    summ = store.summary()
    if summ.get("status") == "no_data":
        return _empty_fig("No attendance data loaded.")

    rate     = summ.get("overall_attendance_rate", 0)
    dr       = summ.get("date_range", {})
    subtitle = f"{dr.get('from','?')} → {dr.get('to','?')}  ·  overall {rate}%"

    df_class = _compute_filtered(store, "class",       period, classes)
    df_week  = _compute_filtered(store, "week",        period, classes)
    df_dow   = _compute_filtered(store, "day_of_week", period, classes)
    raw_all  = store.merged()
    if classes and "class" in raw_all.columns:
        raw_all = raw_all[raw_all["class"].isin(classes)]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["By Class", "Weekly Trend", "By Day of Week", "Status Mix"],
        specs=[
            [{"type": "bar"},    {"type": "scatter"}],
            [{"type": "bar"},    {"type": "domain"}],
        ],
        vertical_spacing=0.24,
        horizontal_spacing=0.12,
    )

    # ── panel 1: class horizontal bar ─────────────────────────────────────────
    if not df_class.empty:
        gcol = "class" if "class" in df_class.columns else df_class.columns[0]
        dfc  = df_class.sort_values("attendance_rate")
        fig.add_trace(go.Bar(
            x=dfc["attendance_rate"],
            y=dfc[gcol].astype(str),
            orientation="h",
            marker=dict(color=[_rate_color(r) for r in dfc["attendance_rate"]], line=dict(width=0)),
            hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
            showlegend=False,
        ), row=1, col=1)
        fig.add_vline(x=75, row=1, col=1,
                      line=dict(color=DANGER, width=1, dash="dash"))

    # ── panel 2: weekly trend line ────────────────────────────────────────────
    if not df_week.empty:
        wcol = "week" if "week" in df_week.columns else df_week.columns[0]
        dfw  = df_week.sort_values(wcol)
        fig.add_trace(go.Scatter(
            x=[_fmt_week(str(v)) for v in dfw[wcol]], y=dfw["attendance_rate"],
            mode="lines+markers",
            line=dict(color=ACCENT, width=2),
            marker=dict(size=5, color=ACCENT),
            hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>",
            showlegend=False,
        ), row=1, col=2)
        fig.add_hline(y=75, row=1, col=2,
                      line=dict(color=DANGER, width=1, dash="dash"))
        fig.update_xaxes(tickangle=-90, tickfont=dict(size=11, color=TEXT), row=1, col=2)

    # ── panel 3: weekday bar ──────────────────────────────────────────────────
    if not df_dow.empty:
        gcol = "day_of_week" if "day_of_week" in df_dow.columns else df_dow.columns[0]
        dfd  = df_dow.copy()
        if "day_of_week" in dfd.columns:
            dfd["day_of_week"] = pd.Categorical(
                dfd["day_of_week"], categories=_DAY_ORDER, ordered=True
            )
            dfd = dfd.sort_values("day_of_week")
        fig.add_trace(go.Bar(
            x=dfd[gcol].astype(str),
            y=dfd["attendance_rate"],
            marker=dict(color=[_rate_color(r) for r in dfd["attendance_rate"]], line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>",
            showlegend=False,
        ), row=2, col=1)
        fig.add_hline(y=75, row=2, col=1,
                      line=dict(color=DANGER, width=1, dash="dash"))

    # ── panel 4: status donut ─────────────────────────────────────────────────
    if not raw_all.empty and "status" in raw_all.columns:
        sc     = raw_all["status"].value_counts()
        labels = [str(s) for s in sc.index]
        fig.add_trace(go.Pie(
            labels=[l.title() for l in labels],
            values=sc.values,
            hole=0.5,
            marker=dict(
                colors=[STATUS_COLORS.get(s, MUTED) for s in labels],
                line=dict(color=CANVAS, width=2),
            ),
            hovertemplate="<b>%{label}</b><br>%{value:,}  (%{percent})<extra></extra>",
            showlegend=True,
        ), row=2, col=2)

    full_title = title or f"Excelsis 360 — Attendance Overview"
    fig.update_layout(
        title=dict(
            text=f"{full_title}<br><sup style='color:{MUTED};font-size:11px'>{subtitle}</sup>",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=15, color=TEXT),
            x=0.02, xanchor="left",
        ),
        paper_bgcolor=CANVAS,
        plot_bgcolor=SURFACE,
        font=dict(family="Plus Jakarta Sans, sans-serif", color=TEXT, size=14),
        height=720,
        margin=dict(l=60, r=40, t=80, b=40),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", bordercolor=GRID,
            font=dict(size=13, color=TEXT),
            x=0.88, y=0.18,
        ),
        hoverlabel=dict(
            bgcolor=SURFACE, bordercolor=GRID,
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color=TEXT),
        ),
    )
    # Apply dark styling to all Cartesian axes
    for attr in vars(fig.layout):
        if attr.startswith(("xaxis", "yaxis")):
            getattr(fig.layout, attr).update(
                gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID,
                tickfont=dict(size=12, color=TEXT), color=TEXT,
            )
    # Style subplot title annotations
    for ann in fig.layout.annotations:
        ann.font.update(family="Plus Jakarta Sans, sans-serif", size=14, color=TEXT)

    return fig


# ── query router ──────────────────────────────────────────────────────────────

def build_query_dashboard(
    store,
    chart_type: str = "class_bar",
    group_by: str = "class",
    period: str = "all",
    title: str = "",
    classes=None,
) -> go.Figure:
    """Route to the correct chart and return an interactive Plotly figure."""
    summ = store.summary()
    if summ.get("status") == "no_data":
        return _empty_fig("No attendance data loaded.")

    if chart_type == "full":
        return build_full_dashboard(store, period=period, classes=classes, title=title)
    if chart_type == "class_bar":
        return _class_bar(store, period, classes, title)
    if chart_type == "weekly_trend":
        return _weekly_trend(store, period, classes, title)
    if chart_type == "weekday_bar":
        return _weekday_bar(store, period, classes, title)
    if chart_type == "status_donut":
        return _status_donut(store, classes, title)
    if chart_type == "at_risk_bar":
        return _at_risk_bar(store, 75.0, classes, title)
    if chart_type == "grade_bar":
        return _grade_bar(store, period, classes, title)

    # Unknown chart_type — fall back to the most relevant chart by group_by
    if group_by == "week":
        return _weekly_trend(store, period, classes, title)
    if group_by == "grade":
        return _grade_bar(store, period, classes, title)
    if group_by == "day_of_week":
        return _weekday_bar(store, period, classes, title)
    return _class_bar(store, period, classes, title)
