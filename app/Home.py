"""NebiusBench — Home Page."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.ui_utils import (
    NEBIUS_BLUE, NEBIUS_CARD, NEBIUS_BORDER, NEBIUS_MUTED, NEBIUS_TEXT,
    NEBIUS_SUCCESS, NEBIUS_WARNING, NEBIUS_NAVY,
    apply_global_styles, page_header,
)
from benchmark.storage.database import init_db
from benchmark.storage.repository import BenchmarkRepository
from benchmark.storage.database import get_session_factory

st.set_page_config(
    page_title="NebiusBench",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://nebius.com/docs",
        "Report a bug": "https://github.com/nebiusbench/nebiusbench/issues",
        "About": "NebiusBench — Benchmarking platform for Nebius AI",
    },
)

init_db()
apply_global_styles()


def _get_recent_runs() -> list[dict]:
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            return repo.get_run_summary_list()[:5]
    except Exception:
        return []


def render_hero() -> None:
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {NEBIUS_NAVY} 0%, #0d1929 100%);
            border: 1px solid {NEBIUS_BORDER};
            border-radius: 16px;
            padding: 40px 48px;
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        ">
            <div style="
                position: absolute; top: -40px; right: -40px;
                width: 200px; height: 200px;
                background: radial-gradient(circle, rgba(0,163,255,0.12) 0%, transparent 70%);
            "></div>
            <div style="font-size: 0.8rem; color: {NEBIUS_BLUE}; font-weight: 600;
                        text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 12px">
                ⚡ Production-Grade AI Infrastructure Benchmarking
            </div>
            <h1 style="font-size: 2.4rem; font-weight: 800; color: {NEBIUS_TEXT}; margin: 0 0 12px">
                NebiusBench
            </h1>
            <p style="font-size: 1.05rem; color: {NEBIUS_MUTED}; max-width: 640px; margin: 0 0 24px; line-height: 1.7">
                Benchmark <strong style="color:{NEBIUS_TEXT}">Nebius Serverless AI Endpoints</strong>
                and <strong style="color:{NEBIUS_TEXT}">AI Jobs</strong> with real-time metrics,
                concurrency sweeps, cost analysis, and downloadable reports.
            </p>
            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                <span style="background:rgba(0,163,255,0.1);border:1px solid rgba(0,163,255,0.3);
                             border-radius:20px;padding:4px 14px;font-size:0.8rem;color:{NEBIUS_BLUE}">
                    OpenAI-Compatible API
                </span>
                <span style="background:rgba(0,200,150,0.1);border:1px solid rgba(0,200,150,0.3);
                             border-radius:20px;padding:4px 14px;font-size:0.8rem;color:{NEBIUS_SUCCESS}">
                    Async Concurrency Testing
                </span>
                <span style="background:rgba(255,181,71,0.1);border:1px solid rgba(255,181,71,0.3);
                             border-radius:20px;padding:4px 14px;font-size:0.8rem;color:{NEBIUS_WARNING}">
                    Cost Estimation
                </span>
                <span style="background:rgba(167,139,250,0.1);border:1px solid rgba(167,139,250,0.3);
                             border-radius:20px;padding:4px 14px;font-size:0.8rem;color:#A78BFA">
                    SQLite Persistence
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_cards() -> None:
    cols = st.columns(3)
    features = [
        {
            "icon": "🚀",
            "title": "Endpoint Benchmarking",
            "items": ["TTFT & Inter-Token Latency", "Throughput (req/s, tok/s)", "Concurrency sweep [1→100]",
                      "Cold & Warm start", "Streaming & non-streaming", "p50 / p90 / p95 / p99"],
            "color": NEBIUS_BLUE,
        },
        {
            "icon": "🏭",
            "title": "Jobs Benchmarking",
            "items": ["Job creation time", "Queue delay measurement", "Container startup timing",
                      "Execution time", "End-to-end lifecycle", "Error rate & retries"],
            "color": NEBIUS_SUCCESS,
        },
        {
            "icon": "📊",
            "title": "Visualization & Reports",
            "items": ["Real-time Plotly charts", "Run comparison tables", "Cost projections",
                      "Markdown / JSON / HTML export", "SQLite result history", "Downloadable reports"],
            "color": NEBIUS_WARNING,
        },
    ]
    for col, feat in zip(cols, features):
        with col:
            items_html = "".join(
                f'<li style="color:{NEBIUS_MUTED};margin:4px 0;font-size:0.87rem">'
                f'<span style="color:{feat["color"]}">✓</span> {item}</li>'
                for item in feat["items"]
            )
            st.markdown(
                f"""<div style="background:{NEBIUS_CARD};border:1px solid {NEBIUS_BORDER};
                              border-top:3px solid {feat['color']};border-radius:12px;
                              padding:24px;height:100%">
                    <div style="font-size:1.8rem;margin-bottom:10px">{feat['icon']}</div>
                    <h3 style="color:{NEBIUS_TEXT};font-size:1rem;margin:0 0 12px;font-weight:700">
                        {feat['title']}
                    </h3>
                    <ul style="list-style:none;margin:0;padding:0">{items_html}</ul>
                </div>""",
                unsafe_allow_html=True,
            )


def render_architecture() -> None:
    st.markdown("### Architecture")
    st.markdown(
        """
```mermaid
graph TD
    A[Streamlit UI] --> B[BenchmarkRunner]
    B --> C[Endpoint Benchmarks]
    B --> D[Jobs Benchmarks]
    C --> C1[TTFT]
    C --> C2[Throughput]
    C --> C3[Concurrency Sweep]
    C --> C4[Cold/Warm Start]
    C --> C5[Streaming]
    D --> D1[Job Startup]
    D --> D2[Job Execution]
    D --> D3[Job Completion]
    B --> E[MetricsCollector]
    E --> F[MetricsAnalyzer]
    F --> G[SQLite DB]
    F --> H[MetricsReporter]
    H --> I[Markdown]
    H --> J[JSON]
    H --> K[HTML]
```
        """
    )


def render_metrics_definitions() -> None:
    st.markdown("### Key Metrics")
    col1, col2 = st.columns(2)
    with col1:
        metrics = [
            ("TTFT", "Time from request submission to first token received (streaming)"),
            ("ITL", "Average delay between consecutive generated tokens"),
            ("Throughput", "Sustained requests/sec and tokens/sec under load"),
            ("Concurrency Scaling", "How latency and RPS change as parallelism increases"),
            ("Error Rate", "Fraction of requests returning non-2xx responses"),
        ]
        for name, desc in metrics:
            st.markdown(
                f"""<div class="info-card" style="margin:6px 0">
                <strong style="color:{NEBIUS_BLUE}">{name}</strong><br>
                <span style="color:{NEBIUS_MUTED};font-size:0.85rem">{desc}</span>
                </div>""",
                unsafe_allow_html=True,
            )
    with col2:
        metrics2 = [
            ("Cold Start", "First-request latency after a period of endpoint inactivity"),
            ("Warm Start", "p50 latency for requests when endpoint is fully warm"),
            ("Cost/1M Tokens", "Estimated cost per one million tokens based on Nebius pricing"),
            ("p99 Latency", "99th-percentile latency — tail latency seen by 1 in 100 requests"),
            ("Job Queue Delay", "Time from job submission to container actually running"),
        ]
        for name, desc in metrics2:
            st.markdown(
                f"""<div class="info-card" style="margin:6px 0">
                <strong style="color:{NEBIUS_SUCCESS}">{name}</strong><br>
                <span style="color:{NEBIUS_MUTED};font-size:0.85rem">{desc}</span>
                </div>""",
                unsafe_allow_html=True,
            )


def render_recent_runs(runs: list[dict]) -> None:
    st.markdown("### Recent Benchmark Runs")
    if not runs:
        st.markdown(
            f"""<div style="background:{NEBIUS_CARD};border:1px dashed {NEBIUS_BORDER};
                          border-radius:10px;padding:32px;text-align:center;color:{NEBIUS_MUTED}">
                No benchmark runs yet. Head to <strong>Run Benchmark</strong> to get started!
            </div>""",
            unsafe_allow_html=True,
        )
        return

    import pandas as pd
    df = pd.DataFrame(runs)
    display_cols = {
        "name": "Run Name", "model": "Model", "status": "Status",
        "concurrency": "Concurrency", "ttft_p50": "TTFT p50 (ms)",
        "throughput_rps": "Throughput (rps)", "error_rate": "Error Rate",
        "created_at": "Created",
    }
    df_display = df[[c for c in display_cols if c in df.columns]].rename(columns=display_cols)
    if "Error Rate" in df_display.columns:
        df_display["Error Rate"] = df_display["Error Rate"].apply(
            lambda x: f"{x*100:.1f}%" if x is not None else "—"
        )
    if "TTFT p50 (ms)" in df_display.columns:
        df_display["TTFT p50 (ms)"] = df_display["TTFT p50 (ms)"].apply(
            lambda x: f"{x:.1f}" if x is not None else "—"
        )
    if "Throughput (rps)" in df_display.columns:
        df_display["Throughput (rps)"] = df_display["Throughput (rps)"].apply(
            lambda x: f"{x:.2f}" if x is not None else "—"
        )
    st.dataframe(df_display, use_container_width=True, hide_index=True)


def render_quickstart() -> None:
    st.markdown("### Quick Start")
    tab1, tab2, tab3 = st.tabs(["Local Setup", "Docker", "CLI"])
    with tab1:
        st.code(
            """# 1. Clone and install
git clone https://github.com/nebiusbench/nebiusbench
cd nebiusbench
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your NEBIUS_API_KEY

# 3. Launch
streamlit run app/Home.py""",
            language="bash",
        )
    with tab2:
        st.code(
            """# Build and run with Docker Compose
cp .env.example .env
# Edit .env with your NEBIUS_API_KEY

docker compose up --build

# Open http://localhost:8501""",
            language="bash",
        )
    with tab3:
        st.code(
            """# Run a benchmark from the CLI
python -m benchmark.runner \\
  --endpoint https://api.studio.nebius.com/v1 \\
  --model meta-llama/Meta-Llama-3.1-8B-Instruct-fast \\
  --requests 100 \\
  --concurrency 10 \\
  --streaming""",
            language="bash",
        )


# ─── Main ─────────────────────────────────────────────────────────────────────

render_hero()

col_main, col_sidebar = st.columns([7, 3])

with col_main:
    render_feature_cards()
    st.markdown("---")
    render_recent_runs(_get_recent_runs())
    st.markdown("---")
    render_quickstart()
    st.markdown("---")
    render_architecture()

with col_sidebar:
    st.markdown("### Quick Stats")
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            all_runs = repo.get_run_summary_list()
            completed = [r for r in all_runs if r["status"] == "completed"]
            failed = [r for r in all_runs if r["status"] == "failed"]
    except Exception:
        all_runs = completed = failed = []

    col_a, col_b = st.columns(2)
    col_a.metric("Total Runs", len(all_runs))
    col_b.metric("Completed", len(completed))
    col_c, col_d = st.columns(2)
    col_c.metric("Failed", len(failed))
    col_d.metric("Success Rate", f"{(len(completed)/max(len(all_runs),1)*100):.0f}%")

    st.markdown("---")
    st.markdown("### Supported Models")
    models = [
        ("Llama 3.1 8B", "Fast, efficient"),
        ("Llama 3.1 70B", "High quality"),
        ("Llama 3.1 405B", "Flagship"),
        ("Mistral 7B", "Lightweight"),
        ("Mixtral 8x7B", "MoE balanced"),
        ("Qwen 2.5 72B", "Multilingual"),
        ("DeepSeek V3", "Reasoning"),
    ]
    for name, desc in models:
        st.markdown(
            f"<div style='padding:6px 0;border-bottom:1px solid {NEBIUS_BORDER}'>"
            f"<span style='color:{NEBIUS_TEXT};font-size:0.85rem;font-weight:600'>{name}</span>"
            f"<span style='color:{NEBIUS_MUTED};font-size:0.75rem;float:right'>{desc}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### Resources")
    st.markdown(
        f"""
- [Nebius AI Documentation](https://nebius.com/docs)
- [API Reference](https://nebius.com/docs/ai-studio/api)
- [GitHub Repository](https://github.com/nebiusbench/nebiusbench)
- [Report an Issue](https://github.com/nebiusbench/nebiusbench/issues)
        """
    )

st.markdown(
    f"""<div style="text-align:center;color:{NEBIUS_MUTED};font-size:0.75rem;
                    padding:24px 0 8px;border-top:1px solid {NEBIUS_BORDER};margin-top:24px">
        NebiusBench v0.1.0 · MIT License · Built for Nebius AI Hackathon
    </div>""",
    unsafe_allow_html=True,
)
