# Measured bounded-parameter loading improvement

The preceding [stage profile](stage-profile.md) located about 99% of elapsed pipeline time inside raw-table preparation/loading. This change compares the original executemany strategy with batches of 500 rows in one parameterized INSERT VALUES statement. Both use the same validated normalized records, typed raw schema, exact duplicate raw rows, SQL models and result fetch.

## Actual interleaved comparison

2026-10-15, macOS Darwin 25.6.0 arm64, Python 3.12.14, DuckDB 1.4.3, 10 logical CPUs/default DuckDB threads. Three pairs per workload, with strategy order alternating reference/candidate then candidate/reference then reference/candidate. Each variant runs in its own fresh child process. The laptop was not idle/power/cache isolated; normal local work occurred. No statistical significance or percentile claim follows from three pairs.

| Synthetic users | Raw records | Reference median seconds | Batched median seconds | Reduction in median elapsed time | Reference / batched median peak RSS MiB |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 21,500 | 4.144 | 3.006 | 27.5% | 97.7 / 94.2 |
| 5,000 | 107,500 | 21.626 | 15.379 | 28.9% | 227.0 / 180.4 |

[All 12 actual samples](load-comparison-output.json) retain execution order, complete metric digests, independent correctness results, wall seconds, stage seconds and whole-process peak RSS. Reduction is `1 - candidate median / reference median`; these are full-pipeline durations, not SQL-only speed. Ratios compare the new interleaved run rather than the historical separate benchmark. Lower RSS was observed here but is not a guaranteed reduction for arbitrary inputs. Peak RSS includes imports, synthetic input generation, pipeline, correctness checks and complete-result JSON serialization/hash. It is not isolated SQL memory or an incremental memory allocation.

Each sample validates closed-form expected DAU, exact D1/D7 retention, user-days, transactions, revenue and player-match grain. Each pair also compares SHA256 of a stable serialization of all six complete result sets, covering more than aggregate counts. All six pairs match. The regular one-cohort/one-hero/all-users-retained benchmark is deliberately simple, not representative production telemetry or skew. The diverse showcase remains unchanged.

## Change and compatibility

The default canonical pipeline now uses `load_strategy='batched'`, with `insert_batch_size=500`. The reference `load_strategy='executemany'` remains available. Optional batch size must be an integer from 1 to 1,000 (booleans rejected), even for empty input; load strategy is one of the two named values. Default CLI use requires no new flags or dependencies. Only the Python API and benchmark expose strategy selection.

Values are bound parameters; SQL contains only trusted static table/schema names and placeholder groups. A batch has at most 1,000 rows and, with the existing widest schema, 7,000 parameters. The last partial batch is inserted normally. Strict source validation/normalization occurs first, before either loading strategy. Exact duplicate rows still enter raw tables and deduplicate in the same staging SQL. Input lists and metric grains do not change. Typed integer/timestamp/boolean values avoid JSON/float conversion during ingestion.

This is bounded statement batching, not streaming ingestion: full validated records and prepared tuples remain in memory. Raw tables are temporary in a fresh in-memory connection; this does not add durable transactions, CDC or production exactly-once guarantees. The optional dbt demo's separate raw-loader implementation still uses executemany; no dbt execution speedup was measured or claimed.

## Reproduce

Use the normal installed project on macOS/Linux; dbt is unnecessary for comparison:

```bash
PYTHONPATH=src .venv/bin/python scripts/compare_loaders.py --users 1000 5000 --repeats 3 --output comparison-local.json
PYTHONPATH=src .venv/bin/python scripts/benchmark_pipeline.py --users 5000 --repeats 3 --load-strategy batched --profile-stages --output batched-local.json
PYTHONPATH=src .venv/bin/python scripts/benchmark_pipeline.py --users 5000 --repeats 3 --load-strategy executemany --profile-stages --output reference-local.json
```

Timing covers validation, setup, raw loading, all SQL models, fetching/formatting and connection close. Imports/input generation and post-run correctness/hash/report writing are excluded; optional profiling overhead is included equally. Existing benchmark size bounds and 180-second worker timeout apply; the comparison uses batch size 500. Output parent must exist and existing output files are overwritten. Old benchmark/profile commands now explicitly select executemany for historical reproducibility. Existing result JSON files remain historical records.

## Verification and limits

Three initial tests failed before loader options/helper existed. Tests cover batch sizes 1/2/3/500, last partial batch, raw duplicate cardinality, SQL-looking values bound as strings, UTC normalization from a +08:00 timestamp and exact BIGINT values/HUGEINT sums. Invalid options fail on empty inputs. A fourth CLI regression exercises alternating order and independent four-user totals without asserting any performance threshold. Full 28-test suite with optional dbt passes: [actual output](batched-load-test-output.txt). Default optimized output preserves all original 14 showcase snapshots byte-for-byte.

This approximately 29% local elapsed-time reduction is a measured result for two regular workloads, not a production SLA, universal percentage, distributed scale result or employer accomplishment. No AWS, Airflow or Spark/Kafka implementation follows from it. The next portfolio gap is executable orchestration/failure handling; further performance tuning should require a new measured bottleneck or workload, not a bigger headline.
