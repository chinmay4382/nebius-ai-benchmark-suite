# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="NebiusBench Contributors" \
      description="Production-grade benchmarking platform for Nebius AI Endpoints" \
      version="0.1.0"

# Non-root user for security
RUN groupadd -r nebiusbench && useradd -r -g nebiusbench -d /app -s /bin/bash nebiusbench

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/nebiusbench/.local

# Copy application code
COPY --chown=nebiusbench:nebiusbench . .

# Create required directories
RUN mkdir -p data reports/markdown reports/json reports/html \
    && chown -R nebiusbench:nebiusbench /app

USER nebiusbench

ENV PATH="/home/nebiusbench/.local/bin:${PATH}" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" \
    || exit 1

ENTRYPOINT ["python", "-m", "streamlit", "run", "app/Home.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true"]
