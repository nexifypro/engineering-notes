#!/usr/bin/env bash
# Exports point-in-time evidence for the infrastructure controls in ../crosswalk.csv to a dated
# folder of JSON/CSV files. Run it monthly (and the day before an audit); hand the folder to the
# auditor instead of screenshots. Read-only AWS calls only.
set -euo pipefail
OUT="evidence/$(date -u +%Y-%m-%d)"
mkdir -p "$OUT"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_REGION:-us-east-1}
echo "account=$ACCOUNT region=$REGION" > "$OUT/context.txt"

run() { # name, command...
  local name=$1; shift
  if "$@" > "$OUT/$name.json" 2> "$OUT/$name.err"; then rm -f "$OUT/$name.err"; echo "ok   $name"; else echo "FAIL $name (see $OUT/$name.err)"; fi
}

# CC6.1 / 164.312(a)
run iam-password-policy aws iam get-account-password-policy
run s3-account-public-access-block aws s3control get-public-access-block --account-id "$ACCOUNT"
run ebs-encryption-by-default aws ec2 get-ebs-encryption-by-default
# CC6.2 / 164.312(a)(2)(i) / 164.312(d)
aws iam generate-credential-report > /dev/null 2>&1 || true; sleep 2
aws iam get-credential-report --query Content --output text | base64 --decode > "$OUT/iam-credential-report.csv" && echo "ok   iam-credential-report"
run access-analyzers aws accessanalyzer list-analyzers
# CC7.1 / CC7.2 / 164.312(b)
run cloudtrail-trails aws cloudtrail describe-trails
for t in $(aws cloudtrail describe-trails --query 'trailList[].Name' --output text); do run "cloudtrail-status-$t" aws cloudtrail get-trail-status --name "$t"; done
run config-recorders aws configservice describe-configuration-recorder-status
run config-conformance-packs aws configservice describe-conformance-pack-status
for p in $(aws configservice describe-conformance-packs --query 'ConformancePackDetails[].ConformancePackName' --output text 2>/dev/null); do
  run "config-compliance-$p" aws configservice get-conformance-pack-compliance-summary --conformance-pack-names "$p"
done
run securityhub-standards aws securityhub get-enabled-standards
run securityhub-failed-controls aws securityhub get-findings --filters '{"ComplianceStatus":[{"Value":"FAILED","Comparison":"EQUALS"}],"RecordState":[{"Value":"ACTIVE","Comparison":"EQUALS"}]}' --max-items 500
run guardduty-detectors aws guardduty list-detectors
# A1.2 / 164.312(c)
run backup-vaults aws backup list-backup-vaults
run backup-plans aws backup list-backup-plans
run backup-jobs-30d aws backup list-backup-jobs --by-created-after "$(date -u -v-30d +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -d '30 days ago' +%Y-%m-%dT00:00:00Z)"
# KMS rotation for every customer key
for k in $(aws kms list-keys --query 'Keys[].KeyId' --output text); do
  if [ "$(aws kms describe-key --key-id "$k" --query 'KeyMetadata.KeyManager' --output text)" = "CUSTOMER" ]; then run "kms-rotation-$k" aws kms get-key-rotation-status --key-id "$k"; fi
done
echo "evidence written to $OUT"
