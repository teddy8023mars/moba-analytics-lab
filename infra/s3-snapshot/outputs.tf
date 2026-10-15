output "reader_policy_json" {
  description = "Illustrative policy document only; no IAM policy or role is created."
  value       = jsonencode(local.reader_policy)
}
