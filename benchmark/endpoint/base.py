"""Base class for endpoint benchmarks with shared HTTP logic."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from benchmark.auth import get_iam_token
from benchmark.models import BenchmarkConfig, PromptDataset, RequestMetric

logger = logging.getLogger(__name__)

_PROMPTS = {
    PromptDataset.SHORT: "Explain machine learning in one sentence.",
    PromptDataset.MEDIUM: (
        "Write a detailed explanation of how transformer neural networks work, "
        "including the attention mechanism and positional encoding."
    ),
    PromptDataset.LONG: (
        "You are an AI researcher. Write a comprehensive technical report on the current state "
        "of large language models, covering training methodologies, scaling laws, emergent "
        "capabilities, alignment challenges, and deployment considerations."
    ),
    PromptDataset.CODE: (
        "Write a Python implementation of a binary search tree with insert, search, and delete "
        "operations. Include type hints and docstrings."
    ),
}


class BaseEndpointBenchmark:
    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _build_client_async(self) -> httpx.AsyncClient:
        token = await get_iam_token()
        return httpx.AsyncClient(
            base_url=self.config.endpoint_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.config.timeout_seconds),
            limits=httpx.Limits(max_connections=300, max_keepalive_connections=100),
        )

    def _build_client(self) -> httpx.AsyncClient:
        """Sync-compatible builder — token fetched inside async context."""
        import asyncio
        token = asyncio.get_event_loop().run_until_complete(get_iam_token()) \
            if asyncio.get_event_loop().is_running() else asyncio.run(get_iam_token())
        return httpx.AsyncClient(
            base_url=self.config.endpoint_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.config.timeout_seconds),
            limits=httpx.Limits(max_connections=300, max_keepalive_connections=100),
        )

    def _get_prompt(self) -> str:
        if self.config.prompt_dataset == PromptDataset.CUSTOM and self.config.custom_prompt:
            return self.config.custom_prompt
        return _PROMPTS.get(self.config.prompt_dataset, _PROMPTS[PromptDataset.MEDIUM])

    def _build_payload(self, stream: bool = False) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "messages": [{"role": "user", "content": self._get_prompt()}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": stream,
        }

    async def _request_non_streaming(
        self, client: httpx.AsyncClient, sequence_num: int = 0, concurrency: int = 1
    ) -> RequestMetric:
        metric = RequestMetric(
            request_id=str(uuid.uuid4()),
            sequence_num=sequence_num,
            concurrency_level=concurrency,
        )
        metric.start_time = time.perf_counter()

        try:
            response = await client.post(
                "/chat/completions",
                json=self._build_payload(stream=False),
            )
            metric.end_time = time.perf_counter()
            metric.status_code = response.status_code

            if response.status_code == 200:
                data = response.json()
                choice = data["choices"][0]
                usage = data.get("usage", {})

                metric.prompt_tokens = usage.get("prompt_tokens", 0)
                metric.completion_tokens = usage.get("completion_tokens", 0)
                metric.total_tokens = usage.get("total_tokens", 0)
                metric.total_latency_ms = (metric.end_time - metric.start_time) * 1000
                metric.is_success = True

                if metric.completion_tokens > 0 and metric.total_latency_ms > 0:
                    metric.tokens_per_second = metric.completion_tokens / (metric.total_latency_ms / 1000)
            else:
                metric.is_success = False
                metric.error = f"HTTP {response.status_code}: {response.text[:200]}"
                metric.total_latency_ms = (metric.end_time - metric.start_time) * 1000

        except httpx.TimeoutException as exc:
            metric.end_time = time.perf_counter()
            metric.is_success = False
            metric.error = f"Timeout: {exc}"
            metric.total_latency_ms = (metric.end_time - metric.start_time) * 1000
            metric.status_code = 408

        except Exception as exc:
            metric.end_time = time.perf_counter()
            metric.is_success = False
            metric.error = str(exc)
            metric.total_latency_ms = (metric.end_time - metric.start_time) * 1000
            metric.status_code = 0

        return metric

    async def _request_streaming(
        self, client: httpx.AsyncClient, sequence_num: int = 0, concurrency: int = 1
    ) -> RequestMetric:
        metric = RequestMetric(
            request_id=str(uuid.uuid4()),
            sequence_num=sequence_num,
            concurrency_level=concurrency,
        )
        metric.start_time = time.perf_counter()
        token_times: list[float] = []

        try:
            async with client.stream(
                "POST", "/chat/completions", json=self._build_payload(stream=True)
            ) as response:
                metric.status_code = response.status_code
                if response.status_code != 200:
                    metric.is_success = False
                    metric.error = f"HTTP {response.status_code}"
                    metric.end_time = time.perf_counter()
                    metric.total_latency_ms = (metric.end_time - metric.start_time) * 1000
                    return metric

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        import json
                        parsed = json.loads(chunk)
                        delta = parsed["choices"][0]["delta"]
                        if delta.get("content"):
                            now = time.perf_counter()
                            token_times.append(now)
                            if metric.first_token_time is None:
                                metric.first_token_time = now
                    except Exception:
                        continue

            metric.end_time = time.perf_counter()
            metric.total_latency_ms = (metric.end_time - metric.start_time) * 1000
            metric.completion_tokens = len(token_times)

            if metric.first_token_time:
                metric.ttft_ms = (metric.first_token_time - metric.start_time) * 1000

            if len(token_times) > 1:
                gaps = [
                    (token_times[i] - token_times[i - 1]) * 1000
                    for i in range(1, len(token_times))
                ]
                metric.inter_token_latency_ms = sum(gaps) / len(gaps)

            if metric.completion_tokens > 0 and metric.total_latency_ms > 0:
                metric.tokens_per_second = metric.completion_tokens / (metric.total_latency_ms / 1000)

            metric.is_success = True

        except Exception as exc:
            metric.end_time = time.perf_counter()
            metric.is_success = False
            metric.error = str(exc)
            metric.total_latency_ms = (metric.end_time - metric.start_time) * 1000

        return metric
