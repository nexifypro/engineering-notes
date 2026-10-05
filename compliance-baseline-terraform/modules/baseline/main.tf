# Compliance baseline: the infrastructure controls behind SOC 2 CC6/CC7/CC8/A1 and
# HIPAA §164.312 that can be implemented once and proven continuously.
# Each resource block names the criteria it supports; see ../../crosswalk.csv for the mapping.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.region
  tags       = merge({ ManagedBy = "terraform", Baseline = "compliance" }, var.tags)
}

# ---------------------------------------------------------------------------
# Audit storage: one bucket, versioned, encrypted, Object Lock, no public access.
# SOC 2 CC7.2 / CC6.1 · HIPAA 164.312(b) audit controls, 164.312(c)(1) integrity
# ---------------------------------------------------------------------------
resource "aws_kms_key" "audit" {
  description             = "${var.name_prefix} audit logs"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  tags                    = local.tags
}

resource "aws_kms_alias" "audit" {
  name          = "alias/${var.name_prefix}-audit"
  target_key_id = aws_kms_key.audit.key_id
}

data "aws_iam_policy_document" "audit_key" {
  statement {
    sid       = "AccountAdmin"
    actions   = ["kms:*"]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${local.account_id}:root"]
    }
  }
  statement {
    sid       = "CloudTrailEncrypt"
    actions   = ["kms:GenerateDataKey*", "kms:DescribeKey"]
    resources = ["*"]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com", "config.amazonaws.com", "logs.${local.region}.amazonaws.com"]
    }
  }
}

resource "aws_kms_key_policy" "audit" {
  key_id = aws_kms_key.audit.id
  policy = data.aws_iam_policy_document.audit_key.json
}

resource "aws_s3_bucket" "audit" {
  bucket              = "${var.name_prefix}-audit-${local.account_id}"
  object_lock_enabled = true
  tags                = local.tags
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.object_lock_days
    }
  }
  depends_on = [aws_s3_bucket_versioning.audit]
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.audit.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "audit" {
  bucket                  = aws_s3_bucket.audit.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    id     = "expire"
    status = "Enabled"
    filter {}
    expiration { days = var.audit_bucket_retention_days }
    noncurrent_version_expiration { noncurrent_days = 30 }
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}

data "aws_iam_policy_document" "audit_bucket" {
  statement {
    sid       = "CloudTrailAclCheck"
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.audit.arn]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com", "config.amazonaws.com"]
    }
  }
  statement {
    sid       = "CloudTrailWrite"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.audit.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com", "config.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.audit.arn, "${aws_s3_bucket.audit.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "audit" {
  bucket     = aws_s3_bucket.audit.id
  policy     = data.aws_iam_policy_document.audit_bucket.json
  depends_on = [aws_s3_bucket_public_access_block.audit]
}

# ---------------------------------------------------------------------------
# Account-wide guardrails
# SOC 2 CC6.1, CC6.6 · HIPAA 164.312(a)(1), 164.312(d)
# ---------------------------------------------------------------------------
resource "aws_s3_account_public_access_block" "account" {
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_account_password_policy" "strict" {
  minimum_password_length        = var.password_policy.minimum_length
  require_lowercase_characters   = true
  require_uppercase_characters   = true
  require_numbers                = true
  require_symbols                = true
  allow_users_to_change_password = true
  max_password_age               = var.password_policy.max_age_days
  password_reuse_prevention      = var.password_policy.reuse_prevention
  hard_expiry                    = false
}

resource "aws_ebs_encryption_by_default" "account" {
  enabled = true
}

resource "aws_accessanalyzer_analyzer" "account" {
  analyzer_name = "${var.name_prefix}-access-analyzer"
  type          = "ACCOUNT"
  tags          = local.tags
}

# ---------------------------------------------------------------------------
# CloudTrail: all regions, log file validation, encrypted, to the audit bucket and CloudWatch Logs
# SOC 2 CC7.2, CC7.3 · HIPAA 164.312(b)
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "/aws/cloudtrail/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.audit.arn
  tags              = local.tags
}

data "aws_iam_policy_document" "cloudtrail_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cloudtrail_logs" {
  name               = "${var.name_prefix}-cloudtrail-to-logs"
  assume_role_policy = data.aws_iam_policy_document.cloudtrail_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "cloudtrail_logs" {
  role = aws_iam_role.cloudtrail_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
    }]
  })
}

resource "aws_cloudtrail" "account" {
  name                          = "${var.name_prefix}-trail"
  s3_bucket_name                = aws_s3_bucket.audit.id
  s3_key_prefix                 = "cloudtrail"
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.audit.arn
  cloud_watch_logs_group_arn    = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
  cloud_watch_logs_role_arn     = aws_iam_role.cloudtrail_logs.arn
  tags                          = local.tags
  depends_on                    = [aws_s3_bucket_policy.audit]
}

# ---------------------------------------------------------------------------
# AWS Config: record everything, deliver to the audit bucket, evaluate conformance packs
# SOC 2 CC7.1, CC8.1 · HIPAA 164.308(a)(1)(ii)(D) information system activity review
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "config_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "config" {
  name               = "${var.name_prefix}-config"
  assume_role_policy = data.aws_iam_policy_document.config_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWS_ConfigRole"
}

resource "aws_config_configuration_recorder" "account" {
  name     = "${var.name_prefix}-recorder"
  role_arn = aws_iam_role.config.arn
  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "account" {
  name           = "${var.name_prefix}-delivery"
  s3_bucket_name = aws_s3_bucket.audit.id
  s3_key_prefix  = "config"
  s3_kms_key_arn = aws_kms_key.audit.arn
  depends_on     = [aws_config_configuration_recorder.account, aws_s3_bucket_policy.audit]
}

resource "aws_config_configuration_recorder_status" "account" {
  name       = aws_config_configuration_recorder.account.name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.account]
}

resource "aws_config_conformance_pack" "packs" {
  for_each      = var.conformance_pack_templates
  name          = "${var.name_prefix}-${each.key}"
  template_body = data.http.conformance_pack[each.key].response_body
  depends_on    = [aws_config_configuration_recorder_status.account]
}

data "http" "conformance_pack" {
  for_each = var.conformance_pack_templates
  url      = each.value
}

# ---------------------------------------------------------------------------
# Detection: GuardDuty and Security Hub standards
# SOC 2 CC7.2, CC7.3 · HIPAA 164.308(a)(6) security incident procedures (detective support)
# ---------------------------------------------------------------------------
resource "aws_guardduty_detector" "account" {
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  tags                         = local.tags
}

resource "aws_securityhub_account" "account" {
  enable_default_standards  = false
  control_finding_generator = "SECURITY_CONTROL"
  auto_enable_controls      = true
}

resource "aws_securityhub_standards_subscription" "standards" {
  for_each      = toset(var.enable_security_hub_standards)
  standards_arn = "arn:${data.aws_partition.current.partition}:securityhub:${local.region}::standards/${each.value}"
  depends_on    = [aws_securityhub_account.account]
}

# ---------------------------------------------------------------------------
# Backup: a daily plan with a locked vault, applied by tag
# SOC 2 A1.2, A1.3 · HIPAA 164.308(a)(7) contingency plan, 164.312(c)(1)
# ---------------------------------------------------------------------------
resource "aws_backup_vault" "primary" {
  name        = "${var.name_prefix}-vault"
  kms_key_arn = aws_kms_key.audit.arn
  tags        = local.tags
}

resource "aws_backup_vault_lock_configuration" "primary" {
  backup_vault_name  = aws_backup_vault.primary.name
  min_retention_days = 7
  max_retention_days = 3650
}

resource "aws_backup_plan" "daily" {
  name = "${var.name_prefix}-daily"
  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.primary.name
    schedule          = var.backup_schedule
    start_window      = 60
    completion_window = 360
    lifecycle { delete_after = var.backup_retention_days }
  }
  tags = local.tags
}

data "aws_iam_policy_document" "backup_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["backup.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "${var.name_prefix}-backup"
  assume_role_policy = data.aws_iam_policy_document.backup_assume.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_backup_selection" "tagged" {
  name         = "${var.name_prefix}-tagged"
  plan_id      = aws_backup_plan.daily.id
  iam_role_arn = aws_iam_role.backup.arn
  selection_tag {
    type  = "STRINGEQUALS"
    key   = "Backup"
    value = "daily"
  }
}
