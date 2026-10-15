# Optional S3 infrastructure configuration and mock-plan verification

Implements root PLAN.md's reviewed17:41design. Local Terraform1.12.2/AWS5.100.0,
no liveAWScredentials/API-backedplan/apply/resources. Tests first, provider schema
validation and explicit mock-provider command=plan only. Six planned resources:
bucket/force_destroyfalse, fourpublicblocks, AES256 encryption, Enabledversioning,
BucketOwnerEnforced and TLS-deny policy. Output reader-policyJSON only: prefix-scoped
ListBucket/GetObject, noIAMresource/role/key/upload/backend/lifecycleexpiration.
Requiredrestrictedbucketname/singleprefixsegment, Singapore-only region.

Files infra/s3-snapshot/*.tf/tests/*.tftest.hcl/lockfile/gitignore/README;
scripts/check_s3_infra.py isolates cloud/TFsettings inownedtemporaryHOME, checks
pinnedversion, runsfmt/init-backendfalse/validate/mocktest and saveslogs/summary
underfreshoutput. DedicatedCIjob usespinnedCLI/noAWSsecrets. Pythonunit testcovers
actualenvironment-sanitizingboundary withoutTerraformdependency.

Acceptance eightTerraformruns: guardrails/TLSdeny/readerpolicy/customprefix,
invalidbucket/wildcard/root/traversalprefix. ObserveRED missingmodule, finalGREEN,
then mutate a public-access safety flag and observe assertionfailure/restoredGREEN.
Realtools/output, notsource-string tests. Reviewactualclaims/code, preservevisuals,
personalpublishandcheckexactcommitCI/Pages. MockassertionsdonotproveAWSruntimeIAM
orclouddeployment; noresourcescreatedandnoresume/masteryclaim.
