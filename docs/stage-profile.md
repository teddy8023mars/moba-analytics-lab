# Full-rebuild stage timing

Measured on 2026-10-15 with the same regular synthetic benchmark shape, Python 3.12.14, DuckDB 1.4.3, macOS Darwin 25.6.0 arm64, 10 logical CPUs and default 10 DuckDB threads. Each size has three sequential fresh child processes; every sample checks independent expected DAU, retention, revenue and player-match totals. [Raw recorded samples](stage-profile-output.json) retain every stage duration and process peak RSS. This was a normal laptop session without idle/power/cache isolation.

## Actual stage medians, seconds

| Users | Validation | Connection setup | Raw load | SQL models | Fetch/format | Close | Inner total | Median raw-load share |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1000 | 0.0212 | 0.0042 | 4.1079 | 0.0131 | 0.0115 | 0.0008 | 4.1592 | 98.78% |
| 5000 | 0.1114 | 0.0047 | 20.7094 | 0.0387 | 0.0569 | 0.0008 | 20.9215 | 98.99% |

Each cell is the median of that stage's three observations. Different stage medians can come from different runs, so summing median columns need not reproduce median total. The percentage is the median of each sample's raw_load / inner total ratio. Original outer full-call durations are also retained. Inner total partitions from just after timing-argument validation until successful connection close; outer call includes optional argument checking and publishing the timing dict. Instrumentation overhead is included; no uninstrumented/profiled speed comparison is claimed.

## What is measured

- **validation**: observation date parsing, normalization, duplicate conflicts, event types and foreign-key/time checks.
- **connection_setup**: in-memory connection, UTC setting, observation table creation/insertion.
- **raw_load**: raw-table creation, dictionary/key lookup, normalized duplicate expansion, Python tuple preparation and bound `executemany` insertions across all five raw tables.
- **sql_models**: reading packaged model SQL and executing all staging/fact/mart statements.
- **result_fetch**: six SELECTs, ordering, fetching and converting results into dictionaries/ISO dates.
- **connection_close**: successful context-manager exit and connection close.

These are elapsed wall-clock regions, not per-operator CPU profiles. Peak RSS retains whole-process scope described in [the original benchmark](benchmark.md), not per-stage memory. Input generation, imports and output writing remain outside the timed function.

## Finding and next experiment

Raw loading accounts for about 99% of elapsed pipeline time on both measured regular workloads. The 5,000-user workload has 107,500 raw records; median raw loading is about 20.71 seconds, versus about 0.039 seconds for the complete SQL-model stage. The evidence locates the slow region, but does not isolate how much belongs to row marshalling, bound inserts, Python loops or table setup. It does not imply all SQL workloads are cheap.

The next justified experiment is batching parameterized raw inserts while preserving typed values, exact duplicate raw cardinality, strict validation and all six metric outputs. Measure baseline and candidate in the same controlled experiment; keep the simpler path if it does not produce a defensible benefit. No optimization or speedup has been delivered in this profiling milestone. The diverse tiny showcase and all metric/model definitions remain unchanged; this regular one-cohort/one-hero/100%-retention workload is not representative production telemetry.

## Reproduce and API

Install the normal project (dbt optional, unnecessary for this benchmark):

```bash
PYTHONPATH=src .venv/bin/python scripts/benchmark_pipeline.py --users 1000 5000 --repeats 3 --profile-stages --output profile-local.json
```

The benchmark's existing bounded scale/repeat/worker-timeout rules apply. Python callers can request `run_pipeline(data, as_of, timings={})`, retaining their dict to inspect six stage seconds and `total`. Use a variable, for example:

```python
from moba_lab.pipeline import run_pipeline
stages = {}
metrics = run_pipeline(data, '2026-01-14', timings=stages)
print(stages)
```

Default calls preserve the original result shape and do not sample the performance clock. The dictionary is replaced only after a successful complete rebuild, including connection close. Failed validation or later SQL errors leave its previous contents unchanged; callers must handle the exception and avoid presenting a prior report as the failed run. No failed-run profiling or per-stage memory capture is implemented. `timings` must be a dict or None. Timing publication and optional argument checking are outside inner total.

Verification: three new expected-behavior tests first failed due to missing timings keyword/CLI flag. Full 24-test suite with optional dbt passes in [stage-profile-test-output.txt](stage-profile-test-output.txt). Tests compare all profiled metrics against the unprofiled path, assert literal known retention/revenue, check input preservation and timing partition, exercise both early validation and injected late SQL failures, and run a fresh-process four-user CLI sample with independent totals. No performance thresholds are used in tests.
