# Benchmark Methodology

## Overview

NebiusBench uses a structured, reproducible approach to measuring LLM inference performance on Nebius AI Serverless Endpoints.

## Request Flow

All benchmarks use OpenAI-compatible HTTP requests against Nebius AI endpoints:

```
Client → httpx.AsyncClient → POST /chat/completions → Nebius Endpoint → Response
```

Timing is captured using `time.perf_counter()` for high-resolution measurements.

## TTFT Measurement

Time-To-First-Token (TTFT) is measured exclusively in **streaming mode**:

1. Record `t_start = time.perf_counter()` before request submission
2. Parse Server-Sent Events (SSE) stream line by line
3. Record `t_first_token` when the first non-empty `delta.content` chunk arrives
4. `TTFT = (t_first_token - t_start) × 1000` milliseconds

Non-streaming requests cannot accurately measure TTFT since the full response arrives at once.

## Inter-Token Latency (ITL)

ITL is measured as the average gap between consecutive token arrival times:

```
ITL = mean(t[i] - t[i-1]) for i in range(1, n_tokens)
```

## Concurrency Testing

Concurrency levels are swept using `asyncio.Semaphore` to limit simultaneous active requests:

```python
semaphore = asyncio.Semaphore(concurrency_level)
tasks = [bounded_request(i) for i in range(request_count)]
results = await asyncio.gather(*tasks)
```

This simulates real-world concurrent load patterns.

## Cold Start

Cold start is measured as the latency of the **first request** sent to an endpoint after a period of inactivity. In practice:

1. Send an initial streaming request to the endpoint
2. Record `total_latency_ms` for this first request
3. Compare against warm-start latency measured immediately after

## Statistical Aggregation

All latency distributions are computed using NumPy:

- **p50** (median): `np.percentile(arr, 50)`
- **p90**: `np.percentile(arr, 90)`
- **p95**: `np.percentile(arr, 95)`
- **p99**: `np.percentile(arr, 99)`

## Throughput

```
throughput_rps = successful_requests / wall_clock_duration_seconds
tokens_per_second = total_completion_tokens / wall_clock_duration_seconds
```

Wall-clock duration captures the full benchmark window including concurrency overhead.

## Retry Handling

Failed requests (network errors, 5xx) are recorded but not retried during benchmarks to preserve measurement accuracy. Timeout is configurable (default: 120s).

## Reproducibility

Every benchmark run stores its full configuration in SQLite including:
- Model ID, endpoint URL, concurrency, request count
- Prompt dataset selection
- Timestamp and run ID

Results can be re-exported at any time from the Report Generator page.
