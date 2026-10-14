# Declared-scale local full-rebuild benchmark

Actual run on 2026-10-15: macOS/Darwin 25.6.0 arm 64, Python 3.12.14, DuckDB 1.4.3, 10 logical CPUs, DuckDB default 10 threads. This was a normal laptop session with other local work, without CPU/power/cache isolation. Results describe this experiment; they are not production throughput, an optimization improvement or a portable SLA.

## Workload and timing boundary

All users sign up on January 1 and log in on each of 14 days. A duplicate day 0 login per user makes raw logins 15 N but canonical user-days 14 N. Each user has two different 199/999-cent payments plus one exact duplicate. Each four-user group has two matches with four participants each. This is a deliberately regular correctness workload, not a realistic/skewed player population: all exact D1/D7 retention is 100%, one hero, one signup cohort, and no late-arriving data. The original diverse tiny showcase fixture remains unchanged.

Per size: users=N, raw logins=15 N, matches=N/2, participants=2 N, raw payments=3 N: total 21.5 N input rows. Largest run has 5,000 users and 107,500 raw rows across five tables, not 107,500 unique players or game matches. Validation rejects conflicting identities; exact duplicates survive raw insertion then deduplicate in staging.

Each of three sequential samples runs in a fresh Python subprocess with a new in-memory DuckDB connection. The timer covers canonical input validation, typed raw insertion, all SQL model rebuilds, fetching/formatting all six metric result sets. It excludes fixture generation, module imports, child startup, post-run correctness checks and report/HTML writes. Peak RSS is the whole child-process high-water mark including those imports, fixture generation and correctness checks; it is not SQL-only memory or incremental allocation. macOS reports bytes; Linux RSS is multiplied by 1024. All raw samples and process IDs are retained in [benchmark-output.json](benchmark-output.json).

## Actual observed samples

| Synthetic users | Raw rows | All sample seconds | Median seconds | All sample peak RSS MiB |
|---:|---:|---|---:|---|
| 100 | 2,150 | 0.433, 0.441, 0.433 | 0.433 | 67.3, 68.8, 68.2 |
| 1,000 | 21,500 | 4.191, 4.147, 4.172 | 4.172 | 97.1, 93.8, 98.4 |
| 5,000 | 107,500 | 20.829, 20.808, 20.937 | 20.829 | 225.1, 227.3, 225.9 |

No P95/P99 is estimated from three samples. No speedup is claimed because no baseline/optimized implementation pair was tested. Timings are end-to-end full rebuilds, not isolated SQL execution. Positive timings are recorded; CI has no timing thresholds.

## Independent correctness checks

Before scaling, a four-user test asserts literal input counts 4/60/2/8/12,56 user-days,14 DAU values of 4, D1/D7 cohorts of 4 retained out of 4, four player groups with two matches each,8 deduplicated transactions and 4,792 fictional cents. Every sample checks the closed-form workload totals, exact retention rows, all DAU counts and player/match grain. Largest sample verifies 70,000 user-days,10,000 transactions and 5,990,000 fictional cents. These invariants catch duplicate inflation; they do not model full MOBA rules or evaluate arbitrary datasets.

## Reproduce

Install the normal project; dbt is not needed for benchmarking. macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple .
PYTHONPATH=src .venv/bin/python scripts/benchmark_pipeline.py --users 100 1000 5000 --repeats 3 --load-strategy executemany --output benchmark-local.json
PYTHONPATH=src .venv/bin/python scripts/explain_user_day.py --output query-plan-local.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Output parent must exist; named output files are overwritten. Sizes must be positive multiples of 4 up to 20,000; repeats 1–10, each worker bounded to 180 seconds. Defaults are the recorded three sizes and three repeats. Custom runs above the defaults have not been measured here. Synthetic inputs/results are held in memory; high scales can consume substantial memory. Windows is outside this benchmark's supported RSS platforms.

## Read the actual query plan

[Recorded EXPLAIN ANALYZE](benchmark-query-plan.txt) comes from a separate four-user,60-login-record fixture. It applies the same date/user DISTINCT grain as canonical user_day, directly to raw_logins. The plan shows a table scan of 60 rows and HASH_GROUP_BY producing 56 rows, demonstrating duplicate collapse. This explanatory query omits canonical staging/cutoff and is not the whole-pipeline benchmark. Its tiny timing cannot explain the 20-second larger workload, prove a bottleneck or predict scaling. The next useful performance step is stage timing of validation/loading/SQL/result fetch before choosing an optimization.

References: [DuckDB EXPLAIN ANALYZE semantics](https://duckdb.org/docs/current/guides/meta/explain_analyze), [Python resource usage API](https://docs.python.org/3/library/resource.html). Recorded plans come from pinned DuckDB 1.4.3; current documentation may describe a newer version.

Historical results above used the executemany loader. The current default is bounded batched loading; select executemany explicitly to reproduce the reference algorithm. See [the interleaved comparison](batched-load.md) for the later measured change.
