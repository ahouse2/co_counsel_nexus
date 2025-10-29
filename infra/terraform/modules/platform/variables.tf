variable "project" {
  description = "Project slug used for naming AWS resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment identifier (e.g., community, enterprise)."
  type        = string
}

variable "region" {
  description = "AWS region for provisioned resources."
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources."
  type        = map(string)
  default     = {}
}

variable "backup_retention_days" {
  description = "Lifecycle retention window for S3 backups (in days)."
  type        = number
  default     = 30
}

variable "kms_key_arn" {
  description = "Optional KMS key ARN for S3 server-side encryption."
  type        = string
  default     = ""
}

variable "oidc_provider_arn" {
  description = "OIDC provider ARN for EKS IRSA bindings."
  type        = string
  default     = ""
}

variable "service_account_namespace" {
  description = "Kubernetes namespace for the Helm release service account."
  type        = string
  default     = "default"
}

variable "service_account_name" {
  description = "Service account name requiring AWS access."
  type        = string
  default     = "full-stack"
}
