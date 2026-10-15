# S3 snapshot configuration — mocked plans only

This optional infrastructure-as-code exercise defines a private destination for
synthetic Parquet snapshots. **It has not been deployed to AWS.** All recorded
Terraform tests use a mocked AWS provider and `command = plan`; no AWS credentials,
API-backed plan, apply, upload or resource creation was performed. There is no IAM
role or policy deployment. The earlier [Parquet dataset](../../docs/parquet.md)
remains local; this module does not upload it.

## Reproduce the checks

Install Terraform **1.12.2** and Python3.11+; the committed lockfile pins AWS
provider **5.100.0**. These are reproducibility pins, not a latest-version claim.
From the repository root:

```sh
python3 scripts/check_s3_infra.py --output .s3-checks/run-1
```

Use a new evidence directory. The wrapper copies configuration to an owned
temporary directory, replaces HOME/CLI configuration, removes inherited AWS/TF
settings, points shared credentials/config to nonexistent owned paths and disables
EC2 metadata. It does not inspect or change your cloud account settings. An
optional `--plugin-cache PATH` can reuse an existing Terraform provider cache;
provider files are software dependencies, not credentials.

Actual command sequence: Terraform version, fmt-check, init with backend disabled
and read-only lockfile, validate, then test. Init needs network access to the
Terraform registry when the provider is not cached. The tests use mock-provider
plans; the wrapper requires all eight acceptance runs to pass, refusing an empty
test run. Logs and summary.json go to the requested directory, never Terraform
state. The dedicated CI job has no cloud credentials and uploads only that evidence.

## What the plan defines

| Configuration | Intended behavior checked in the mocked plan |
| --- | --- |
| S3 bucket | `force_destroy=false`; does not authorize deleting nonempty data |
| Public-access block | All four block/ignore/restrict flags enabled |
| Default encryption | AES256 (SSE-S3); no KMS key resource |
| Versioning | Enabled; no expiration rule or deletion of old versions |
| Ownership | BucketOwnerEnforced; no ACL resource |
| Bucket policy | Explicit deny for non-TLS bucket/object requests |
| Reader policy output | JSON document allowing ListBucket only for `snapshots/*` and GetObject only under `snapshots/`; no Put/Delete/admin permissions |

The required illustrative bucket name uses 3–63 lowercase alphanumeric/hyphen
characters and alphanumeric endpoints; dots are excluded. This does not check
global name availability. The prefix is one lowercase alphanumeric/underscore/
hyphen segment with a trailing slash; empty, root, wildcard and traversal prefixes
are rejected. Region is restricted to **ap-southeast-1**, ordinary AWS partition.

A client using the reader document would need to list with a prefix such as
`snapshots/`; root listing is not granted. This unattached JSON document does not
grant anyone real access. Other policies, account rules and explicit denies are
not evaluated by these mocked tests.

## Actual verification evidence

- [Command/exit summary](../../docs/s3-infra-output.json): Terraform1.12.2, format,
  init, validate and mock-test all succeeded.
- [Eight actual mock-plan results](../../docs/s3-infra-test-output.txt): guardrails,
  TLS deny, reader scope, custom prefix, invalid bucket and wildcard/root/traversal
  prefix rejection.
- [Observed failure before implementation](../../docs/s3-red-test.txt): referenced
  resources were not yet defined.
- [Safety mutation rejected](../../docs/s3-mutation-red.txt): changing
  block_public_policy to false fails the guardrails assertion; restored
  configuration then passes all eight runs.
- [Python regression suite](../../docs/s3-core-test-output.txt):44 discovered
  methods, three optional integrations skipped in the base environment. The new
  test verifies inherited dummy credentials and Terraform overrides are removed
  from the actual child-environment builder without modifying the caller's data.

Mocks use the real provider schema, but computed resource identifiers can be fake.
They are not published here as live AWS identifiers. Terraform's test teardown
messages refer to mock framework cleanup, not real cloud deletion. Exact-commit CI
must be checked after publication; local results do not establish remote success.

## Limits and next steps

These are configuration/plan checks, not deployed IAM authorization tests,
cloud-operational experience, a full data lake, or production security assurance.
There is no remote backend, multi-user state locking, ingestion service, catalog,
S3 object consistency test, network benchmark, lifecycle/cost management or incident
response demonstration. Versioning without an expiration policy can retain data
and incur storage costs if someone later deploys this configuration.

This sprint executes no real plan/apply/destroy. Any later live deployment requires
separate user authorization for the account, resources and costs; this README does
not ask for that approval or claim deployment readiness.

References: [Terraform provider mocking](https://developer.hashicorp.com/terraform/language/tests/mocking),
[pinned AWS provider documentation](https://github.com/hashicorp/terraform-provider-aws/tree/v5.100.0/website/docs/r).
