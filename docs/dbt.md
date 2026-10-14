# Actual local dbt build and failure gate

## Setup and run

From the repository root, Python 3.12 on macOS/Linux:

```bash
python3 -m venv .venv-dbt
.venv-dbt/bin/python -m pip install --index-url https://pypi.org/simple -r requirements-dbt.txt .
PYTHONPATH=src .venv-dbt/bin/python scripts/run_dbt_demo.py --output .dbt-output/demo-1
PYTHONPATH=src .venv-dbt/bin/python -m unittest discover -s tests -v
```

A fresh output directory receives warehouse.duckdb, per-phase logs/results, dbt manifest/run artifacts and summary.json. Existing warehouse files are refused rather than overwritten. The final warehouse contains the earlier January8 cutoff; summary.json reports January14 results and the separate early-cutoff check. No global ~/.dbt profile is edited. All paths are local; no cloud credentials are needed. Anonymous usage statistics are disabled. Top-level versions are pinned in requirements-dbt.txt; transitive packages are resolved by pip, not a complete lock file.

## Model dependency flow

The loader uses the canonical strict fixture validator (an internal API within this repo), retaining exact duplicates in typed raw tables. dbt handles SQL transformations using source/ref dependencies:

- Five staging models apply the observation cutoff and deduplicate users, logins, matches, participants and payments.
- user_day and fact_player_match establish independent login/day and participant/match grains.
- DAU, observable exact-day D1/D7 retention, hero/player statistics and payment-date monetization consume those grains.
- observation holds the explicit last completely observed UTC day. Profiles apply UTC on every dbt connection.

Every model materializes as a local table in analytics. No incremental model is claimed. Checked-in SQL is adapted from the existing canonical model definitions; exact parity checks detect future drift between the two paths. dbt does not replace raw validation.

## Independent evidence and injected failure

[Actual compact output](dbt-output.json) records versions and observed results. The generated fixture contains 101 user-days, 14 DAU days, 8 retention cohort/offset rows, 3 hero groups, 12 player groups and 4 payment dates. January1 has D1 2/3 and D7 3/3; revenue is 1,396 fictional cents. These literal expectations supplement full canonical parity. At January8 only 5 retention rows remain observable, including only January1 D7.

Thirteen models and three singular data tests build successfully. Tests enforce required fact keys, composite uniqueness, bounded/coherent retention counts and ratios, supported offsets and cohort maturity. The runner changes exactly one materialized retained count to cohort_users+1 and invokes only retention_invariants: expected exit1, one failed record. It then rebuilds all models and proves clean exit0 and original metrics restored. These are real CLI runs, not fabricated snapshots. The corrupt warehouse is not exported into Pages.

The optional integration test is skipped when dbt is absent; a dedicated CI job installs pinned dbt dependencies and runs the full suite so that feature cannot silently skip in its own job. Base Python3.11/3.12 jobs continue to test the lightweight core.

## Scope and references

This is a single-process local full rebuild on tiny synthetic fixtures. Three data tests are targeted invariants, not exhaustive business rules. The corruption is injected after raw ingestion; normal raw validation rejects malformed source events earlier. No Airflow schedule, AWS deployment, Spark/Kafka, large-scale benchmark or production reliability claim follows from this demo. The optional models do not change the public dashboard's canonical outputs.

Implementation references: [official dbt-duckdb profile, file and settings documentation](https://github.com/duckdb/dbt-duckdb), [official dbt data-test semantics](https://docs.getdbt.com/docs/build/data-tests). Initial integration regression failed because the runner was absent. During adaptation, an overly broad one-time SQL rewrite replaced a column alias with a model ref and missed a newline before retention SQL; the real build exposed the cycle. Checked-in models were corrected to rewrite only relation references, then actual builds/parity/fault tests passed. No text-rewrite generator is part of runtime.
