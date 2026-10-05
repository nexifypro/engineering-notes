variable "name_prefix" {
  description = "Prefix for named resources, e.g. acme-prod."
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for the CloudTrail log group. HIPAA documentation retention is 6 years; audit log retention is set by your policy."
  type        = number
  default     = 400
}

variable "audit_bucket_retention_days" {
  description = "Days to keep CloudTrail and Config objects in S3 before expiry (Object Lock retention is separate and shorter by default)."
  type        = number
  default     = 2557 # 7 years
}

variable "object_lock_days" {
  description = "Compliance-mode Object Lock retention for audit objects. Nobody, including the root user, can delete them earlier."
  type        = number
  default     = 365
}

variable "enable_security_hub_standards" {
  description = "Security Hub standards to subscribe to (ARN suffixes under the standards path)."
  type        = list(string)
  default = [
    "aws-foundational-security-best-practices/v/1.0.0",
    "cis-aws-foundations-benchmark/v/3.0.0",
  ]
}

variable "conformance_pack_templates" {
  description = "Map of conformance pack name to the URL of its template body (AWS sample templates). Empty map disables."
  type        = map(string)
  default = {
    "hipaa-security" = "https://raw.githubusercontent.com/awslabs/aws-config-rules/master/aws-config-conformance-packs/Operational-Best-Practices-for-HIPAA-Security.yaml"
  }
}

variable "backup_schedule" {
  description = "Cron for the daily AWS Backup rule (UTC)."
  type        = string
  default     = "cron(0 3 * * ? *)"
}

variable "backup_retention_days" {
  type    = number
  default = 35
}

variable "password_policy" {
  description = "IAM account password policy for the few humans who still have console passwords."
  type = object({
    minimum_length   = number
    max_age_days     = number
    reuse_prevention = number
  })
  default = { minimum_length = 14, max_age_days = 90, reuse_prevention = 24 }
}

variable "tags" {
  type    = map(string)
  default = {}
}
