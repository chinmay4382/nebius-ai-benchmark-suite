"""Shared Streamlit UI helpers — styling, charts, and layout utilities."""

from __future__ import annotations

from typing import Any, Optional

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

# ─── Design Tokens ────────────────────────────────────────────────────────────

NEBIUS_BLUE = "#00A3FF"
NEBIUS_NAVY = "#1C2333"
NEBIUS_DARK = "#0E1117"
NEBIUS_CARD = "#141824"
NEBIUS_BORDER = "#2D3748"
NEBIUS_SUCCESS = "#00C896"
NEBIUS_WARNING = "#FFB547"
NEBIUS_ERROR = "#FF4B4B"
NEBIUS_TEXT = "#E8EAF0"
NEBIUS_MUTED = "#8892A4"

PLOTLY_THEME = {
    "plot_bgcolor": NEBIUS_NAVY,
    "paper_bgcolor": NEBIUS_DARK,
    "font": {"color": NEBIUS_TEXT, "family": "Inter, system-ui, sans-serif"},
    "colorway": [NEBIUS_BLUE, NEBIUS_SUCCESS, NEBIUS_WARNING, "#A78BFA", "#F472B6", "#34D399"],
    "xaxis": {"gridcolor": NEBIUS_BORDER, "linecolor": NEBIUS_BORDER},
    "yaxis": {"gridcolor": NEBIUS_BORDER, "linecolor": NEBIUS_BORDER},
}

_CSS = f"""
<style>
/* ── Global ── */
html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: {NEBIUS_NAVY};
    border-right: 1px solid {NEBIUS_BORDER};
}}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {{
    color: {NEBIUS_BLUE};
}}

/* ── Metric cards ── */
[data-testid="metric-container"] {{
    background: {NEBIUS_CARD};
    border: 1px solid {NEBIUS_BORDER};
    border-radius: 10px;
    padding: 16px 20px;
    transition: border-color 0.2s;
}}
[data-testid="metric-container"]:hover {{
    border-color: {NEBIUS_BLUE};
}}
[data-testid="stMetricLabel"] {{
    color: {NEBIUS_MUTED} !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
[data-testid="stMetricValue"] {{
    color: {NEBIUS_TEXT} !important;
    font-size: 1.6rem !important;
    font-weight: 700;
}}
[data-testid="stMetricDelta"] {{
    font-size: 0.8rem !important;
}}

/* ── Buttons ── */
.stButton > button {{
    background: linear-gradient(135deg, {NEBIUS_BLUE} 0%, #0077CC 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.5rem 1.4rem;
    transition: all 0.2s;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(0,163,255,0.3);
}}

/* ── Progress ── */
[data-testid="stProgress"] > div > div {{
    background: {NEBIUS_BLUE};
    border-radius: 4px;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab"] {{
    color: {NEBIUS_MUTED};
    font-weight: 500;
}}
.stTabs [aria-selected="true"] {{
    color: {NEBIUS_BLUE} !important;
    border-bottom: 2px solid {NEBIUS_BLUE} !important;
}}

/* ── Divider ── */
hr {{
    border-color: {NEBIUS_BORDER};
}}

/* ── Section header ── */
.section-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid {NEBIUS_BORDER};
}}

/* ── Status badges ── */
.badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.badge-success {{ background: rgba(0,200,150,0.15); color: {NEBIUS_SUCCESS}; border: 1px solid {NEBIUS_SUCCESS}; }}
.badge-running {{ background: rgba(0,163,255,0.15); color: {NEBIUS_BLUE}; border: 1px solid {NEBIUS_BLUE}; }}
.badge-failed  {{ background: rgba(255,75,75,0.15);  color: {NEBIUS_ERROR};   border: 1px solid {NEBIUS_ERROR}; }}
.badge-pending {{ background: rgba(255,181,71,0.15); color: {NEBIUS_WARNING}; border: 1px solid {NEBIUS_WARNING}; }}

/* ── Info card ── */
.info-card {{
    background: {NEBIUS_CARD};
    border: 1px solid {NEBIUS_BORDER};
    border-left: 3px solid {NEBIUS_BLUE};
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
}}
</style>
"""


def apply_global_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    apply_global_styles()
    cols = st.columns([1, 10])
    with cols[0]:
        if icon:
            st.markdown(f"<div style='font-size:2.4rem;margin-top:4px'>{icon}</div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(
            f"<h1 style='margin:0;color:{NEBIUS_TEXT};font-weight:700;font-size:1.8rem'>{title}</h1>"
            f"<p style='margin:2px 0 0;color:{NEBIUS_MUTED};font-size:0.9rem'>{subtitle}</p>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='margin:12px 0 20px'/>", unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: Optional[str] = None, delta_ok: bool = True) -> None:
    color = NEBIUS_SUCCESS if delta_ok else NEBIUS_ERROR
    delta_html = f"<span style='color:{color};font-size:0.8rem'>{delta}</span>" if delta else ""
    st.markdown(
        f"""<div class="info-card">
        <div style='color:{NEBIUS_MUTED};font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em'>{label}</div>
        <div style='color:{NEBIUS_TEXT};font-size:1.5rem;font-weight:700;margin:4px 0'>{value}</div>
        {delta_html}
        </div>""",
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    cls = {
        "completed": "badge-success",
        "running": "badge-running",
        "failed": "badge-failed",
        "pending": "badge-pending",
    }.get(status.lower(), "badge-pending")
    return f'<span class="badge {cls}">{status}</span>'


# ─── Plotly Chart Builders ────────────────────────────────────────────────────

def _apply_theme(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        **PLOTLY_THEME,
        height=height,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(
            bgcolor="rgba(28,35,51,0.8)",
            bordercolor=NEBIUS_BORDER,
            borderwidth=1,
        ),
    )
    return fig


def chart_ttft_distribution(ttft_values: list[float], title: str = "TTFT Distribution") -> go.Figure:
    fig = px.histogram(
        x=ttft_values,
        nbins=40,
        title=title,
        labels={"x": "TTFT (ms)", "y": "Count"},
        color_discrete_sequence=[NEBIUS_BLUE],
    )
    return _apply_theme(fig)


def chart_latency_percentiles(
    p50: list[float], p90: list[float], p99: list[float], x_labels: Optional[list] = None
) -> go.Figure:
    x = x_labels or list(range(len(p50)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=p50, name="p50", line=dict(color=NEBIUS_SUCCESS, width=2)))
    fig.add_trace(go.Scatter(x=x, y=p90, name="p90", line=dict(color=NEBIUS_WARNING, width=2)))
    fig.add_trace(go.Scatter(x=x, y=p99, name="p99", line=dict(color=NEBIUS_ERROR, width=2),
                             fill="tonexty", fillcolor="rgba(255,75,75,0.05)"))
    fig.update_layout(title="TTFT Percentiles Over Time", xaxis_title="Request #", yaxis_title="ms")
    return _apply_theme(fig)


def chart_throughput_vs_concurrency(concurrency: list[int], rps: list[float], tps: list[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=concurrency, y=rps, name="Requests/sec",
        line=dict(color=NEBIUS_BLUE, width=2.5), mode="lines+markers",
        marker=dict(size=7),
    ))
    fig.add_trace(go.Scatter(
        x=concurrency, y=[t / 100 for t in tps], name="Tokens/sec ÷100",
        line=dict(color=NEBIUS_SUCCESS, width=2.5, dash="dot"), mode="lines+markers",
        marker=dict(size=7),
    ))
    fig.update_layout(
        title="Throughput vs Concurrency",
        xaxis_title="Concurrency Level",
        yaxis_title="Rate",
    )
    return _apply_theme(fig)


def chart_latency_vs_concurrency(
    concurrency: list[int], p50: list[float], p99: list[float]
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=concurrency, y=p50, name="TTFT p50",
        fill="tozeroy", fillcolor=f"rgba(0,163,255,0.1)",
        line=dict(color=NEBIUS_BLUE, width=2.5), mode="lines+markers",
    ))
    fig.add_trace(go.Scatter(
        x=concurrency, y=p99, name="TTFT p99",
        line=dict(color=NEBIUS_ERROR, width=2, dash="dash"), mode="lines+markers",
    ))
    fig.update_layout(
        title="TTFT Latency vs Concurrency",
        xaxis_title="Concurrency Level",
        yaxis_title="Latency (ms)",
    )
    return _apply_theme(fig)


def chart_error_rate_vs_concurrency(concurrency: list[int], error_pct: list[float]) -> go.Figure:
    colors = [NEBIUS_ERROR if e > 5 else NEBIUS_WARNING if e > 1 else NEBIUS_SUCCESS for e in error_pct]
    fig = go.Figure(go.Bar(
        x=[str(c) for c in concurrency],
        y=error_pct,
        marker_color=colors,
        name="Error Rate %",
    ))
    fig.update_layout(
        title="Error Rate vs Concurrency",
        xaxis_title="Concurrency Level",
        yaxis_title="Error Rate (%)",
    )
    return _apply_theme(fig)


def chart_cost_projection(projections: dict[str, float]) -> go.Figure:
    labels = list(projections.keys())
    values = list(projections.values())
    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker=dict(
            color=values,
            colorscale=[[0, NEBIUS_SUCCESS], [0.5, NEBIUS_WARNING], [1, NEBIUS_ERROR]],
            showscale=False,
        ),
        text=[f"${v:.2f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        title="Projected Monthly Cost",
        xaxis_title="Request Volume",
        yaxis_title="Monthly Cost (USD)",
    )
    return _apply_theme(fig)


def chart_compare_runs(df: pd.DataFrame, metric: str, run_col: str = "Run") -> go.Figure:
    fig = px.bar(
        df,
        x=run_col,
        y=metric,
        color=run_col,
        color_discrete_sequence=[NEBIUS_BLUE, NEBIUS_SUCCESS, NEBIUS_WARNING, "#A78BFA"],
        title=f"Comparison: {metric}",
        text_auto=".2f",
    )
    fig.update_traces(textposition="outside")
    return _apply_theme(fig)


def sidebar_config() -> dict[str, Any]:
    """Render the global sidebar and return settings."""
    with st.sidebar:
        st.markdown(
            f"""<div style='text-align:center;padding:16px 0 8px'>
            <div style='font-size:2rem'>⚡</div>
            <div style='color:{NEBIUS_BLUE};font-size:1.1rem;font-weight:700'>NebiusBench</div>
            <div style='color:{NEBIUS_MUTED};font-size:0.75rem'>v0.1.0</div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown(f"<div style='color:{NEBIUS_MUTED};font-size:0.75rem;padding:4px 0'>NAVIGATION</div>",
                    unsafe_allow_html=True)
        pages = {
            "Home": "🏠",
            "Run Benchmark": "🚀",
            "Live Metrics": "📊",
            "Compare Runs": "🔍",
            "Cost Analysis": "💰",
            "Report Generator": "📄",
        }
        for name, icon in pages.items():
            st.markdown(f"{icon} **{name}**")
        st.divider()
        st.markdown(f"<div style='color:{NEBIUS_MUTED};font-size:0.7rem;text-align:center'>Powered by Nebius AI</div>",
                    unsafe_allow_html=True)
    return {}
