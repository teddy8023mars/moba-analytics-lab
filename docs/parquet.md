# A local partitioned Parquet user-day snapshot

This optional exercise persists the canonical user-day fact as typed Parquet,
reads every record back, recomputes DAU and records a real date-filter query plan.
It uses the existing pinned DuckDB1.4.3 dependency. All demo data is synthetic.
There is no AWS account, cloud resource, broker, catalog or additional dependency.

From the repository root, after base installation:

```sh
PYTHONPATH=src .venv/bin/python scripts/run_parquet_demo.py --output .parquet-output/run-1
```

Choose a **new output directory** every time. Existing directories, files and
output symlinks are refused; the experiment never appends to or overwrites an
existing dataset. The script exits0 and prints the completed summary on success,
or exits2 on handled validation, filesystem or DuckDB failure.

## Layout and actual results

[Actual seed7 output](parquet-output.json), cutoff2026-01-14:

- **101** user-day facts, **14** date partitions/files; all records roundtrip exactly.
- Recomputed DAU agrees with the canonical pipeline on every date.
- Filtering 2026-01-08 returns nine user IDs: u00,u01,u02,u03,u05,u07,u09,u10,u11.
- The actual EXPLAIN reports projection `user_id`, a date File Filter and
  **Scanning Files: 1/14**. Its `~2 rows` is an optimizer estimate, not the actual
  nine returned users, scanned bytes or a timing measurement.

```text
run-1/
  user_day/
    activity_date=2026-01-01/data_0.parquet
    activity_date=2026-01-02/data_0.parquet
    ...
  summary.json
```

`activity_date` is written from SQL DATE values and recovered from Hive directory
keys as DATE; `user_id` is VARCHAR. Data is compressed with ZSTD. One DuckDB writer
thread keeps this small demonstration's file inventory simple. The filtered query
projects only user_id, while the separate full-read comparison deliberately reads
all dates. Partition pruning in the filtered query does not mean the whole
experiment only reads one file.

[Official Hive partitioning guidance](https://duckdb.org/docs/lts/data/partitioning/hive_partitioning)
explains directory partition keys and filter pushdown;
[Parquet guidance](https://duckdb.org/docs/current/data/parquet/overview) describes
columnar files and compression. Current documentation can target a newer release;
the compatibility evidence here comes from actual pinned1.4.3 execution.

## Input and completion boundary

`moba_lab.parquet_snapshot.export_user_days(rows, output, filter_date)` requires
nonempty exact activity_date/user_id records, canonical YYYY-MM-DD dates, nonblank
string IDs and unique(date,user_id) grain. Invalid input is rejected before the
output directory is created. This exercise explicitly refuses an empty fact
instead of producing an unqueryable partition tree. Values and paths are bound
parameters, so quotes in IDs and output paths remain data.

The exporter compares full sorted rows with its source facts and recomputes daily
counts independently with Python Counter before checking Parquet SQL results.
The seed runner first verifies literal101facts/14dates and reconciles canonical
DAU with those source facts. The summary is published by a same-directory file
rename only after roundtrip/filter checks and connection close.

I/O failure can leave **owned partial data** without a completion summary; retry
with a new directory. There is no transaction across the directory, fsync,
concurrent-writer/race protection or durable power-loss claim. Callers should only
consume a successfully completed owned run. No manifest signing, source
completeness or generic schema-evolution guarantee is provided.

## Verification and limits

Five initial acceptance methods failed before the API/script existed:
[RED record](parquet-red.txt). Six final methods cover literal five-fact DAU2/1/2,
real DATE schema, quoted/Unicode IDs, missing-date filter, invalid/empty/duplicate
input before writes, preserved existing markers and dangling symlinks, actual
seed runner and repeat-run failure. A narrow injected summary-write error leaves
real Parquet files but no completion summary; retry is refused. DuckDB export and
readback remain real in that fault test.

[dbt environment suite](parquet-dbt-test-output.txt) and
[Airflow environment suite](parquet-airflow-test-output.txt) each discover43methods;
combined optional environments cover all43unique methods. Remote exact-commit CI
must be checked separately after publication. Existing14dashboard snapshots
regenerate unchanged.

Tiny daily files illustrate a layout, not a production recommendation: file sizes,
partition cardinality, row groups and compaction need workload-specific decisions.
No speedup, compression ratio, network I/O, S3/IAM, distributed execution, Iceberg
or Delta transaction, late-data rewrite, or production-scale result is claimed.
The original six analytical marts, default CLI and existing dashboards are unchanged.
