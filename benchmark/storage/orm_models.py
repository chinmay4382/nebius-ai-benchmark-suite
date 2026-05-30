"""SQLAlchemy ORM models for NebiusBench."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benchmark.storage.database import Base


class BenchmarkRunORM(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    benchmark_type: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    concurrency: Mapped[int] = mapped_column(Integer, default=1)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    results: Mapped[list[BenchmarkResultORM]] = relationship(
        "BenchmarkResultORM", back_populates="run", cascade="all, delete-orphan"
    )
    reports: Mapped[list[ReportORM]] = relationship(
        "ReportORM", back_populates="run", cascade="all, delete-orphan"
    )

    @property
    def config(self) -> dict[str, Any]:
        return json.loads(self.config_json)

    @config.setter
    def config(self, value: dict[str, Any]) -> None:
        self.config_json = json.dumps(value)

    @property
    def tags(self) -> list[str]:
        return json.loads(self.tags_json)

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self.tags_json = json.dumps(value)

    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class BenchmarkResultORM(Base):
    __tablename__ = "benchmark_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("benchmark_runs.id"), nullable=False)
    result_type: Mapped[str] = mapped_column(String(64), default="endpoint")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    raw_data_json: Mapped[str] = mapped_column(Text, default="[]")
    concurrency_level: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[BenchmarkRunORM] = relationship("BenchmarkRunORM", back_populates="results")

    @property
    def metrics(self) -> dict[str, Any]:
        return json.loads(self.metrics_json)

    @metrics.setter
    def metrics(self, value: dict[str, Any]) -> None:
        self.metrics_json = json.dumps(value)

    @property
    def raw_data(self) -> list[Any]:
        return json.loads(self.raw_data_json)

    @raw_data.setter
    def raw_data(self, value: list[Any]) -> None:
        self.raw_data_json = json.dumps(value)


class ReportORM(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("benchmark_runs.id"), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped[BenchmarkRunORM] = relationship("BenchmarkRunORM", back_populates="reports")
