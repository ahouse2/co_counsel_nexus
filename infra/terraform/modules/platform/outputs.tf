output "documents_bucket" {
  description = "S3 bucket name for document storage."
  value       = aws_s3_bucket.documents.bucket
}

output "graphs_bucket" {
  description = "S3 bucket name for graph exports."
  value       = aws_s3_bucket.graphs.bucket
}

output "telemetry_bucket" {
  description = "S3 bucket name for telemetry archives."
  value       = aws_s3_bucket.telemetry.bucket
}

output "neo4j_secret_arn" {
  description = "Secrets Manager ARN containing the Neo4j password."
  value       = aws_secretsmanager_secret.neo4j.arn
}

output "grafana_secret_arn" {
  description = "Secrets Manager ARN containing the Grafana admin password."
  value       = aws_secretsmanager_secret.grafana.arn
}

output "api_secret_arn" {
  description = "Secrets Manager ARN containing the API JWT secret."
  value       = aws_secretsmanager_secret.api.arn
}

output "service_account_role_arn" {
  description = "IAM role ARN bound to the Kubernetes service account."
  value       = aws_iam_role.service_account.arn
}
