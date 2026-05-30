"""Job completion verification and timing."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

import httpx

from benchmark.auth import get_iam_token
from benchmark.models import JobBenchmarkConfig, JobMetric

logger = logging.getLogger(__name__)


class JobCompletionBenchmark:
    """
    Measures end-to-end job lifecycle time including cleanup.
    Tracks creation → queue → running → completed → deleted.
    """

    def __init__(self, config: JobBenchmarkConfig) -> None:
        self.config = config

    async def _build_client(self) -> httpx.AsyncClient:
        token = await get_iam_token()
        return httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(self.config.timeout_seconds),
        )

    async def _full_lifecycle(self, client: httpx.AsyncClient, idx: int) -> JobMetric:
        metric = JobMetric(job_id=str(uuid.uuid4()))
        t_start = time.perf_counter()

        try:
            t0 = time.perf_counter()
            resp = await client.post(
                f"/folders/{self.config.folder_id}/jobs",
                json={
                    "name": f"nebiusbench-lifecycle-{idx}",
                    "project_id": self.config.project_id,
                    "resources": {"platform": "cpu-d3", "preset": "2vcpu-8gb"},
                    "container": {
                        "image": "cr.nebius.cloud/nebius/python:3.12-slim",
                        "command": ["python", "-c", "print('lifecycle check')"],
                    },
                    "labels": {"created_by": "nebiusbench", "type": "lifecycle"},
                },
            )
            metric.creation_time_ms = (time.perf_counter() - t0) * 1000

            if resp.status_code not in (200, 201, 202):
                metric.status = "failed"
                return metric

            job_id = resp.json().get("id", metric.job_id)
            metric.job_id = job_id

            q_start = time.perf_counter()
            prev_status = ""
            while time.perf_counter() - t_start < self.config.timeout_seconds:
                r = await client.get(f"/folders/{self.config.folder_id}/jobs/{job_id}")
                if r.status_code != 200:
                    await asyncio.sleep(2)
                    continue

                status = r.json().get("status", "")
                if status != prev_status:
                    logger.debug("Job %s: %s → %s", job_id, prev_status, status)
                    prev_status = status

                if status == "RUNNING" and metric.queue_delay_ms == 0:
                    metric.queue_delay_ms = (time.perf_counter() - q_start) * 1000
                    metric.startup_time_ms = metric.queue_delay_ms

                if status == "COMPLETED":
                    metric.completion_time_ms = (time.perf_counter() - t_start) * 1000
                    metric.execution_time_ms = metric.completion_time_ms - metric.creation_time_ms - metric.queue_delay_ms
                    metric.total_time_ms = metric.completion_time_ms
                    metric.status = "completed"
                    break

                if status in ("FAILED", "CANCELLED"):
                    metric.status = status.lower()
                    break

                await asyncio.sleep(2)
            else:
                metric.status = "timeout"

        except Exception as exc:
            metric.status = "failed"
            metric.error = str(exc)
            logger.exception("Job lifecycle failed: %s", exc)

        return metric

    async def run(self) -> list[JobMetric]:
        metrics: list[JobMetric] = []
        async with await self._build_client() as client:
            for i in range(self.config.job_count):
                m = await self._full_lifecycle(client, i)
                metrics.append(m)
                logger.info(
                    "Lifecycle job %d/%d: %s (total %.1fs)",
                    i + 1, self.config.job_count, m.status, m.total_time_ms / 1000
                )
        return metrics

    def run_sync(self) -> list[JobMetric]:
        return asyncio.run(self.run())
