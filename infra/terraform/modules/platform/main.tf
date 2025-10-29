locals {
  name_prefix         = "${var.project}-${var.environment}"
  tags_base           = {
    Project     = var.project
    Environment = var.environment
    Region      = var.region
  }
  tags                = merge(local.tags_base, var.tags)
  oidc_provider_host  = var.oidc_provider_arn != "" ? regexreplace(var.oidc_provider_arn, "arn:aws:iam::[0-9]+:oidc-provider/", "") : ""
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "documents" {
  bucket        = "${local.name_prefix}-documents"
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    id     = "expire-old-objects"
    status = "Enabled"
    expiration {
      days = var.backup_retention_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != "" ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn != "" ? var.kms_key_arn : null
    }
  }
}

resource "aws_s3_bucket" "graphs" {
  bucket        = "${local.name_prefix}-graphs"
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_versioning" "graphs" {
  bucket = aws_s3_bucket.graphs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "graphs" {
  bucket = aws_s3_bucket.graphs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != "" ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn != "" ? var.kms_key_arn : null
    }
  }
}

resource "aws_s3_bucket" "telemetry" {
  bucket        = "${local.name_prefix}-telemetry"
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_versioning" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != "" ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn != "" ? var.kms_key_arn : null
    }
  }
}

resource "random_password" "neo4j" {
  length  = 32
  special = true
}

resource "random_password" "grafana" {
  length  = 24
  special = true
}

resource "random_password" "api" {
  length  = 48
  special = true
}

resource "aws_secretsmanager_secret" "neo4j" {
  name = "${local.name_prefix}/neo4j-password"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "neo4j" {
  secret_id     = aws_secretsmanager_secret.neo4j.id
  secret_string = random_password.neo4j.result
}

resource "aws_secretsmanager_secret" "grafana" {
  name = "${local.name_prefix}/grafana-admin"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "grafana" {
  secret_id     = aws_secretsmanager_secret.grafana.id
  secret_string = random_password.grafana.result
}

resource "aws_secretsmanager_secret" "api" {
  name = "${local.name_prefix}/api-jwt"
  tags = local.tags
}

resource "aws_secretsmanager_secret_version" "api" {
  secret_id     = aws_secretsmanager_secret.api.id
  secret_string = random_password.api.result
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  dynamic "statement" {
    for_each = var.oidc_provider_arn != "" ? [1] : []
    content {
      effect = "Allow"
      actions = ["sts:AssumeRoleWithWebIdentity"]
      principals {
        type        = "Federated"
        identifiers = [var.oidc_provider_arn]
      }
      condition {
        test     = "StringEquals"
        variable = "${local.oidc_provider_host}:sub"
        values   = ["system:serviceaccount:${var.service_account_namespace}:${var.service_account_name}"]
      }
    }
  }
}

data "aws_iam_policy_document" "permissions" {
  statement {
    effect = "Allow"
    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.documents.arn,
      aws_s3_bucket.graphs.arn,
      aws_s3_bucket.telemetry.arn
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:GetObjectVersion",
      "s3:DeleteObjectVersion"
    ]
    resources = [
      "${aws_s3_bucket.documents.arn}/*",
      "${aws_s3_bucket.graphs.arn}/*",
      "${aws_s3_bucket.telemetry.arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.neo4j.arn,
      aws_secretsmanager_secret.grafana.arn,
      aws_secretsmanager_secret.api.arn
    ]
  }
}

resource "aws_iam_role" "service_account" {
  name               = "${local.name_prefix}-platform"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = local.tags
}

resource "aws_iam_policy" "service_account" {
  name   = "${local.name_prefix}-platform"
  policy = data.aws_iam_policy_document.permissions.json
}

resource "aws_iam_role_policy_attachment" "service_account" {
  role       = aws_iam_role.service_account.name
  policy_arn = aws_iam_policy.service_account.arn
}

resource "aws_s3_bucket_lifecycle_configuration" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id
  rule {
    id     = "expire-telemetry"
    status = "Enabled"
    expiration {
      days = var.backup_retention_days
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "graphs" {
  bucket = aws_s3_bucket.graphs.id
  rule {
    id     = "expire-graphs"
    status = "Enabled"
    expiration {
      days = var.backup_retention_days
    }
  }
}
