# Executed local Airflow TaskFlow example

This optional example runs Apache Airflow **2.11.0** using actual `DAG.test(use_executor=False)` with a fresh local SQLite metadata database for each scenario. The Python 3.12 environment is separate from core/dbt dependencies. It demonstrates task dependencies, one native retry and a publication gate. It does not start or deploy a scheduler, web/API server or executor service.

```mermaid
flowchart LR
    A[Generate seed7 synthetic fixture] --> B[Build canonical metrics]
    B --> C[Validate totals and retention]
    C --> D[Write local publication manifest]
```

The [TaskFlow source](../orchestration/moba_dag.py) defines four real tasks. XCom values are only local file paths; metric datasets stay in run-local JSON files. The [runner](../scripts/run_airflow_demo.py) creates a fresh home/config/metadata database per scenario and reads final states from Airflow task instances. Existing Airflow configuration variables are removed from each child's inherited environment, then only wrapper-owned settings are supplied. No default connections are loaded. Tests supply unrelated Airflow configuration/database paths and verify that no files are created at those paths.

## Actual observed outcomes

[Recorded summary](airflow-output.json) comes from executing all scenarios, not a hand-authored dashboard state:

| Scenario | DAG | Generate | Build | Validate | Local publish | Build attempts | Manifest exists |
|---|---|---|---|---|---|---:|---|
| Clean | success | success | success | success | success | 1 | yes |
| One transient build failure | success | success | success | success | success | 2 | yes |
| Corrupt retained-user count | failed | success | success | failed | upstream_failed | 1 | no |

The transient case raises before writing metrics on its first attempt; Airflow's configured one retry with zero delay executes attempt 2 successfully. There is no custom retry loop. This does not prove recovery from every interruption point or distributed side-effect idempotency.

The permanent bad-metrics case changes retained users to cohort users + 1. The validation task raises `AirflowFailException`; the default all-success dependency rule prevents publication. The unapproved metrics file remains in that isolated scenario's artifacts for inspection, with no published manifest. Normal and recovered scenarios independently verify 101 user-days, 14 DAU dates, 8 retention rows, 3 hero groups, 12 player groups, 4 payment dates and 1,396 fictional cents. These fixture-specific gates additionally check retention bounds, rate arithmetic, allowed offsets and observable maturity. They are not a general contract engine or evidence of source completeness.

## Reproduce

From the repository root, macOS/Linux with Python 3.12:

```bash
python3 -m venv .venv-airflow
.venv-airflow/bin/python -m pip install --index-url https://pypi.org/simple 'apache-airflow==2.11.0' --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.11.0/constraints-3.12.txt
.venv-airflow/bin/python -m pip install --index-url https://pypi.org/simple -r requirements-airflow.txt .
.venv-airflow/bin/python -m pip check
PYTHONPATH=src .venv-airflow/bin/python scripts/run_airflow_demo.py --output .airflow-output/demo-1
PYTHONPATH=src .venv-airflow/bin/python -m unittest discover -s tests -v
```

Use a fresh output folder. If any scenario directory or summary already exists, the runner refuses to overwrite it before launching workers. It never clears/resets a pre-existing Airflow database. The internal worker mode verifies wrapper-owned configuration before importing Airflow. Per-child execution timeout is 120 seconds. Read `summary.json` for portable results and each scenario's `worker.log`, metadata and artifacts for details. A failed overall DAG is expected in `bad_metrics`; the wrapper exits successfully only when observed outcomes match all three expected scenarios.

Airflow is first installed with the official version/Python-specific constraints; the normal project is installed afterward while keeping Airflow pinned, following the official installation pattern. The version is pinned for this local reproducibility experiment, not presented as the newest production release. No dbt package is required in this environment.

## Publication and limits

`publish_local` writes a local JSON manifest with metric-file name, SHA256, row counts and fictional revenue. It publishes nothing to GitHub, a website, a cloud warehouse or another person. JSON artifacts use same-directory temporary files and atomic replacement; there is no fsync/power-loss durability claim. A failed gate leaves the manifest absent. The wrapper's fresh-directory scope prevents stale success artifacts from being mistaken for the failed scenario's output.

The DAG has `schedule=None`, `catchup=False` and local file paths, and is built by a factory for these manual runs. It is not installed as a scheduler-discovered production DAG. DAG.test uses a serialized local execution path, bypassing an executor service. Distributed workers would require a proper shared artifact/object-store design. Scheduler operation, scheduled catchup/backfill, alerts, secrets/IAM, external sources, multi-worker concurrency, AWS and Kafka/Spark remain unimplemented here.

## Verification and references

An expected-behavior integration test first failed because the runner was absent. The completed tests assert actual states, attempt numbers, independent metrics, bad-manifest absence, protection of existing scenario files, and isolation from inherited Airflow configuration. [Airflow-environment output](airflow-test-output.txt) records 30 discovered tests, with only the separate optional dbt test skipped. [dbt-environment compatibility output](airflow-dbt-compat-output.txt) records 30 discovered tests with the two optional Airflow tests skipped. The dedicated CI jobs explicitly check installation/version before running, so each optional feature is actually exercised in its own job. All core tests also run on Ubuntu Python 3.11/3.12. Remote CI status must be checked on the published commit.

Original Pages snapshots remain byte-identical; no current production system or real-time data is implied. Official references: [DAG.test semantics](https://airflow.apache.org/docs/apache-airflow/2.11.0/core-concepts/debug.html), [constrained installation](https://airflow.apache.org/docs/apache-airflow/2.11.0/installation/installing-from-pypi.html).
