"""Job startup timing benchmark."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Optional

import httpx

from benchmark.auth import get_iam_token
from benchmark.models import JobBenchmarkConfig, JobMetric

logger = logging.getLogger(__name__)


class JobStartupBenchmark:
    """Measures Nebius AI Job creation and queue-to-running time."""

    def __init__(self, config: JobBenchmarkConfig) -> None:
        self.config = config

    async def _build_client(self) -> httpx.AsyncClient:
        token = await get_iam_token()
        return httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(self.config.timeout_seconds),
        )

    async def _create_job(self, client: httpx.AsyncClient, job_num: int) -> JobMetric:
        metric = JobMetric(job_id=str(uuid.uuid4()))
        create_start = time.perf_counter()

        try:
            payload = {
                "name": f"nebiusbench-job-{job_num}",
                "project_id": self.config.project_id,
                "resources": {"platform": "cpu-d3", "preset": "2vcpu-8gb"},
                "container": {
                    "image": "cr.nebius.cloud/nebius/python:3.12-slim",
                    "command": ["python", "-c", "print('NebiusBench job probe')"],
                },
                "labels": {"created_by": "nebiusbench", "type": "startup-probe"},
            }
            response = await client.post(
                f"/folders/{self.config.folder_id}/jobs",
                json=payload,
            )
            create_end = time.perf_counter()
            metric.creation_time_ms = (create_end - create_start) * 1000

            if response.status_code not in (200, 201, 202):
                metric.status = "failed"
                metric.error = f"Create failed: HTTP {response.status_code}"
                return metric

            job_data = response.json()
            job_id = job_data.get("id", metric.job_id)
            metric.job_id = job_id
            logger.info("Job %s created in %.1f ms", job_id, metric.creation_time_ms)

            queue_start = time.perf_counter()
            running = await self._wait_for_status(client, job_id, "RUNNING", timeout=300)
            metric.queue_delay_ms = (time.perf_counter() - queue_start) * 1000

            if not running:
                metric.status = "timeout"
                metric.error = "Job did not reach RUNNING within timeout"
                return metric

            startup_start = time.perf_counter()
            completed = await self._wait_for_status(client, job_id, "COMPLETED", timeout=600)
            metric.startup_time_ms = (time.perf_counter() - startup_start) * 1000

            metric.total_time_ms = metric.creation_time_ms + metric.queue_delay_ms + metric.startup_time_ms
            metric.status = "completed" if completed else "timeout"

        except Exception as exc:
            metric.status = "failed"
            metric.error = str(exc)
            logger.exception("Job creation failed: %s", exc)

        return metric

    async def _wait_for_status(
        self, client: httpx.AsyncClient, job_id: str, target_status: str, timeout: float = 300
    ) -> bool:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            try:
                resp = await client.get(f"/folders/{self.config.folder_id}/jobs/{job_id}")
                if resp.status_code == 200:
                    status = resp.json().get("status", "")
                    if status == target_status:
                        return True
                    if status in ("FAILED", "CANCELLED"):
                        return False
            except Exception:
                pass
            await asyncio.sleep(2)
        return False

    async def run(self) -> list[JobMetric]:
        metrics: list[JobMetric] = []
        async with await self._build_client() as client:
            for i in range(self.config.job_count):
                metric = await self._create_job(client, i)
                metrics.append(metric)
                logger.info(
                    "Job %d/%d: status=%s total=%.1fs",
                    i + 1, self.config.job_count,
                    metric.status, metric.total_time_ms / 1000,
                )
        return metrics

    def run_sync(self) -> list[JobMetric]:
        return asyncio.run(self.run())
