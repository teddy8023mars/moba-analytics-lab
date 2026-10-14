# Verification evidence

Executed locally on 2026-10-15 on macOS arm64 with Python 3.12.14 and DuckDB 1.4.3. No remote CI outcome is claimed. Commands below run from the project root; the bundled Python used to create virtual environments was `/Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`.

## Development install and tests

```sh
/Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple -e .
.venv/bin/python -m unittest discover -s tests -v
```

Results: installation exited 0; DuckDB 1.4.3 installed; **12 tests passed**, no warnings in final run. The original nine tests were written first and initially failed with `pipeline is not implemented`. A later strict-format regression failed because compact `20260108` was accepted; after canonical-date validation, the full suite passed.

Tests cover literal 50% D1/D7 retention, exclusion of unobservable/future cohorts, an earlier watermark excluding D7, UTC offset boundaries, exact repeated login/payment/participant events, no transaction-to-match multiplication, null keys, unknown users/matches, negative payments, naive timestamps, pre-signup events, conflicting duplicate identities, empty input, deterministic generation/rebuild and CLI CSV/HTML export. The CLI malformed-JSON subprocess exits **2** as expected.

## End-to-end synthetic demo

```sh
.venv/bin/moba-lab generate --output examples/fixture.json --seed 7
.venv/bin/moba-lab run --input examples/fixture.json --as-of 2026-01-14 --output examples/report
```

Both commands exited 0. Actual generator output:

```json
{"logins": 102, "matches": 10, "participants": 40, "payments": 5, "users": 12}
```

Actual report row counts:

```json
{"dau": 14, "hero_stats": 3, "monetization": 4, "player_stats": 12, "retention": 8, "user_day": 101}
```

There are 4 deduplicated payment transactions totaling **1,396 fictional cents**. The January 1 signup cohort has 3 users, D1 2/3 and D7 3/3 in this generated example. The separate hand-calculated test fixture has 2 users, D1 1/2 and D7 1/2.

A second run using the same generator seed produced byte-identical six CSV files and HTML. Checked-in fixture SHA-256: `50a5e5c2330265011c8b48fc7843db7035af58ef11f6e836f7c5484f051d13db`.

## Normal package installation

```sh
.venv/bin/python -m pip wheel --index-url https://pypi.org/simple --no-deps --wheel-dir .artifacts .
/Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv-wheel
.venv-wheel/bin/python -m pip install --index-url https://pypi.org/simple .artifacts/moba_analytics_lab-0.1.0-py3-none-any.whl
.venv-wheel/bin/python -m unittest discover -s tests -v
.venv-wheel/bin/moba-lab run --input examples/fixture.json --as-of 2026-01-14 --output .artifacts/wheel-report
```

Wheel build/install and installed CLI exited 0; **12 tests passed** in the non-editable wheel environment. SQL is included as package data and was exercised by that CLI. An initial wheel build used the machine's configured package mirror for build requirements; the final wheel build above explicitly used official PyPI. Runtime dependency installation explicitly used official PyPI in both environments.

## Limits of this evidence

Only local Python 3.12/macOS was executed here. GitHub Actions targets Ubuntu Python 3.11/3.12 but remote runs await publication. No benchmark, production reliability, real MOBA game validity or business effect is established. All data/metrics are synthetic. Full rebuild uses memory; input completeness is asserted by the caller; output-directory writes are not atomic. No dbt, cloud warehouse, incremental ingestion, observability service or live source connector is included.

## Optional dbt execution — 2026-10-15

Earlier sections describe the original pre-publication release. The optional dbt extension now runs locally on Python3.12.14 with dbt-core1.10.11, dbt-duckdb1.10.1 and DuckDB1.4.3. Full18-test suite (including one real multi-phase dbt integration test) passed: [test output](dbt-test-output.txt). [Observed summary](dbt-output.json) records13 built models,3 passing singular data tests, all six marts equal to canonical outputs at Jan14 and Jan08, one deliberate retention violation / test exit1, and restored build exit0. The actual CLI demo was run separately to retain evidence. Rebuilt14 showcase snapshots and confirmed docs/index.html, showcase-data.json and SVG unchanged. Remote results for this commit must be checked after publishing.

Remote first commit7a60212 exposed an optional-test discovery bug: the checked-in dbt/ folder satisfied find_spec as a namespace without dbt installed, so baseline jobs attempted a missing executable. Distribution metadata now requires both dbt-core and dbt-duckdb. Actual core-only local environment passes17 tests with1 skip: [output](dbt-base-test-output.txt); optional environment passes all18 with no skips: [output](dbt-test-output.txt). Dedicated CI checks dbt --version before the suite, so its own install cannot silently disappear. The first failed run remains historical evidence; check the corrective commit Actions result separately.

## Local benchmark extension — 2026-10-15

Three new tests first failed because the workload/benchmark tool was absent. Four-user literal expectations, invalid scales and a two-fresh-process CLI smoke test now pass. Actual three-sample workloads at100/1000/5000users generated docs/benchmark-output.json; timing boundaries and all samples in docs/benchmark.md. A separate actual EXPLAIN ANALYZE illustrates raw60→distinct56records. Full21-test optional environment suite passes (including dbt) in benchmark-test-output.txt; showcase regenerated unchanged. During the first full-suite run, the retained local dbt launcher pointed to a removed worktree and exited126. Reinstalled the same dbt-core1.10.11 using the normalized absolute runtime path; fresh full suite passed. This was local runtime repair, no project/core change. Remote CI must still be checked on the published commit.

## Optional stage timing — 2026-10-15

Three expected-result tests observed RED (missing keyword/CLI flag). Timings partition a successful pipeline through connection close; failed early validation and injected later SQL errors preserve the caller's prior dict. Full 24-test optional dbt suite passed in stage-profile-test-output.txt. Six fresh-process measurements at 1,000/5,000 users recorded all stage durations in stage-profile-output.json with independent correctness checks. Original 14 showcase snapshots regenerated without HTML/JSON/SVG changes. Reviewer found no blockers and suggested later-failure coverage, which was added before full verification. Remote CI for the published commit remains to be checked separately.

## Bounded parameter batching — 2026-10-15

Initial loader expected-behavior tests observed RED, then batch/value/duplicate/invalid-option assertions passed. Four new tests now include a real alternating-order comparison CLI smoke check. Twelve actual fresh-process samples (three reference/candidate pairs per 1,000/5,000 users) all pass independent workload checks and complete six-mart digest parity. Measured median elapsed reductions are 27.5%/28.9%; all samples and memory scope in load-comparison-output.json and batched-load.md. Candidate adopted as default after measurement. Full 28-test optional-dbt suite passed after default change; original 14-snapshot showcase regenerated unchanged. Review found no blockers and correctly required peak RSS to disclose result serialization/hash. Remote CI for this published commit must be checked separately.

## Optional Airflow execution — 2026-10-15

Pinned Airflow2.11.0 installed in a separate Python3.12 environment using official constraints; pip check clean. Initial expected integration test failed on missing runner, then actual DAG.test scenarios passed. Airflow performs the transient task retry natively with attempt sequence [1,2]; bad retained count fails validate_metrics and marks publish_local upstream_failed with no manifest. Wrapper now strips inherited Airflow config/context variables, supplies owned HOME/config/SQLite, verifies child isolation before Airflow import, and refuses existing scenario paths. Full Airflow-environment suite discovers30tests with dbt1skip; complementary dbt environment discovers30tests with Airflow2skip. Actual outputs in airflow-test-output.txt / airflow-dbt-compat-output.txt and airflow-output.json. Original14snapshot exporter regenerated unchanged. Independent review found no blockers, and explicit use_executor=False adopted. Dedicated remote Airflow CI job/versioncheck added; remote result must be checked after publication.
