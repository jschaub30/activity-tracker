variable "region" {
  type        = string
  description = "Primary AWS region for DDB, Lambda, S3, SQS."
  default     = "us-west-2"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names."
  default     = "garmin-tracker"
}

variable "repo_name" {
  type        = string
  description = "Value of the repo tag (key: repo)."
  default     = "garmin-tracker"
}

variable "lambda_image_tag" {
  type        = string
  description = "ECR image tag for API and worker Lambdas."
  default     = "bootstrap"
}

variable "domain_name" {
  type        = string
  description = "Optional custom domain for CloudFront (empty = default CF domain)."
  default     = ""
}

variable "hosted_zone_id" {
  type        = string
  description = "Route53 hosted zone for domain_name (required when domain_name is set)."
  default     = ""
}

variable "price_class" {
  type        = string
  description = "CloudFront price class."
  default     = "PriceClass_100"
}

variable "enable_scheduled_sync" {
  type        = bool
  description = "Create EventBridge Scheduler to enqueue a daily sync-all."
  default     = false
}
