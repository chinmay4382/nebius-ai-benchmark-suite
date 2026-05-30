"""Job execution timing benchmark."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Optional

import httpx

from benchmark.models import JobBenchmarkConfig, JobMetric

logger = logging.getLogger(__name__)


class JobExecutionBenchmark:
    """
    Benchmarks execution time of AI Jobs on Nebius.
    Submits jobs with a standard workload and measures how long they run.
    """

    def __init__(self, config: JobBenchmarkConfig, workload_script: Optional[str] = None) -> None:
        self.config = config
        self.workload_script = workload_script or self._default_workload()

    def _default_workload(self) -> str:
        return (
            "import time, math; "
            "[math.sqrt(i) for i in range(1_000_000)]; "
            "print('Execution complete')"
        )

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            timeout=httpx.Timeout(self.config.timeout_seconds),
        )

    async def _run_job(self, client: httpx.AsyncClient, job_num: int) -> JobMetric:
        metric = JobMetric(job_id=str(uuid.uuid4()))

        try:
            t0 = time.perf_counter()
            response = await client.post(
                f"/folders/{self.config.folder_id}/jobs",
                json={
                    "name": f"nebiusbench-exec-{job_num}",
                    "project_id": self.config.project_id,
                    "resources": {"platform": "cpu-d3", "preset": "2vcpu-8gb"},
                    "container": {
                        "image": "cr.nebius.cloud/nebius/python:3.12-slim",
                        "command": ["python", "-c", self.workload_script],
                    },
                    "labels": {"created_by": "nebiusbench", "type": "execution-benchmark"},
                },
            )
            metric.creation_time_ms = (time.perf_counter() - t0) * 1000

            if response.status_code not in (200, 201, 202):
                metric.status = "failed"
                return metric

            job_id = response.json().get("id", metric.job_id)
            metric.job_id = job_id

            exec_start = time.perf_counter()
            while time.perf_counter() - exec_start < self.config.timeout_seconds:
                resp = await client.get(f"/folders/{self.config.folder_id}/jobs/{job_id}")
                if resp.status_code == 200:
                    status = resp.json().get("status", "")
                    if status == "COMPLETED":
                        metric.execution_time_ms = (time.perf_counter() - exec_start) * 1000
                        metric.total_time_ms = metric.creation_time_ms + metric.execution_time_ms
                        metric.status = "completed"
                        break
                    if status in ("FAILED", "CANCELLED"):
                        metric.status = "failed"
                        break
                await asyncio.sleep(3)
            else:
                metric.status = "timeout"

        except Exception as exc:
            metric.status = "failed"
            metric.error = str(exc)

        return metric

    async def run(self) -> list[JobMetric]:
        metrics: list[JobMetric] = []
        async with self._build_client() as client:
            for i in range(self.config.job_count):
                m = await self._run_job(client, i)
                metrics.append(m)
                logger.info("Execution job %d: %s (%.1fs)", i + 1, m.status, m.total_time_ms / 1000)
        return metrics

    def run_sync(self) -> list[JobMetric]:
        return asyncio.run(self.run())
