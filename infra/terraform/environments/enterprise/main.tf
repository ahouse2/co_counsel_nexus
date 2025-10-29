terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5"
    }
  }
}

provider "aws" {
  region = var.region
}

module "platform" {
  source = "../../modules/platform"

  project                   = var.project
  environment               = var.environment
  region                    = var.region
  tags                      = var.tags
  backup_retention_days     = 30
  oidc_provider_arn         = var.oidc_provider_arn
  service_account_namespace = var.service_account_namespace
  service_account_name      = var.service_account_name
}

output "documents_bucket" {
  value       = module.platform.documents_bucket
  description = "Documents S3 bucket name"
}

output "graphs_bucket" {
  value       = module.platform.graphs_bucket
  description = "Graph export S3 bucket"
}

output "telemetry_bucket" {
  value       = module.platform.telemetry_bucket
  description = "Telemetry S3 bucket"
}

output "neo4j_secret_arn" {
  value       = module.platform.neo4j_secret_arn
  description = "Secrets Manager ARN for Neo4j"
}

output "service_account_role_arn" {
  value       = module.platform.service_account_role_arn
  description = "IAM role ARN to annotate the Helm service account"
}
