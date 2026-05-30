"""About Nebius — Serverless AI Builders Challenge."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
from app.ui_utils import (
    NEBIUS_BLUE, NEBIUS_CARD, NEBIUS_BORDER, NEBIUS_MUTED, NEBIUS_TEXT,
    NEBIUS_SUCCESS, NEBIUS_NAVY, NEBIUS_WARNING,
    apply_global_styles,
)

st.set_page_config(
    page_title="About Nebius | NebiusBench",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_styles()

# ── Hero with real Nebius logo + challenge header image ───────────────────────
st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, {NEBIUS_NAVY} 0%, #0d1929 100%);
        border: 1px solid {NEBIUS_BORDER};
        border-radius: 16px;
        padding: 40px 48px;
        margin-bottom: 28px;
        text-align: center;
    ">
        <img src="https://nebius.com/logo.svg"
             alt="Nebius AI"
             style="height: 48px; margin-bottom: 24px; filter: brightness(0) invert(1);" />
        <h1 style="color: {NEBIUS_TEXT}; font-size: 2.2rem; margin: 0 0 12px 0;">
            Serverless AI <span style="color: {NEBIUS_BLUE};">Builders Challenge</span>
        </h1>
        <p style="color: {NEBIUS_MUTED}; font-size: 1.05rem; max-width: 620px; margin: 0 auto; line-height: 1.75;">
            Build something real. Document it clearly. Share it openly.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Challenge header image ─────────────────────────────────────────────────────
st.markdown(
    """
    <div style="border-radius: 12px; overflow: hidden; margin-bottom: 28px;">
        <img src="https://assets.nebius.com/assets/392a2a84-b150-411b-b4ef-bd7b490378e3/header.jpg"
             alt="Nebius Serverless AI Builders Challenge"
             style="width: 100%; display: block; border-radius: 12px;" />
    </div>
    """,
    unsafe_allow_html=True,
)

# ── What is the challenge ──────────────────────────────────────────────────────
st.markdown(
    f"<h2 style='color:{NEBIUS_BLUE}; margin-bottom:16px;'>What is this challenge?</h2>",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div style="
        background: {NEBIUS_CARD};
        border: 1px solid {NEBIUS_BORDER};
        border-radius: 12px;
        padding: 28px 32px;
        margin-bottom: 28px;
        line-height: 1.8;
    ">
        <p style="color:{NEBIUS_TEXT}; font-size:1rem; margin: 0 0 14px 0;">
            The <strong style="color:{NEBIUS_BLUE};">Nebius Serverless AI Builders Challenge</strong>
            invites the ML and AI community to do one thing: build something real, document it clearly,
            and share it openly.
        </p>
        <p style="color:{NEBIUS_MUTED}; font-size:0.95rem; margin:0;">
            Top submissions become <strong style="color:{NEBIUS_TEXT};">reference examples for
            practitioners globally</strong> — they stay valuable long after the competition ends.
            The goal is not just winning, it's contributing something genuinely useful to the community.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── What is Nebius Serverless AI ──────────────────────────────────────────────
st.markdown(
    f"<h2 style='color:{NEBIUS_BLUE}; margin-bottom:16px;'>What is Nebius Serverless AI?</h2>",
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

cards = [
    ("⚡", "No Cluster Management",
     "GPU and CPU accelerated compute — without managing clusters or long-running infrastructure."),
    ("💳", "Pay Per Use",
     "Run a job, serve a model, pay only for what you use. No idle costs, no upfront commitment."),
    ("🌍", "Built for the Community",
     "Winning submissions become reference examples that practitioners worldwide learn from."),
]

for col, (icon, title, body) in zip([col1, col2, col3], cards):
    col.markdown(
        f"""
        <div style="
            background: {NEBIUS_CARD};
            border: 1px solid {NEBIUS_BORDER};
            border-radius: 12px;
            padding: 24px 20px;
            min-height: 150px;
        ">
            <div style="font-size: 2rem; margin-bottom: 10px;">{icon}</div>
            <div style="color:{NEBIUS_TEXT}; font-weight:600; font-size:0.95rem; margin-bottom:8px;">{title}</div>
            <div style="color:{NEBIUS_MUTED}; font-size:0.88rem; line-height:1.65;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Our submission ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="
        background: linear-gradient(135deg, #0d1f0d 0%, {NEBIUS_CARD} 100%);
        border: 1px solid {NEBIUS_SUCCESS}55;
        border-radius: 16px;
        padding: 36px 40px;
        margin-bottom: 28px;
    ">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
            <span style="font-size:2rem;">🏆</span>
            <h2 style="color:{NEBIUS_SUCCESS}; margin:0; font-size:1.4rem;">Our Submission — NebiusBench</h2>
        </div>
        <p style="color:{NEBIUS_TEXT}; font-size:0.97rem; line-height:1.8; margin: 0 0 12px 0;">
            <strong style="color:{NEBIUS_BLUE};">NebiusBench</strong> is a production-grade
            benchmarking and observability platform built specifically for Nebius Serverless AI
            Endpoints and AI Jobs.
        </p>
        <p style="color:{NEBIUS_MUTED}; font-size:0.92rem; line-height:1.8; margin:0;">
            It measures TTFT, inter-token latency, throughput, and concurrency scaling — then
            visualises everything in a Streamlit dashboard with real-time charts, run comparison,
            cost analysis, and downloadable reports. Built to be a reference tool for anyone
            evaluating Nebius AI performance.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── What we measure ───────────────────────────────────────────────────────────
st.markdown(
    f"<h2 style='color:{NEBIUS_BLUE}; margin-bottom:16px;'>What NebiusBench measures</h2>",
    unsafe_allow_html=True,
)

metrics = [
    (NEBIUS_BLUE,    "TTFT",               "Time-to-First-Token via Server-Sent Events"),
    (NEBIUS_SUCCESS, "Throughput",          "Sustained requests/sec and tokens/sec under load"),
    (NEBIUS_WARNING, "Concurrency Scaling", "Latency curve across 1 → 100 parallel requests"),
    ("#A78BFA",      "Cold Start",          "First-request latency after endpoint inactivity"),
    ("#F472B6",      "Cost Analysis",       "Per-model pricing and usage projections"),
]

cols = st.columns(len(metrics))
for col, (color, label, desc) in zip(cols, metrics):
    col.markdown(
        f"""
        <div style="
            background: {NEBIUS_CARD};
            border: 1px solid {NEBIUS_BORDER};
            border-top: 3px solid {color};
            border-radius: 10px;
            padding: 16px 14px;
            text-align: center;
        ">
            <div style="color:{color}; font-weight:700; font-size:0.9rem; margin-bottom:6px;">{label}</div>
            <div style="color:{NEBIUS_MUTED}; font-size:0.78rem; line-height:1.5;">{desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Links ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="
        background: {NEBIUS_CARD};
        border: 1px solid {NEBIUS_BORDER};
        border-radius: 12px;
        padding: 20px 28px;
    ">
        <span style="color:{NEBIUS_MUTED}; font-size:0.88rem;">Useful links →&nbsp;&nbsp;</span>
        <a href="https://nebius.com/serverless-ai-builders-challenge" target="_blank"
           style="color:{NEBIUS_BLUE}; text-decoration:none; font-size:0.88rem; margin-right:20px;">🏆 The Challenge</a>
        <a href="https://nebius.com" target="_blank"
           style="color:{NEBIUS_BLUE}; text-decoration:none; font-size:0.88rem; margin-right:20px;">🌐 nebius.com</a>
        <a href="https://nebius.com/docs" target="_blank"
           style="color:{NEBIUS_BLUE}; text-decoration:none; font-size:0.88rem; margin-right:20px;">📖 Docs</a>
        <a href="https://github.com/chinmay4382/nebius-ai-benchmark-suite" target="_blank"
           style="color:{NEBIUS_BLUE}; text-decoration:none; font-size:0.88rem;">💻 GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
