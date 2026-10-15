mock_provider "aws" {}
variables {
  bucket_name = "moba-synthetic-example"
}
run "guardrails" {
  command = plan
  assert {
    condition = (
      !aws_s3_bucket.snapshot.force_destroy &&
      aws_s3_bucket_public_access_block.snapshot.block_public_acls &&
      aws_s3_bucket_public_access_block.snapshot.block_public_policy &&
      aws_s3_bucket_public_access_block.snapshot.ignore_public_acls &&
      aws_s3_bucket_public_access_block.snapshot.restrict_public_buckets &&
      one(aws_s3_bucket_server_side_encryption_configuration.snapshot.rule).apply_server_side_encryption_by_default[0].sse_algorithm == "AES256" &&
      aws_s3_bucket_versioning.snapshot.versioning_configuration[0].status == "Enabled" &&
      aws_s3_bucket_ownership_controls.snapshot.rule[0].object_ownership == "BucketOwnerEnforced"
    )
    error_message = "Snapshot plan must retain destruction, public-access, encryption, versioning and ownership safeguards."
  }
}
run "tls_deny" {
  command = plan
  assert {
    condition = (
      length(jsondecode(aws_s3_bucket_policy.snapshot.policy).Statement) == 1 &&
      jsondecode(aws_s3_bucket_policy.snapshot.policy).Statement[0].Effect == "Deny" &&
      jsondecode(aws_s3_bucket_policy.snapshot.policy).Statement[0].Principal == "*" &&
      jsondecode(aws_s3_bucket_policy.snapshot.policy).Statement[0].Action == "s3:*" &&
      jsondecode(aws_s3_bucket_policy.snapshot.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false" &&
      toset(jsondecode(aws_s3_bucket_policy.snapshot.policy).Statement[0].Resource) == toset(["arn:aws:s3:::moba-synthetic-example", "arn:aws:s3:::moba-synthetic-example/*"])
    )
    error_message = "The policy must deny non-TLS requests for both bucket and objects."
  }
}
run "reader_scope" {
  command = plan
  assert {
    condition = (
      length(jsondecode(output.reader_policy_json).Statement) == 2 &&
      jsondecode(output.reader_policy_json).Statement[0].Effect == "Allow" &&
      toset(jsondecode(output.reader_policy_json).Statement[0].Action) == toset(["s3:ListBucket"]) &&
      toset(jsondecode(output.reader_policy_json).Statement[0].Resource) == toset(["arn:aws:s3:::moba-synthetic-example"]) &&
      toset(jsondecode(output.reader_policy_json).Statement[0].Condition.StringLike["s3:prefix"]) == toset(["snapshots/*"]) &&
      jsondecode(output.reader_policy_json).Statement[1].Effect == "Allow" &&
      toset(jsondecode(output.reader_policy_json).Statement[1].Action) == toset(["s3:GetObject"]) &&
      toset(jsondecode(output.reader_policy_json).Statement[1].Resource) == toset(["arn:aws:s3:::moba-synthetic-example/snapshots/*"])
    )
    error_message = "Reader document must grant only prefix-scoped ListBucket and GetObject."
  }
}
run "custom_prefix" {
  command = plan
  variables { snapshot_prefix = "lab-data/" }
  assert {
    condition = (
      toset(jsondecode(output.reader_policy_json).Statement[0].Condition.StringLike["s3:prefix"]) == toset(["lab-data/*"]) &&
      toset(jsondecode(output.reader_policy_json).Statement[1].Resource) == toset(["arn:aws:s3:::moba-synthetic-example/lab-data/*"])
    )
    error_message = "Custom prefix must change listing and object scopes together."
  }
}
run "invalid_bucket" {
  command = plan
  variables { bucket_name = "Bad_Bucket" }
  expect_failures = [var.bucket_name]
}
run "wildcard_prefix" {
  command = plan
  variables { snapshot_prefix = "*/" }
  expect_failures = [var.snapshot_prefix]
}
run "root_prefix" {
  command = plan
  variables { snapshot_prefix = "/" }
  expect_failures = [var.snapshot_prefix]
}
run "traversal_prefix" {
  command = plan
  variables { snapshot_prefix = "../" }
  expect_failures = [var.snapshot_prefix]
}
