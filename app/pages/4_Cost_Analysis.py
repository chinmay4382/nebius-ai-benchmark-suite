"""Page 5 — Cost Analysis."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.ui_utils import (
    NEBIUS_BLUE, NEBIUS_CARD, NEBIUS_BORDER, NEBIUS_MUTED, NEBIUS_TEXT,
    NEBIUS_SUCCESS, NEBIUS_ERROR, NEBIUS_WARNING,
    apply_global_styles, page_header, PLOTLY_THEME, chart_cost_projection,
)
from benchmark.runner import estimate_cost, get_model_pricing
from benchmark.storage.database import get_session_factory, init_db
from benchmark.storage.repository import BenchmarkRepository

st.set_page_config(page_title="Cost Analysis · NebiusBench", page_icon="💰", layout="wide")
apply_global_styles()
page_header("Cost Analysis", "Cost estimation, projections, and per-model comparison", "💰")

init_db()

pricing = get_model_pricing()


def _load_run_summaries():
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


tab_runs, tab_estimator, tab_model_compare = st.tabs(
    ["Run Cost History", "Cost Estimator", "Model Price Comparison"]
)

# ─── Tab 1: Run Cost History ──────────────────────────────────────────────────
with tab_runs:
    runs = _load_run_summaries()
    completed = [r for r in runs if r["status"] == "completed"]

    if not completed:
        st.info("No completed benchmark runs. Run a benchmark to see cost data.")
    else:
        cost_rows = []
        for run_meta in completed:
            results = _load_results(run_meta["id"])
            ep = next((r for r in results if r.result_type == "endpoint"), None)
            if not ep:
                continue
            m = ep.metrics
            model_id = run_meta.get("model", "unknown")
            total_tokens = m.get("total_tokens", 0)
            prompt_tokens = int(total_tokens * 0.6)
            completion_tokens = total_tokens - prompt_tokens

            if total_tokens > 0 and model_id in pricing:
                p = pricing[model_id]
                cost_usd = (
                    (prompt_tokens / 1_000_000) * p.input_per_1m_tokens
                    + (completion_tokens / 1_000_000) * p.output_per_1m_tokens
                )
                req_count = m.get("total_requests", 1)
                cost_rows.append({
                    "Run": run_meta["name"],
                    "Model": model_id.split("/")[-1],
                    "Requests": req_count,
                    "Total Tokens": total_tokens,
                    "Cost (USD)": round(cost_usd, 6),
                    "Cost/Request": round(cost_usd / max(req_count, 1), 8),
                    "Cost/1M Tok": round(cost_usd / max(total_tokens, 1) * 1_000_000, 4),
                    "Date": run_meta["created_at"],
                })

        if cost_rows:
            df_cost = pd.DataFrame(cost_rows)
            st.dataframe(df_cost, use_container_width=True, hide_index=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Spend (all runs)", f"${sum(r['Cost (USD)'] for r in cost_rows):.4f}")
            col2.metric("Avg Cost/Run", f"${sum(r['Cost (USD)'] for r in cost_rows)/len(cost_rows):.4f}")
            col3.metric("Total Requests Benchmarked", f"{sum(r['Requests'] for r in cost_rows):,}")

            if len(cost_rows) > 1:
                fig_trend = px.line(
                    df_cost, x="Date", y="Cost (USD)", color="Model",
                    title="Cost Trend Across Runs",
                    markers=True,
                    color_discrete_sequence=[NEBIUS_BLUE, NEBIUS_SUCCESS, NEBIUS_WARNING],
                )
                fig_trend.update_layout(**PLOTLY_THEME, height=380, margin=dict(l=40,r=20,t=40,b=60))
                st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No token usage data available. Benchmarks with streaming provide token counts.")

# ─── Tab 2: Cost Estimator ────────────────────────────────────────────────────
with tab_estimator:
    st.markdown("#### Interactive Cost Calculator")

    col_form, col_result = st.columns([4, 6])

    with col_form:
        model_options = list(pricing.keys())
        sel_model = st.selectbox("Model", model_options, key="est_model")
        avg_prompt_tokens = st.number_input(
            "Avg Prompt Tokens / Request", min_value=1, max_value=32000, value=150, step=10
        )
        avg_completion_tokens = st.number_input(
            "Avg Completion Tokens / Request", min_value=1, max_value=8192, value=256, step=10
        )
        daily_requests = st.number_input(
            "Daily Requests", min_value=1, max_value=10_000_000, value=10_000, step=1000
        )
        bench_requests = st.number_input(
            "Benchmark Request Count (for single run cost)", min_value=1, max_value=10000, value=100
        )

        st.markdown("---")
        if sel_model in pricing:
            p = pricing[sel_model]
            st.markdown(
                f"""<div class="info-card">
                <strong>Input pricing:</strong> ${p.input_per_1m_tokens:.4f} / 1M tokens<br>
                <strong>Output pricing:</strong> ${p.output_per_1m_tokens:.4f} / 1M tokens
                </div>""",
                unsafe_allow_html=True,
            )

    with col_result:
        ce = estimate_cost(
            model_id=sel_model,
            prompt_tokens=avg_prompt_tokens * bench_requests,
            completion_tokens=avg_completion_tokens * bench_requests,
            request_count=bench_requests,
            daily_requests=daily_requests,
        )

        st.markdown("#### Single Benchmark Run Cost")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Total Cost", f"${ce.total_cost_usd:.6f}")
        cc2.metric("Cost / Request", f"${ce.cost_per_request_usd:.8f}")
        cc3.metric("Cost / 1M Tokens", f"${ce.cost_per_1m_tokens_usd:.4f}")

        st.markdown("#### Monthly Projections")
        proj_labels = {
            "1k_req_day": "1K req/day",
            "10k_req_day": "10K req/day",
            "100k_req_day": "100K req/day",
            "1m_req_day": "1M req/day",
        }
        proj_data = {proj_labels.get(k, k): v for k, v in ce.projected_monthly_cost_at_rps.items()}

        mc1, mc2, mc3, mc4 = st.columns(4)
        for col, (label, val) in zip([mc1, mc2, mc3, mc4], proj_data.items()):
            col.metric(label, f"${val:.2f}/mo")

        fig_proj = chart_cost_projection(proj_data)
        st.plotly_chart(fig_proj, use_container_width=True)

        st.markdown("#### Daily Cost Breakdown")
        if sel_model in pricing:
            p = pricing[sel_model]
            daily_input_cost = avg_prompt_tokens * daily_requests / 1_000_000 * p.input_per_1m_tokens
            daily_output_cost = avg_completion_tokens * daily_requests / 1_000_000 * p.output_per_1m_tokens
            daily_total = daily_input_cost + daily_output_cost

            fig_breakdown = go.Figure(go.Pie(
                labels=["Input Tokens", "Output Tokens"],
                values=[daily_input_cost, daily_output_cost],
                marker_colors=[NEBIUS_BLUE, NEBIUS_SUCCESS],
                hole=0.4,
                textinfo="label+percent+value",
                texttemplate="%{label}<br>$%{value:.4f}",
            ))
            fig_breakdown.update_layout(
                **PLOTLY_THEME, title=f"Daily Cost Breakdown (${daily_total:.4f}/day)",
                height=320, margin=dict(l=20,r=20,t=50,b=20),
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)

# ─── Tab 3: Model Price Comparison ───────────────────────────────────────────
with tab_model_compare:
    st.markdown("#### Nebius Model Pricing Comparison")

    if not pricing:
        st.warning("No pricing data loaded. Check config/models.yaml.")
    else:
        price_rows = []
        for model_id, p in pricing.items():
            if model_id == "custom":
                continue
            price_rows.append({
                "Model": model_id.split("/")[-1],
                "Model ID": model_id,
                "Input ($/1M)": p.input_per_1m_tokens,
                "Output ($/1M)": p.output_per_1m_tokens,
                "Blended ($/1M)": (p.input_per_1m_tokens + p.output_per_1m_tokens) / 2,
                "Category": (
                    "Economy" if p.output_per_1m_tokens < 0.15 else
                    "Standard" if p.output_per_1m_tokens < 0.5 else
                    "Premium" if p.output_per_1m_tokens < 2 else "Flagship"
                ),
            })

        df_prices = pd.DataFrame(price_rows).sort_values("Blended ($/1M)")
        st.dataframe(df_prices, use_container_width=True, hide_index=True)

        fig_prices = px.bar(
            df_prices,
            x="Model",
            y=["Input ($/1M)", "Output ($/1M)"],
            barmode="group",
            title="Model Pricing: Input vs Output Tokens ($/1M)",
            color_discrete_sequence=[NEBIUS_BLUE, NEBIUS_SUCCESS],
        )
        fig_prices.update_layout(
            **PLOTLY_THEME, height=420,
            xaxis_title="", yaxis_title="Price per 1M Tokens (USD)",
            margin=dict(l=40,r=20,t=40,b=120),
            xaxis_tickangle=-35,
            legend_title="Token Type",
        )
        st.plotly_chart(fig_prices, use_container_width=True)

        avg_prompt = 150
        avg_completion = 256
        per_million_rows = []
        for model_id, p in pricing.items():
            if model_id == "custom":
                continue
            cost_per_1k = (
                avg_prompt / 1_000_000 * p.input_per_1m_tokens +
                avg_completion / 1_000_000 * p.output_per_1m_tokens
            ) * 1000
            per_million_rows.append({
                "Model": model_id.split("/")[-1],
                "Cost per 1K Requests ($)": round(cost_per_1k, 4),
            })

        df_per1k = pd.DataFrame(per_million_rows).sort_values("Cost per 1K Requests ($)")
        fig_1k = px.bar(
            df_per1k, x="Model", y="Cost per 1K Requests ($)",
            title=f"Cost per 1,000 Requests (p={avg_prompt} in, c={avg_completion} out tokens)",
            color="Cost per 1K Requests ($)",
            color_continuous_scale=[[0, NEBIUS_SUCCESS], [0.5, NEBIUS_WARNING], [1, NEBIUS_ERROR]],
            text_auto=".4f",
        )
        fig_1k.update_traces(textposition="outside")
        fig_1k.update_layout(
            **PLOTLY_THEME, height=420,
            xaxis_title="", yaxis_title="USD per 1K Requests",
            margin=dict(l=40,r=20,t=40,b=120),
            xaxis_tickangle=-35,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_1k, use_container_width=True)

        st.markdown(
            f"""<div class="info-card">
            <strong>Pricing assumptions:</strong> {avg_prompt} input tokens + {avg_completion} output tokens per request.<br>
            Nebius pricing is approximate. Always verify with the
            <a href="https://nebius.com/pricing" target="_blank" style="color:{NEBIUS_BLUE}">official pricing page</a>.
            </div>""",
            unsafe_allow_html=True,
        )
