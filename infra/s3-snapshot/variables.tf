variable "bucket_name" {
  type        = string
  description = "Required illustrative name; global AWS availability is not checked."
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Use 3-63 lowercase alphanumeric/hyphen characters with alphanumeric endpoints; dots are excluded in this exercise."
  }
}
variable "snapshot_prefix" {
  type        = string
  default     = "snapshots/"
  description = "A single bounded prefix segment, including trailing slash."
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9_-]*/$", var.snapshot_prefix))
    error_message = "Use one lowercase alphanumeric/underscore/hyphen segment followed by slash, with no wildcards or traversal."
  }
}
variable "region" {
  type        = string
  default     = "ap-southeast-1"
  description = "This bounded example targets the ordinary AWS partition in Singapore."
  validation {
    condition     = var.region == "ap-southeast-1"
    error_message = "This exercise is scoped to ap-southeast-1 only."
  }
}
