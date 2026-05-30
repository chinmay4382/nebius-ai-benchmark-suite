# Architecture

## System Overview

NebiusBench is organized into four layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app/)                       │
│  Home │ Run Benchmark │ Live Metrics │ Compare │ Cost │ Report│
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                 Benchmark Runner (benchmark/runner.py)       │
│  Orchestrates endpoint and job benchmarks                    │
│  Emits LiveUpdate callbacks for real-time UI                 │
└─────────┬──────────────────────────────────┬────────────────┘
          │                                  │
┌─────────▼────────────┐         ┌───────────▼───────────────┐
│  Endpoint Benchmarks │         │    Jobs Benchmarks         │
│  benchmark/endpoint/ │         │    benchmark/jobs/         │
│  • TTFTBenchmark     │         │    • JobStartupBenchmark   │
│  • ThroughputBench   │         │    • JobExecutionBenchmark │
│  • ConcurrencyBench  │         │    • JobCompletionBenchmark│
│  • StreamingBench    │         └───────────────────────────┘
│  • ColdStartBench    │
│  • WarmStartBench    │
└─────────┬────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│                  Metrics Pipeline                             │
│  MetricsCollector → MetricsAnalyzer → MetricsReporter        │
└─────────┬────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│                 Storage Layer (SQLite)                        │
│  BenchmarkRunORM │ BenchmarkResultORM │ ReportORM             │
│  Via SQLAlchemy ORM + Repository pattern                      │
└───────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### Async HTTP with httpx
All HTTP requests use `httpx.AsyncClient` with `asyncio.gather()` for true concurrent benchmarking. The `asyncio.Semaphore` limits concurrent connections to the configured concurrency level.

### Synchronous Entry Points
Each benchmark class provides both `run()` (async) and `run_sync()` (synchronous wrapper via `asyncio.run()`). Streamlit calls the sync variants.

### Real-Time UI Updates
The `BenchmarkRunner` accepts an `on_update: Callable[[LiveUpdate], None]` callback. During execution, it calls this callback with progress info, allowing Streamlit to update progress bars and live charts between request batches.

### Repository Pattern
All database access goes through `BenchmarkRepository`, which provides:
- `create_run()` — write run metadata before execution starts
- `update_run_status()` — update status as run progresses
- `save_result()` — persist metrics JSON after each benchmark phase
- `get_run_summary_list()` — lightweight summaries for the UI tables

### Pydantic v2 Models
Data transfer objects use Pydantic v2 models with strict type checking. ORM models use SQLAlchemy 2.0 mapped columns. The two layers are kept separate — the repository converts between them.

## File Structure

```
benchmark/
├── models.py          # Pydantic data models (shared across all modules)
├── runner.py          # Main orchestrator + cost estimation
├── endpoint/          # Endpoint benchmark implementations
│   ├── base.py        # BaseEndpointBenchmark + shared HTTP logic
│   ├── ttft.py        # Streaming TTFT measurement
│   ├── throughput.py  # Concurrent throughput testing
│   ├── concurrency.py # Multi-level concurrency sweep
│   ├── streaming.py   # Streaming ITL measurement
│   ├── cold_start.py  # First-request latency
│   └── warm_start.py  # Steady-state latency
├── jobs/              # Nebius AI Jobs benchmarks
│   ├── startup.py     # Job creation + queue timing
│   ├── execution.py   # Execution time measurement
│   └── completion.py  # Full lifecycle timing
├── metrics/           # Analysis and reporting
│   ├── collector.py   # Thread-safe metric accumulator
│   ├── analyzer.py    # Statistical aggregation (NumPy)
│   └── reporter.py    # MD/JSON/HTML report generation
└── storage/           # Persistence layer
    ├── database.py    # SQLAlchemy engine setup
    ├── orm_models.py  # SQLAlchemy ORM models
    └── repository.py  # Repository pattern

app/
├── Home.py            # Landing page
├── ui_utils.py        # Shared CSS, colors, chart builders
└── pages/
    ├── 1_Run_Benchmark.py    # Benchmark configuration + execution
    ├── 2_Live_Metrics.py     # Real-time metrics display
    ├── 3_Compare_Runs.py     # Side-by-side run comparison
    ├── 4_Cost_Analysis.py    # Cost estimation + model comparison
    └── 5_Report_Generator.py # Report generation + downloads
```
