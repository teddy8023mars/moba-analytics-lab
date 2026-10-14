# Data engineering JD alignment

Checked 2026-10-15. This is a portfolio capability comparison, not a hiring score, seniority claim or proof of meeting a role's experience minimum. The first releases were built around the Meta Analytics target and common engineering fundamentals; they were not previously an exhaustive current-market JD comparison.

## Employer sources

- [Amazon Data Engineer II, 10542497, Hyderabad](https://www.amazon.jobs/en/jobs/10542497/data-engineer-ii): modeling/warehousing/ETL, reporting integrity and validation, self-service analytics; AWS preferred. Minimum 3+ years DE and 4+ years SQL. Employer page read with application link visible.
- [Amazon Data Engineer — AI/ML Products, 10572912, Beijing](https://www.amazon.jobs/en/jobs/10572912/data-engineer-ai-ml-products-aop-analytics-operations-and-programs): pipelines and analytics/ML data infrastructure, warehouses/lakes, governance/security, CI/CD and collaboration; cloud knowledge and 3+ years DE. Employer page read.
- [Grab Senior Data Engineer, 744000153988681, Jakarta](https://www.grab.careers/en/jobs/744000153988681/senior-data-engineer/): batch/event-driven pipelines, reliable metrics, data checks, AWS and Flink/Spark/Kafka/Airflow/Trino; 6+ years. Used to identify advanced stack gaps, not to suggest this senior vacancy is the user's present match.
- [Meta Singapore Data Engineer, Analytics, LinkedIn job4466993038](https://www.linkedin.com/jobs/view/4466993038/): primary preparation target, using the previously researched JD snapshot. Current availability not reverified in this audit; do not call it a newly confirmed live vacancy.

These examples span APAC but are not all Singapore jobs. Listings change; application eligibility and availability must be checked again before applying.

## Capability-to-evidence matrix

| JD capability | Current concrete evidence | Present limit | Next improvement |
|---|---|---|---|
| Python/SQL modeling, analytics | MOBA typed events → deduplicated staging → user-day/player-match facts → cohort/hero/payment marts; literal expected-value tests | DuckDB local full rebuild, tiny synthetic fixture | Executed dbt layer with documented grains and tests; query-plan analysis |
| ETL and data correctness | Versioned inserts/updates/deletes; target/checkpoint coupled in SQLite transaction; independent reconciliation | Synthetic source envelopes, no production connector/broker or distributed guarantee | Reproducible restart/crash experiment and bounded integration example |
| Data checks, integrity, validation | Six declarative CSV checks; clean/dirty data; error types and CI exit codes | Memory-based local files; no service or warehouse connector | Cross-project gate examples and larger declared-scale runs |
| Reporting, self-service consumption | HTML/CSV exports; interactive pages explain retention eligibility, failure recovery and violations | Recorded synthetic results; not deployed BI or backend service | Clickable dashboards linked from README; evidence and metric definitions beside visuals |
| CI/CD and version control | Actual GitHub CI on Python3.11/3.12, packaged CLI installation where configured | Checks/test pipeline; not cloud deployment infrastructure | Reproducible deployment/build jobs with transparent status |
| Airflow/orchestration | Professional experience exists separately | None of these first labs implements an Airflow deployment | Add one real, executable orchestration example only after current architecture is stable |
| AWS/data lake/security | No project evidence yet | No S3/Redshift/Glue/IAM infrastructure, no cloud deployment or governance service | Design reproducible optional cloud/infrastructure exercise; no paid resources without authorization |
| Spark/Kafka/Flink/distributed scale | No project evidence yet | Cannot infer from Python/DuckDB/SQLite tests | Pick one justified distributed scenario; do not add decorative stack names |
| Stakeholder impact/experience years | Professional employment, separately documented | Personal demos do not create employer impact or additional years | User walkthrough and honest personal-project resume bullets |

## Visual acceptance

Recruiter can understand each repository within one screen: project problem, actual result preview, live demo button, source/run entry. Visualizations use reproducible exported JSON, disclose synthetic data and recorded reference times, keep not-observable retention cells distinct from zero, retain tombstones in recovery snapshots, and do not sum overlapping violations into bad-row counts. Pages contain no paid dependency or company data. Visuals communicate the implementation rather than substitute for it.
