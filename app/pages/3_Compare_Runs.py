"""Page 4 — Compare Runs."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.ui_utils import (
    NEBIUS_BLUE, NEBIUS_CARD, NEBIUS_BORDER, NEBIUS_MUTED, NEBIUS_TEXT,
    NEBIUS_SUCCESS, NEBIUS_ERROR, NEBIUS_WARNING,
    apply_global_styles, page_header, PLOTLY_THEME,
    chart_compare_runs,
)
from benchmark.storage.database import get_session_factory, init_db
from benchmark.storage.repository import BenchmarkRepository

st.set_page_config(page_title="Compare Runs · NebiusBench", page_icon="🔍", layout="wide")
apply_global_styles()
page_header("Compare Runs", "Side-by-side comparison of benchmark runs", "🔍")

init_db()


def _load_runs():
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            return repo.get_run_summary_list()
    except Exception:
        return []


def _load_results(run_id: str):
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            return repo.get_results(run_id)
    except Exception:
        return []


runs = _load_runs()
completed_runs = [r for r in runs if r["status"] == "completed"]

if len(completed_runs) < 2:
    st.markdown(
        f"""<div style="background:{NEBIUS_CARD};border:1px dashed {NEBIUS_BORDER};
                      border-radius:12px;padding:60px;text-align:center;color:{NEBIUS_MUTED}">
            <div style="font-size:3rem;margin-bottom:16px">🔍</div>
            <h3 style="color:{NEBIUS_TEXT}">Need at least 2 completed runs to compare</h3>
            <p>Run more benchmarks from the <strong>Run Benchmark</strong> page.</p>
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()

# ─── Run Selection ────────────────────────────────────────────────────────────
st.markdown("#### Select Runs to Compare")
run_options = {r["id"]: f"{r['name']} — {r['model']} ({r['created_at']})" for r in completed_runs}

col_sel1, col_sel2 = st.columns(2)
with col_sel1:
    run_a_id = st.selectbox("Run A", list(run_options.keys()),
                             format_func=lambda x: run_options[x], index=0)
with col_sel2:
    remaining = [rid for rid in run_options if rid != run_a_id]
    run_b_id = st.selectbox("Run B", remaining,
                             format_func=lambda x: run_options[x], index=0)

extra_ids: list[str] = []
with st.expander("Add more runs (up to 4 total)"):
    for i, rid in enumerate(run_options):
        if rid not in (run_a_id, run_b_id) and len(extra_ids) < 2:
            if st.checkbox(run_options[rid], key=f"extra_{i}"):
                extra_ids.append(rid)

selected_ids = [run_a_id, run_b_id] + extra_ids
selected_metas = {r["id"]: r for r in completed_runs if r["id"] in selected_ids}
selected_results = {rid: _load_results(rid) for rid in selected_ids}


def _get_endpoint_metrics(results) -> dict:
    ep = next((r for r in results if r.result_type == "endpoint"), None)
    return ep.metrics if ep else {}


def _get_sweep_results(results):
    return [r for r in results if r.result_type == "concurrency"]


# ─── KPI Comparison Table ─────────────────────────────────────────────────────
st.divider()
st.markdown("#### KPI Comparison")

comparison_rows = []
metric_keys = [
    ("ttft_p50", "TTFT p50 (ms)", lambda m: m.get("ttft", {}).get("p50")),
    ("ttft_p90", "TTFT p90 (ms)", lambda m: m.get("ttft", {}).get("p90")),
    ("ttft_p99", "TTFT p99 (ms)", lambda m: m.get("ttft", {}).get("p99")),
    ("throughput_rps", "Throughput (rps)", lambda m: m.get("throughput_rps")),
    ("tokens_per_second", "Tokens/sec", lambda m: m.get("tokens_per_second")),
    ("error_rate_pct", "Error Rate (%)", lambda m: (m.get("error_rate", 0) or 0) * 100),
    ("latency_p50", "Latency p50 (ms)", lambda m: m.get("latency", {}).get("p50")),
    ("latency_p99", "Latency p99 (ms)", lambda m: m.get("latency", {}).get("p99")),
    ("total_tokens", "Total Tokens", lambda m: m.get("total_tokens")),
    ("duration_s", "Duration (s)", lambda m: m.get("duration_seconds")),
]

table_data: dict[str, list] = {"Metric": [mk[1] for mk in metric_keys]}
run_values: dict[str, dict] = {}

for rid in selected_ids:
    meta = selected_metas.get(rid, {})
    run_label = meta.get("name", rid[:8])
    metrics = _get_endpoint_metrics(selected_results.get(rid, []))
    vals = []
    run_values[run_label] = {}
    for key, label, extractor in metric_keys:
        v = extractor(metrics)
        run_values[run_label][label] = v
        if v is not None:
            if "Rate" in label:
                vals.append(f"{v:.2f}%")
            elif "Tokens" == label.split()[0] and "sec" not in label:
                vals.append(f"{int(v):,}")
            else:
                vals.append(f"{v:.2f}")
        else:
            vals.append("—")
    table_data[run_label] = vals

df_compare = pd.DataFrame(table_data)

def _highlight_best(val: str, col_vals: list[str], higher_is_better: bool) -> str:
    try:
        nums = [float(v.replace("%", "").replace(",", "")) if v != "—" else None for v in col_vals]
        nums_clean = [n for n in nums if n is not None]
        if not nums_clean or val == "—":
            return ""
        num = float(val.replace("%", "").replace(",", ""))
        best = max(nums_clean) if higher_is_better else min(nums_clean)
        worst = min(nums_clean) if higher_is_better else max(nums_clean)
        if abs(num - best) < 1e-9:
            return f"background-color: rgba(0,200,150,0.15); color: {NEBIUS_SUCCESS}"
        if abs(num - worst) < 1e-9 and len(nums_clean) > 1:
            return f"background-color: rgba(255,75,75,0.1); color: {NEBIUS_ERROR}"
    except Exception:
        pass
    return ""

st.dataframe(df_compare, use_container_width=True, hide_index=True)

st.divider()

# ─── Visual Charts ────────────────────────────────────────────────────────────
st.markdown("#### Visual Comparison")

tab1, tab2, tab3 = st.tabs(["Latency", "Throughput", "Concurrency Sweep"])

with tab1:
    chart_metrics = [
        ("TTFT p50 (ms)", False),
        ("TTFT p90 (ms)", False),
        ("TTFT p99 (ms)", False),
        ("Latency p50 (ms)", False),
    ]

    rows = []
    for run_label, metrics_dict in run_values.items():
        for metric_name, _ in chart_metrics:
            v = metrics_dict.get(metric_name)
            if v is not None:
                rows.append({"Run": run_label, "Metric": metric_name, "Value": v})

    if rows:
        df_lat = pd.DataFrame(rows)
        import plotly.express as px
        fig_lat = px.bar(
            df_lat, x="Metric", y="Value", color="Run", barmode="group",
            title="Latency Comparison",
            color_discrete_sequence=[NEBIUS_BLUE, NEBIUS_SUCCESS, NEBIUS_WARNING, "#A78BFA"],
        )
        fig_lat.update_layout(**PLOTLY_THEME, height=420, margin=dict(l=40,r=20,t=40,b=80),
                               xaxis_title="", yaxis_title="ms")
        st.plotly_chart(fig_lat, use_container_width=True)

with tab2:
    tput_rows = []
    for run_label, metrics_dict in run_values.items():
        rps = metrics_dict.get("Throughput (rps)")
        tps = metrics_dict.get("Tokens/sec")
        if rps is not None:
            tput_rows.append({"Run": run_label, "Metric": "Requests/sec", "Value": rps})
        if tps is not None:
            tput_rows.append({"Run": run_label, "Metric": "Tokens/sec", "Value": tps / 100})

    if tput_rows:
        import plotly.express as px
        df_tput = pd.DataFrame(tput_rows)
        fig_tput = px.bar(
            df_tput, x="Metric", y="Value", color="Run", barmode="group",
            title="Throughput Comparison",
            color_discrete_sequence=[NEBIUS_BLUE, NEBIUS_SUCCESS, NEBIUS_WARNING, "#A78BFA"],
            text_auto=".2f",
        )
        fig_tput.update_traces(textposition="outside")
        fig_tput.update_layout(**PLOTLY_THEME, height=380, margin=dict(l=40,r=20,t=40,b=60),
                                xaxis_title="", yaxis_title="Rate")
        st.plotly_chart(fig_tput, use_container_width=True)

with tab3:
    has_sweep = any(
        _get_sweep_results(selected_results.get(rid, [])) for rid in selected_ids
    )
    if not has_sweep:
        st.info("No concurrency sweep data. Enable sweep when running benchmarks.")
    else:
        fig_sweep = go.Figure()
        colors = [NEBIUS_BLUE, NEBIUS_SUCCESS, NEBIUS_WARNING, "#A78BFA"]
        for idx, rid in enumerate(selected_ids):
            sweep = _get_sweep_results(selected_results.get(rid, []))
            if not sweep:
                continue
            sweep_sorted = sorted(sweep, key=lambda r: r.concurrency_level)
            levels = [r.concurrency_level for r in sweep_sorted]
            rps = [r.metrics.get("throughput_rps", 0) for r in sweep_sorted]
            run_label = selected_metas.get(rid, {}).get("name", rid[:8])
            fig_sweep.add_trace(go.Scatter(
                x=levels, y=rps, name=run_label,
                line=dict(color=colors[idx % len(colors)], width=2.5),
                mode="lines+markers", marker=dict(size=7),
            ))
        fig_sweep.update_layout(
            **PLOTLY_THEME,
            title="Throughput (rps) vs Concurrency",
            xaxis_title="Concurrency Level",
            yaxis_title="Requests/sec",
            height=400,
            margin=dict(l=40,r=20,t=40,b=40),
        )
        st.plotly_chart(fig_sweep, use_container_width=True)

st.divider()

# ─── Delta Summary ────────────────────────────────────────────────────────────
if len(selected_ids) == 2:
    st.markdown("#### Delta Analysis (Run B vs Run A)")
    meta_a = selected_metas.get(run_a_id, {})
    meta_b = selected_metas.get(run_b_id, {})
    m_a = _get_endpoint_metrics(selected_results.get(run_a_id, []))
    m_b = _get_endpoint_metrics(selected_results.get(run_b_id, []))

    delta_metrics = [
        ("TTFT p50", m_a.get("ttft", {}).get("p50"), m_b.get("ttft", {}).get("p50"), False, "ms"),
        ("TTFT p99", m_a.get("ttft", {}).get("p99"), m_b.get("ttft", {}).get("p99"), False, "ms"),
        ("Throughput", m_a.get("throughput_rps"), m_b.get("throughput_rps"), True, "rps"),
        ("Tokens/sec", m_a.get("tokens_per_second"), m_b.get("tokens_per_second"), True, "tok/s"),
        ("Error Rate", m_a.get("error_rate", 0), m_b.get("error_rate", 0), False, "%"),
    ]

    delta_cols = st.columns(len(delta_metrics))
    for col, (name, val_a, val_b, higher_better, unit) in zip(delta_cols, delta_metrics):
        if val_a is not None and val_b is not None and val_a != 0:
            pct_delta = ((val_b - val_a) / abs(val_a)) * 100
            improved = (pct_delta > 0) == higher_better
            color = NEBIUS_SUCCESS if improved else NEBIUS_ERROR
            arrow = "↑" if pct_delta > 0 else "↓"
            col.markdown(
                f"""<div class="info-card" style="border-left-color:{color};text-align:center">
                <div style="color:{NEBIUS_MUTED};font-size:0.75rem;text-transform:uppercase">{name}</div>
                <div style="color:{color};font-size:1.4rem;font-weight:700">{arrow} {abs(pct_delta):.1f}%</div>
                <div style="color:{NEBIUS_MUTED};font-size:0.8rem">
                    {val_a:.2f} → {val_b:.2f} {unit}
                </div>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            col.markdown(
                f"""<div class="info-card" style="text-align:center">
                <div style="color:{NEBIUS_MUTED};font-size:0.75rem;text-transform:uppercase">{name}</div>
                <div style="color:{NEBIUS_MUTED};font-size:1rem">— N/A —</div>
                </div>""",
                unsafe_allow_html=True,
            )
