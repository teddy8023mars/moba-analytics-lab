provider "aws" {
  region = var.region
}
locals {
  bucket_arn = "arn:aws:s3:::${var.bucket_name}"
  tls_policy = {
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [local.bucket_arn, "${local.bucket_arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  }
  reader_policy = {
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = [local.bucket_arn]
        Condition = { StringLike = { "s3:prefix" = ["${var.snapshot_prefix}*"] } }
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${local.bucket_arn}/${var.snapshot_prefix}*"]
      }
    ]
  }
}
resource "aws_s3_bucket" "snapshot" {
  bucket        = var.bucket_name
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "snapshot" {
  bucket                  = aws_s3_bucket.snapshot.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "snapshot" {
  bucket = aws_s3_bucket.snapshot.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_versioning" "snapshot" {
  bucket = aws_s3_bucket.snapshot.id
  versioning_configuration {
    status = "Enabled"
  }
}
resource "aws_s3_bucket_ownership_controls" "snapshot" {
  bucket = aws_s3_bucket.snapshot.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
resource "aws_s3_bucket_policy" "snapshot" {
  bucket = aws_s3_bucket.snapshot.id
  policy = jsonencode(local.tls_policy)
}
