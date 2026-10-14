# MOBA Analytics Lab

A runnable Python + DuckDB + SQL lab for reasoning about event identity, fact grains and cohort observation windows.

**All data is fully synthetic. This is an AI-assisted personal educational project, not an employer implementation, production system or measured business impact.** Hero names and player IDs are fictional.

## Run locally

Requires Python 3.11 or 3.12. No cloud account, API key, database server or dbt setup is needed.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/moba-lab generate --output examples/fixture.json --seed 7
.venv/bin/moba-lab run --input examples/fixture.json --as-of 2026-01-14 --output examples/report
```

Open `examples/report/index.html` in a browser. Six CSV tables and `run.json` accompany the HTML. The checked-in example was produced with these commands. Run metadata declares the UTC observation day; `--as-of` means the input is complete through that day's end, rather than merely the latest event date. The caller must guarantee that completeness. Future events are filtered out of analytical facts.

The seed-7 example has 12 users, 102 raw logins, 10 matches, 40 player/match rows and 5 raw payments. Exact repeats reduce these to 101 user/day rows and 4 payment transactions. These are tiny demonstration fixtures, not a throughput benchmark.

## What the pipeline teaches

- Raw tables retain exact repeated events; staging removes repeats. Conflicting payloads for an identity fail rather than selecting an arbitrary row.
- UTC timestamps accept explicit offsets, then normalize to UTC. Naive timestamps, null keys, unknown references and events preceding signup fail explicitly.
- DAU and retention use a distinct login user/day fact. Repeated logins cannot inflate a retained-user count.
- D1/D7 are exact calendar-day retention. A cohort appears for an offset only when that offset is observable. A newer cohort is excluded, rather than treated as churn.
- Hero statistics use the player/match grain. A hero can have two appearances in one match, so player matches and distinct matches are separate measures. Payments are aggregated independently, preventing a player's multiple purchases from multiplying match facts.
- Currency amounts stay in integer cents. The fictional fixture assumes one currency; no currency conversion, refunds, taxes or net revenue are modeled.

## Structure

`src/moba_lab/models.sql` is the canonical, packaged SQL source. `pipeline.py` validates the table contract and executes it in an in-memory database. `fixtures.py` generates deterministic JSON records. `cli.py` exports CSV and escaped HTML. `tests/test_pipeline.py` uses independent hand-calculated fixtures rather than computing expected values with the implementation.

See [architecture](docs/architecture.md), [metric dictionary and input contract](docs/metrics.md), [actual verification](docs/verification.md), and [implementation plan](docs/implementation-plan.md).

## Scope

This release is a local full rebuild. It provides no real telemetry connector, incremental warehouse load, orchestration, dbt layer, query-performance evidence or production deployment. The validation checks event integrity, not full MOBA game rules: fixtures use four participants per match and do not model ranked rules or enforce balanced kill/death totals. Reports contain fictional metrics and establish no real business conclusions.

MIT licensed. Remote CI is configured for Python 3.11/3.12; its result must be checked after publication.
