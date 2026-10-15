# Bounded native scheduler plan

Extend the shared synthetic DAG factory with optional DAG ID/timetable/start date,
preserving the original DAG.test defaults. An optional Linux runner owns a fresh
HOME/config/SQLite/DAG/plugins/log directory and schedules canonical clean and
bad-metrics DAGs once. No manual trigger, fabricated states or DAG.test execution
in this path. No listeners, cloud services or persistent scheduler deployment.

Acceptance: exactly one scheduler-created run per DAG; clean's four tasks succeed,
manifest verification yields 101/14/8/3/12/4 rows and 1396 fictional cents; corrupt
retained count fails validation and marks publication upstream_failed with no
manifest. Existing paths including broken symlinks are refused; inherited config
and database stay untouched. A bounded deadline returns nonzero, cleans observed
owned process identities and emits no success summary. A separate process sentinel
and a mismatched process identity survive cleanup.

Test-first: new boundary tests initially failed due to absent runner (scheduler-red.txt).
Local macOS optional Airflow suite now discovers49 tests, passes with three skips
(dbt and two Linux-native tests); this is not native scheduler success. Dedicated
Linux CI explicitly enables both native tests and retains actual output/logs in
a tar.gz archive to preserve Airflow's colon-containing log paths. Runtime and
optional dependencies remain separate from core Python requirements.

Before main integration: independent source review, native Linux CI and archived
state/artifact/cleanup verification, documented actual results and honest limits.
The toy branch is feasibility evidence only and is not merged into this feature.

Independent review required a stronger descendant-cleanup check. The updated test
starts an owned parent and SIGTERM-ignoring child, observes the child's identity,
then verifies kill escalation, parent termination and survival of an unrelated
sentinel plus a mismatched creation-time entry. Focused local test passed in5.227s;
native Linux cases remain skipped locally and must pass before main integration.


First feature-branch Linux CI38747418450 (654d42b) failed only the native scheduler
success case: no DAGs discovered, no task attempts, 180-second timeout. Other five
jobs and scheduler timeout/boundary checks passed. Downloaded actual parser logs
report zero files; both observed run lists are empty and cleanup left zero of
three tracked identities. This is not a native MOBA success result.

Root cause: Airflow2.11 default safe-mode discovery requires both airflow and dag
in wrapper source; this factory wrapper lacked the former. A regression using
Airflow's own might_contain_dag returned False (RED), then True after adding an
explicit Airflow DAG import. No discovery safety setting is disabled. Focused six
tests now pass with two native-Linux skips on macOS. Corrective feature-branch CI
must establish actual canonical scheduling before main integration.

Corrective feature commit e2cb818: all six Linux CI jobs passed in38749347369. Downloaded archive independently verified exactly one scheduled run per scenario, expected task states, clean metrics hash/counts/revenue1396, bad manifest absence, timeout nonzero/no summary, and cleanup19/1identities with zero remaining. Final guide links actual output and failure history; main integration requires fresh exact-commit CI.
