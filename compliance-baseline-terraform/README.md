# Compliance baseline in Terraform

Code for the article **SOC 2 and HIPAA controls you can prove with Terraform, not screenshots** on
the [NexifyPro blog](https://nexifypro.com/blog/soc2-hipaa-controls-with-terraform).

- `modules/baseline/` the infrastructure controls as one module: KMS-encrypted audit bucket with
  Object Lock, multi-region CloudTrail with log file validation to S3 and CloudWatch Logs, AWS
  Config recorder with conformance packs, GuardDuty, Security Hub CSPM standards, IAM Access
  Analyzer, account-level S3 public access block, EBS default encryption, IAM password policy, AWS
  Backup with a locked vault. Each block is commented with the criteria it supports.
- `examples/single-account/` a root module that applies the baseline to one account.
- `crosswalk.csv` SOC 2 criteria and HIPAA §164.312 safeguards mapped to the AWS mechanism, the
  Terraform resource and the CLI query that produces the evidence.
- `scripts/export-evidence.sh` read-only export of that evidence to a dated folder.
- `docs/90-day-plan.md` the infrastructure track to Type I readiness.
- `.checkov.yaml` policy-as-code for the infrastructure repository itself.

```bash
cd examples/single-account
terraform init && terraform plan        # validated with plan; apply enables billable services
pip install checkov && checkov --config-file ../../.checkov.yaml
../../scripts/export-evidence.sh         # read-only, needs an AWS profile
```

Validated with `terraform validate` and `terraform plan` on 2026-10-05 (Terraform 1.15.8, AWS
provider 6.67). Applying enables AWS Config, GuardDuty and Security Hub, which are billed per
configuration item, per event and per check; see the article for the published rates. This is an
engineering baseline, not legal advice: confirm scope with your auditor.
