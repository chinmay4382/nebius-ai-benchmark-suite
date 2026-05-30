"""Shared Pydantic models for NebiusBench."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Enums ────────────────────────────────────────────────────────────────────


class BenchmarkType(str, Enum):
    ENDPOINT = "endpoint"
    JOBS = "jobs"


class BenchmarkStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PromptDataset(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    CODE = "code"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


# ─── Configuration Models ─────────────────────────────────────────────────────


class BenchmarkConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    endpoint_url: str = Field(..., description="OpenAI-compatible API base URL")
    api_key: str = Field(..., description="API key for authentication")
    model: str = Field(..., description="Model identifier")
    concurrency: int = Field(default=10, ge=1, le=200)
    request_count: int = Field(default=100, ge=1, le=10000)
    max_tokens: int = Field(default=256, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    streaming: bool = Field(default=False)
    prompt_dataset: PromptDataset = Field(default=PromptDataset.MEDIUM)
    custom_prompt: Optional[str] = Field(default=None)
    timeout_seconds: float = Field(default=120.0, ge=1.0)
    warmup_requests: int = Field(default=3, ge=0, le=20)

    @field_validator("endpoint_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("endpoint_url must start with http:// or https://")
        return v


class JobBenchmarkConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_key: str
    project_id: str
    folder_id: str
    base_url: str = "https://api.nebius.cloud/v1"
    job_count: int = Field(default=5, ge=1, le=50)
    timeout_seconds: float = Field(default=600.0)


# ─── Per-Request Metrics ──────────────────────────────────────────────────────


class RequestMetric(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_num: int = 0
    start_time: float = 0.0
    first_token_time: Optional[float] = None
    end_time: float = 0.0
    ttft_ms: Optional[float] = None
    inter_token_latency_ms: Optional[float] = None
    total_latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0.0
    status_code: int = 200
    error: Optional[str] = None
    is_success: bool = True
    concurrency_level: int = 1


# ─── Aggregated Statistics ────────────────────────────────────────────────────


class PercentileStats(BaseModel):
    p50: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    mean: float = 0.0
    min: float = 0.0
    max: float = 0.0
    std: float = 0.0


class EndpointBenchmarkSummary(BaseModel):
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    error_rate: float = 0.0
    success_rate: float = 0.0

    ttft: PercentileStats = Field(default_factory=PercentileStats)
    latency: PercentileStats = Field(default_factory=PercentileStats)
    inter_token_latency: PercentileStats = Field(default_factory=PercentileStats)

    throughput_rps: float = 0.0
    tokens_per_second: float = 0.0
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    total_tokens_total: int = 0

    duration_seconds: float = 0.0
    concurrency_level: int = 1

    cold_start_ms: Optional[float] = None
    warm_start_ms: Optional[float] = None

    raw_metrics: list[RequestMetric] = Field(default_factory=list)


class ConcurrencyResult(BaseModel):
    concurrency_level: int
    summary: EndpointBenchmarkSummary


class JobMetric(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creation_time_ms: float = 0.0
    queue_delay_ms: float = 0.0
    startup_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    completion_time_ms: float = 0.0
    total_time_ms: float = 0.0
    status: str = "completed"
    error: Optional[str] = None


class JobBenchmarkSummary(BaseModel):
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    creation_time: PercentileStats = Field(default_factory=PercentileStats)
    queue_delay: PercentileStats = Field(default_factory=PercentileStats)
    startup_time: PercentileStats = Field(default_factory=PercentileStats)
    execution_time: PercentileStats = Field(default_factory=PercentileStats)
    total_time: PercentileStats = Field(default_factory=PercentileStats)
    raw_metrics: list[JobMetric] = Field(default_factory=list)


# ─── Cost Models ──────────────────────────────────────────────────────────────


class ModelPricing(BaseModel):
    model_id: str
    display_name: str
    input_per_1m_tokens: float
    output_per_1m_tokens: float


class CostEstimate(BaseModel):
    model_id: str
    total_input_tokens: int
    total_output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    cost_per_request_usd: float
    cost_per_1m_tokens_usd: float
    projected_monthly_cost_usd: float
    projected_monthly_cost_at_rps: dict[str, float] = Field(default_factory=dict)


# ─── Run Record ───────────────────────────────────────────────────────────────


class BenchmarkRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    benchmark_type: BenchmarkType
    config: BenchmarkConfig | JobBenchmarkConfig
    status: BenchmarkStatus = BenchmarkStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    endpoint_summary: Optional[EndpointBenchmarkSummary] = None
    job_summary: Optional[JobBenchmarkSummary] = None
    concurrency_results: list[ConcurrencyResult] = Field(default_factory=list)
    cost_estimate: Optional[CostEstimate] = None
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    error_message: Optional[str] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# ─── Report Models ────────────────────────────────────────────────────────────


class BenchmarkReport(BaseModel):
    run_id: str
    run_name: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    format: ReportFormat
    content: str
    file_path: Optional[str] = None


# ─── UI Helper ────────────────────────────────────────────────────────────────


class LiveUpdate(BaseModel):
    """Emitted during benchmark execution for real-time UI updates."""
    timestamp: float
    request_num: int
    total_requests: int
    latest_metric: Optional[RequestMetric] = None
    running_summary: Optional[dict[str, Any]] = None
    message: str = ""
