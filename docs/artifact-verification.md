# Verify a local published artifact before consuming it

The optional Airflow demo already produces a local `published.json` with a
SHA256 digest, row counts and revenue total. Consumers can now check the referenced
file before using it, without importing Airflow:

```sh
moba-lab verify --manifest .airflow-output/demo-1/clean/artifacts/published.json
```

Install the base package as described in the README first. Exit **0** emits a JSON
report with `status=verified`, the SHA256, six row counts and revenue in cents.
Exit **2** emits an error on stderr with no success JSON. The command writes no
files. Paths are resolved relative to the manifest's directory, independent of
the caller's current working directory. The manifest must reference one local
basename; traversal, absolute paths, either slash separator and symlink metrics
files are rejected. Regular file-read errors also fail explicitly.

The verifier reads metrics bytes once, compares their digest, parses the same
bytes as UTF-8 JSON, and checks all six mart arrays against declared row counts.
Revenue is the sum of nonnegative integer `revenue_cents` in the monetization
mart; booleans do not count as integers. Invalid JSON, duplicate JSON keys,
nonfinite JSON constants, malformed manifest fields, count disagreement and
revenue disagreement fail explicitly. Other individual metric fields are not
revalidated by this consistency check.

## Actual evidence

[Captured successful verification](artifact-verification-output.json) consumes the
retained real clean Airflow demo output (synthetic seed7, as-of2026-01-14):
101 user-days, 14 DAU dates, 8 retention rows, 3 heroes, 12 players, 4 payment dates
and **1,396 fictional cents**. Its recorded digest is
`8eb6fabf1da5df5718d1b6abb739ba1baca3d7101ea25d4e9ea0127225db57c3`.
The local owned run directory itself is not included in the repository; reproduce
it using [the Airflow runner](airflow.md).

Seven new test methods exercise real files and CLI exit codes, including missing or
modified files, malformed JSON/schema, unsafe paths and symlinks, boolean counts,
summary disagreements, and matching-hash but malformed metric structures. The
existing native Airflow integration test now consumes actual clean and transient
manifests, then appends a byte to each metrics file and confirms verification
fails. The intentionally bad-metrics scenario still publishes no manifest.

Observed test-first failure: [RED log](artifact-red.txt), six tests with22 failing
assertions/subcases because the `verify` command did not exist. After implementation:
[optional dbt environment](artifact-dbt-test-output.txt) and
[optional Airflow environment](artifact-airflow-test-output.txt) each discover37
methods; each skips the other optional integration(s). Together they exercise all37
unique methods. This is local Python3.12 evidence; exact-commit remote results must
be checked after publication, not inferred from these logs. Review found uncaught deeply nested JSON and exponent-overflow numeric input; [regression RED log](artifact-review-red.txt) records three failures before decoder normalization. The final suites include the fixes and duplicate-key coverage. Existing14 interactive
showcase snapshots regenerate unchanged.

## Limits

This is consistency against an **unsigned, locally trusted manifest**. Anyone able
to replace both data and manifest can generate a new matching digest; this is not
authentication, signing or an authorization boundary. It does not prove source
completeness, business metric correctness, cohort maturity or a production SLA.
The Airflow gate still owns the pre-publication business checks described in its
guide. Counts alone cannot detect substitutions with the same number of rows.

There is no filesystem locking, adversarial race protection or promise that the
file remains unchanged after verification. Passing JSON is only a result about
the bytes read in that invocation. No cloud storage, scheduler deployment,
distributed executor or durable power-loss guarantee is added. The publisher and
existing dashboards are unchanged.
