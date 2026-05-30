"""Repository pattern for clean DB access."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from benchmark.models import (
    BenchmarkRun,
    BenchmarkStatus,
    BenchmarkType,
    EndpointBenchmarkSummary,
    JobBenchmarkSummary,
    ConcurrencyResult,
    CostEstimate,
    BenchmarkReport,
    ReportFormat,
)
from benchmark.storage.orm_models import BenchmarkResultORM, BenchmarkRunORM, ReportORM


class BenchmarkRepository:
    """CRUD operations for benchmark data."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Runs ──────────────────────────────────────────────────────────────────

    def create_run(self, run: BenchmarkRun) -> BenchmarkRunORM:
        config_dict = run.config.model_dump()
        config_dict.pop("api_key", None)

        if isinstance(run.config, __import__("benchmark.models", fromlist=["BenchmarkConfig"]).BenchmarkConfig):
            model = run.config.model
            endpoint_url = run.config.endpoint_url
            concurrency = run.config.concurrency
            request_count = run.config.request_count
        else:
            model = ""
            endpoint_url = run.config.base_url
            concurrency = 1
            request_count = run.config.job_count

        orm = BenchmarkRunORM(
            id=run.id,
            name=run.name,
            benchmark_type=run.benchmark_type.value,
            model=model,
            endpoint_url=endpoint_url,
            concurrency=concurrency,
            request_count=request_count,
            status=run.status.value,
            config_json=json.dumps(config_dict),
            tags_json=json.dumps(run.tags),
            notes=run.notes,
            created_at=run.created_at,
        )
        self._db.add(orm)
        self._db.flush()
        return orm

    def get_run(self, run_id: str) -> Optional[BenchmarkRunORM]:
        return self._db.get(BenchmarkRunORM, run_id)

    def list_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        benchmark_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[BenchmarkRunORM]:
        q = self._db.query(BenchmarkRunORM).order_by(BenchmarkRunORM.created_at.desc())
        if benchmark_type:
            q = q.filter(BenchmarkRunORM.benchmark_type == benchmark_type)
        if status:
            q = q.filter(BenchmarkRunORM.status == status)
        return q.offset(offset).limit(limit).all()

    def update_run_status(
        self,
        run_id: str,
        status: BenchmarkStatus,
        error_message: Optional[str] = None,
    ) -> None:
        orm = self._db.get(BenchmarkRunORM, run_id)
        if orm is None:
            return
        orm.status = status.value
        if status == BenchmarkStatus.RUNNING and orm.started_at is None:
            orm.started_at = datetime.utcnow()
        if status in (BenchmarkStatus.COMPLETED, BenchmarkStatus.FAILED, BenchmarkStatus.CANCELLED):
            orm.completed_at = datetime.utcnow()
        if error_message:
            orm.error_message = error_message
        self._db.flush()

    def delete_run(self, run_id: str) -> bool:
        orm = self._db.get(BenchmarkRunORM, run_id)
        if orm is None:
            return False
        self._db.delete(orm)
        self._db.flush()
        return True

    # ── Results ───────────────────────────────────────────────────────────────

    def save_result(
        self,
        run_id: str,
        result_type: str,
        metrics: dict[str, Any],
        raw_data: list[Any],
        concurrency_level: int = 1,
    ) -> BenchmarkResultORM:
        orm = BenchmarkResultORM(
            id=str(uuid.uuid4()),
            run_id=run_id,
            result_type=result_type,
            metrics_json=json.dumps(metrics),
            raw_data_json=json.dumps(raw_data),
            concurrency_level=concurrency_level,
            created_at=datetime.utcnow(),
        )
        self._db.add(orm)
        self._db.flush()
        return orm

    def get_results(self, run_id: str) -> list[BenchmarkResultORM]:
        return (
            self._db.query(BenchmarkResultORM)
            .filter(BenchmarkResultORM.run_id == run_id)
            .order_by(BenchmarkResultORM.created_at)
            .all()
        )

    # ── Reports ───────────────────────────────────────────────────────────────

    def save_report(self, report: BenchmarkReport) -> ReportORM:
        orm = ReportORM(
            id=str(uuid.uuid4()),
            run_id=report.run_id,
            format=report.format.value,
            content=report.content,
            file_path=report.file_path,
            created_at=report.generated_at,
        )
        self._db.add(orm)
        self._db.flush()
        return orm

    def get_reports(self, run_id: str) -> list[ReportORM]:
        return (
            self._db.query(ReportORM)
            .filter(ReportORM.run_id == run_id)
            .order_by(ReportORM.created_at.desc())
            .all()
        )

    # ── Aggregated helpers ────────────────────────────────────────────────────

    def get_run_summary_list(self) -> list[dict[str, Any]]:
        """Return lightweight summaries for the runs table in the UI."""
        runs = self.list_runs(limit=500)
        summaries = []
        for r in runs:
            results = self.get_results(r.id)
            main = results[0] if results else None
            metrics = main.metrics if main else {}
            summaries.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "model": r.model,
                    "type": r.benchmark_type,
                    "status": r.status,
                    "concurrency": r.concurrency,
                    "request_count": r.request_count,
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
                    "duration_s": r.duration_seconds(),
                    "ttft_p50": metrics.get("ttft", {}).get("p50"),
                    "throughput_rps": metrics.get("throughput_rps"),
                    "error_rate": metrics.get("error_rate"),
                    "tokens_per_second": metrics.get("tokens_per_second"),
                }
            )
        return summaries
