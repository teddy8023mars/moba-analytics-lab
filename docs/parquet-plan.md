# Optional local Parquet snapshot plan

Implements the already reviewed 2026-10-15 storage design in root PLAN.md.
Reuse DuckDB1.4.3, no new dependency/cloud service. Preserve canonical pipeline,
existing dashboards and default CLI. Export a validated nonempty user-day fact to
new owned Hive date partitions, roundtrip all rows, recompute DAU and record actual
filter/projection plan. No append/overwrite, atomic-directory/durability/performance
or production lake claim. I/O failure may leave partial owned files without a
completion summary; use a new directory on retry.

Files: src/moba_lab/parquet_snapshot.py exports export_user_days(rows, output,
filter_date) and returns/writes summary.json only after successful readback and
connection close; script scripts/run_parquet_demo.py validates seed7 Jan14
101facts/14dates and sourceDAU before invoking exporter with Jan08 filter.
Tests tests/test_parquet_snapshot.py: literal5facts/3dates/DAU2,1,2 and real DATE
schema, quote/Unicode IDs and absent-date filter, invalid/empty/duplicate grain
before writes, existing directory and dangling symlink refused, real script output
and rerun error. Actual EXPLAIN evidence, no source text assertions.

1. Clean baseline, expected-behavior tests, observe RED.
2. Implement bound-parameter typed export/readback with strict input grain,
   fresh output ownership, actual file inventory and projected date-filter plan.
3. Focused/full suites in complementary optional environments; actual standalone
   demo in fresh output; original showcase byte comparison.
4. Guide/README evidence and honest small-file/local-only limits, independent
   review, personal publish, exact-commit CI and Pages check.
