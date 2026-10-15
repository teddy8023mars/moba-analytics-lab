# Local artifact verification plan

Goal: give consumers of the existing local Airflow published.json a read-only CLI that verifies artifact bytes and declared summaries before use. Existing synthetic dashboards and publisher output stay unchanged.

Acceptance: `moba-lab verify --manifest PATH` exits0 with a JSON verified report for a matching manifest; exits2 with a useful error for missing/changed files, invalid JSON/schema/hash, mismatched counts/revenue, unsafe filename or symlink target. Read metrics bytes once for both SHA256 and parsing. Require all six known mart arrays of objects, nonnegative integer counts and revenue; reject booleans as numbers. Check file basename only (no separators, dot paths or absolute paths); reject symlink metrics. No output writes.

Limits: local owned artifacts only. An editable unsigned manifest is not authentication; a coordinated edit of data and manifest can pass. This does not re-run business quality checks, prove upstream completeness, lock files after verification, prevent adversarial filesystem races, or deploy a scheduler/cloud service. Existing local DAG still owns metric quality before publication.

Files: src/moba_lab/artifacts.py verifies a manifest; src/moba_lab/cli.py adds verify branch; tests/test_artifacts.py covers real fixture files, mutations and actual CLI exits; tests/test_airflow_demo.py verifies the actual native DAG output as a consumer. docs/artifact-verification.md explains commands/evidence/limits; README adds a link below existing preview.

- [x] Establish clean baseline in existing optional dbt environment.
- [x] Write expected-behavior tests, observe actual failures for absent verify command.
- [x] Implement minimal verifier/API and CLI; run focused and complete tests.
- [x] Consume real Airflow clean/transient manifests and reject tampering; run optional integration.
- [x] Record actual output, preserve original showcase, independent review.
- [ ] Commit/push personal repository; check exact-commit remote CI and Pages before declaring complete.

Execution is already authorized by the hourly personal-project sprint; use existing nested-repository manual worktree fallback (app root is not a Git checkout). No additional approval requested. No new dependency or paid service.
