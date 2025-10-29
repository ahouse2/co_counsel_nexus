variable "project" {
  description = "Project slug used for naming resources."
  type        = string
  default     = "ninth-octopus-mitten"
}

variable "environment" {
  description = "Environment identifier."
  type        = string
  default     = "enterprise"
}

variable "region" {
  description = "AWS region for deployment."
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Optional additional tags."
  type        = map(string)
  default     = {}
}

variable "oidc_provider_arn" {
  description = "EKS OIDC provider ARN for IRSA (leave blank for account-root access)."
  type        = string
  default     = ""
}

variable "service_account_namespace" {
  description = "Namespace of the Helm service account."
  type        = string
  default     = "default"
}

variable "service_account_name" {
  description = "Name of the Helm service account."
  type        = string
  default     = "full-stack"
}
