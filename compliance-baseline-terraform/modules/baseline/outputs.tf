output "audit_bucket" {
  value = aws_s3_bucket.audit.bucket
}

output "cloudtrail_arn" {
  value = aws_cloudtrail.account.arn
}

output "config_recorder" {
  value = aws_config_configuration_recorder.account.name
}

output "security_hub_standards" {
  value = [for s in aws_securityhub_standards_subscription.standards : s.standards_arn]
}

output "backup_vault" {
  value = aws_backup_vault.primary.name
}
