# First release plan

Interfaces: `generate_fixture(seed: int = 7) -> dict`; `run_pipeline(data: dict, as_of: str) -> dict[str, list[dict]]`; `write_reports(metrics, output: Path)`; CLI `moba-lab generate --output fixture.json --seed 7` and `moba-lab run --input fixture.json --as-of 2026-01-08 --output reports`.

1. Write independent fixtures and expected-value tests for exact duplicate handling, UTC dates, D1/D7 eligibility, grains, revenue, repeatability and invalid input. Observe RED before implementing.
2. Implement validated typed raw tables, SQL staging/facts/marts, deterministic generator, CSV/HTML CLI. Run full suite and demo.
3. Write metric dictionary, architecture, setup, honest verification and CI. Coordinator reviews and handles Git/publication.

Pre-flight: generator produces the same JSON table contract consumed by pipeline; SQL marts return dictionaries consumed by CSV/HTML reporting. No interface conflict.
Ruling: do not use Git-dependent execution helper scripts or commits inside this project because coordinator explicitly owns Git operations. Record evidence here instead.
Ruling: raw fixtures use JSON records, enabling explicit types and null/error cases; CSV is the analytical export format. No dbt layer in first release.

Execution evidence:
- Initial independent suite: 9 assertion failures because pipeline absent (RED).
- Implementation: 9 tests passed; test-only unclosed-file warning corrected.
- Added strict observation-date regression: 12 tests, 1 failed because Python accepts compact ISO dates. Root cause: `date.fromisoformat` is permissive. Enforce canonical round-trip format; full suite 12/12 GREEN.
- Additional negative and partial-window checks exercise current validated behavior.
- Demo exported six CSV marts, metadata and HTML. Final independent review belongs to coordinator; no subagent or Git action created here.
