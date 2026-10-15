# Bounded native Linux scheduler experiment

This optional Airflow2.11.0 example runs a real scheduler and SequentialExecutor
against fresh local SQLite metadata. Two `@once` DAGs use the same four-task
canonical MOBA factory as the separate [DAG.test example](airflow.md). It is a
short-lived synthetic experiment, without a web/API/log-serving listener,
cloud resources, ongoing uptime or a production deployment.

## Reproduce on Linux, Python3.12

```sh
python3 -m venv .venv-airflow
.venv-airflow/bin/python -m pip install 'apache-airflow==2.11.0' --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.11.0/constraints-3.12.txt
.venv-airflow/bin/python -m pip install -r requirements-airflow.txt .
.venv-airflow/bin/python -m pip check
PYTHONPATH=src .venv-airflow/bin/python scripts/run_scheduler_demo.py --output .airflow-output/scheduler-1
RUN_SCHEDULER_INTEGRATION=1 PYTHONPATH=src .venv-airflow/bin/python -m unittest discover -s tests -p test_scheduler_demo.py -v
```

Use a completely new output path; directories, files and broken symlinks are
refused before initialization. The runner strips inherited Airflow configuration,
uses owned HOME/config/DB/DAG/plugins/log paths, and initializes metadata without
default connections. It never resets an existing database. The interpreter's bin
folder is prepended to PATH because SequentialExecutor invokes the `airflow`
console command. The generated factory wrapper explicitly imports Airflow so
its default safe-mode discovery includes the file.

The scheduler discovers both DAGs and creates runs from their historical `@once`
timetables; there is no manual trigger or DAG.test call in this runner. Default
observation deadline180seconds, configurable `--timeout` in (0,300]. Initialization
has a separate60-second limit; bounded process cleanup follows observation.
An outer10-minute CI job limit also bounds dependency installation and test work.
On success the controller checks exact run/task states and independently verifies
the clean publication manifest before writing `summary.json`. Failure returns
nonzero, leaves diagnostic files and emits no success summary.

## Acceptance and retained evidence

The dedicated `scheduler-integration` CI job enables both Linux-native tests.
It retains selected synthetic JSON and logs in `native-scheduler-evidence` as a
tar.gz archive; generated Airflow configuration and SQLite are excluded. Tar
transport preserves Airflow log paths containing colons, which direct artifact
upload rejects. The archive is a recorded test output, not a live production feed.

| Scenario | Scheduled DAG | Generate/build | Validate | Publish |
|---|---|---|---|---|
| Canonical clean | success | success/success | success | success, verified manifest |
| Retained users > cohort | failed | success/success | failed | upstream_failed, manifest absent |

Clean expected fixture totals:101user-days,14DAU dates,8retention rows,3hero groups,
12player groups,4payment dates and1396fictional cents. These are deliberately tiny
synthetic results; the separate benchmark documents its own larger local workload.
The bad-metrics file remains available for diagnosis, without an approved manifest.

The timeout integration test starts the actual scheduler with a0.001-second
observation limit and verifies nonzero exit, cleanup and no summary. It does not
wait for worker descendants. A separate process test starts an owned parent and
SIGTERM-ignoring child, tracks their identities and exercises kill escalation;
an unrelated sentinel and mismatched creation-time entry survive. Cleanup
reports only observed PID+creation-time matches, not every process on the host.

## Limits and failure history

SQLite/SequentialExecutor and local XCom file paths are development constraints.
This does not demonstrate HA, distributed workers/shared artifacts, periodic
calendar processing, backfill, production alerting, cloud IAM or AWS deployment.
The separate DAG.test example remains the native retry evidence; this scheduler
exercise does not add retry or distributed exactly-once claims. Versions are
pinned for reproducibility rather than presented as latest production choices.

Earlier macOS service probes stalled after task-runner fork; the precise cause
was not established. This native runner therefore explicitly requires Linux.
The first canonical Linux feature commit654d42b timed out because default safe-mode
file discovery skipped the factory wrapper; parser logs reported0files and no
DAG/task rows. The [regression](scheduler-discovery-red.txt) used Airflow's real
heuristic and returned False. An explicit import fixed discovery, without
turning safe mode off; [focused local checks](scheduler-discovery-green.txt)
passed. Original DAG.test behavior is preserved. The toy feasibility branch is
separate evidence, and is not included in this feature.

Actual Ubuntu/Python3.12 CI on commit e2cb818 passed all six jobs, including
both native scheduler tests: [run38749347369](https://github.com/teddy8023mars/moba-analytics-lab/actions/runs/38749347369).
The downloaded [recorded summary](scheduler-output.json) confirms the table above;
clean output bytes match manifest SHA256 and independently counted fixture totals.
Success cleanup observed19 process identities and left none tracked; the
[timeout cleanup](scheduler-timeout-cleanup.json) observed1 and left none tracked.
The source regression is included in [50 local tests](scheduler-corrected-local-tests.txt)
with3optional skips on macOS; the actual Linux native tests passed in CI.
A new main-branch commit must have its own CI checked before claiming that exact
commit passed. Official version-specific reference:
[Airflow2.11 scheduler CLI](https://airflow.apache.org/docs/apache-airflow/2.11.0/cli-and-env-variables-ref.html).
