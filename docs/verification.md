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
