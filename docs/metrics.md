# Metrics Reference

## Endpoint Metrics

### Latency Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| TTFT | ms | Time from request start to first streamed token |
| Inter-Token Latency (ITL) | ms | Average delay between consecutive output tokens |
| End-to-End Latency | ms | Total time from request submission to last token |
| Cold Start | ms | First-request latency after endpoint inactivity |
| Warm Start | ms | p50 latency when endpoint is fully warmed up |

### Throughput Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| Throughput | req/sec | Successful requests per second (wall-clock) |
| Tokens/sec | tok/sec | Output tokens generated per second |
| Total Tokens | count | Sum of all prompt + completion tokens |

### Reliability Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| Success Rate | % | Fraction of requests returning HTTP 200 |
| Error Rate | % | Fraction of requests failing (timeout, 4xx, 5xx) |

### Percentile Distribution

All latency metrics are reported at:

- **p50** — Median: half of requests are faster than this
- **p90** — 90th percentile: 1 in 10 requests is slower
- **p95** — 95th percentile: 1 in 20 requests is slower
- **p99** — 99th percentile: 1 in 100 requests is slower (tail latency)

## Cost Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| Cost per Request | USD | Average total cost per API call |
| Cost per 1M Tokens | USD | Blended cost for one million tokens |
| Total Benchmark Cost | USD | Full cost of the benchmark run |
| Monthly Projection | USD/mo | Estimated monthly cost at given request rate |

Cost is calculated as:

```
cost = (prompt_tokens / 1e6 × input_price) + (completion_tokens / 1e6 × output_price)
```

## Job Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| Job Creation Time | ms | Time for the Jobs API to accept the request |
| Queue Delay | ms | Time from accepted to RUNNING status |
| Startup Time | ms | Container initialization time |
| Execution Time | ms | Time from RUNNING to COMPLETED |
| Total Time | ms | Full lifecycle: creation → completion |

## Interpreting Results

### TTFT Targets (approximate)
- **< 200ms p50**: Excellent — suitable for interactive chat
- **200–500ms p50**: Good — acceptable for most applications
- **500ms–1s p50**: Fair — may feel slow for interactive use
- **> 1s p50**: Poor — investigate model/endpoint configuration

### Throughput Targets
- These depend heavily on token length; compare across runs with the same configuration

### Error Rate Targets
- **< 0.1%**: Excellent
- **0.1–1%**: Good
- **1–5%**: Investigate — may indicate rate limiting or capacity issues
- **> 5%**: Critical — endpoint may be misconfigured or overloaded
