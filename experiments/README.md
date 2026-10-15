# Disposable Linux scheduler feasibility probe

Experimental branch only; this is not the canonical MOBA scheduler demonstration.
Airflow 2.11.0 with SequentialExecutor schedules an `@once` synthetic two-task DAG
in a fresh owned HOME/SQLite directory. The second task writes a three-record toy
manifest. No MOBA pipeline, cloud service, recurring uptime or production claim.

The controller waits at most 120 seconds for the DAG after initialization and
then cleans up the scheduler and observed descendants by PID and creation time.
The CI job also has an eight-minute outer deadline. This is bounded process
cleanup evidence, not proof about unobserved processes or power-loss behavior.
Existing paths are refused. Failure logs and last metadata observation are kept;
`output.json` is written only after successful DAG checks and owned cleanup.

Run on Linux in the constrained optional Airflow runtime:

```sh
python experiments/scheduler_probe.py --output /tmp/new-scheduler-probe
```

No manual trigger or `DAG.test` is used. Earlier macOS service probes timed out;
their precise underlying stall cause was not established. Existing main-branch
`DAG.test` results remain separate from this experiment.
