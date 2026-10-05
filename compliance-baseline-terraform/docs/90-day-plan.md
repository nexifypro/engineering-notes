# 90 days to SOC 2 Type I readiness (infrastructure track)

Assumes a single AWS organisation, an identity provider in place, and a named control owner.
The people and vendor tracks (policies, onboarding, vendor reviews, risk assessment) run in
parallel and are where a compliance platform earns its fee.

## Days 1–15 · Decide and baseline
- Pick the audit window, the trust services categories (Security plus Availability and Confidentiality are typical for SaaS) and whether HIPAA applies.
- Sign the AWS BAA in Artifact if PHI will be processed; list the HIPAA-eligible services you use.
- Apply the baseline module to every account: audit bucket, CloudTrail, Config, GuardDuty, Security Hub standards, Access Analyzer, Backup, account guardrails.
- Run `scripts/export-evidence.sh` once; file it as the "before" snapshot.

## Days 16–45 · Close the findings that matter
- Work the Security Hub failed controls by severity; accept the rest in writing with an owner and a date.
- Turn on MFA for every human identity; eliminate long-lived access keys or rotate and inventory them.
- Tag data stores with a classification; attach the daily backup plan by tag; run one restore and keep the job id.
- Put branch protection and Checkov on the infrastructure repositories; from here, every change is reviewed.

## Days 46–75 · Make evidence routine
- Schedule the evidence export monthly; store output in the audit bucket under a dated prefix.
- Write the five auditor narratives that reference the exports: access, change, logging and monitoring, backup and recovery, encryption.
- Run an access review from the IAM credential report and Identity Center assignments; record who reviewed what.
- Hold one incident drill using a GuardDuty finding; keep the ticket and the timeline.

## Days 76–90 · Readiness review
- Walk the crosswalk with the auditor-to-be: for each row, show the Terraform, the live evidence file, and the owner.
- Fix drift the review uncovers; re-export.
- Agree the Type I date. The same exports, taken monthly, become the Type II operating-effectiveness evidence.

## What cannot be automated
Risk assessment, policy approval, security awareness training, vendor management, background
checks, incident response decisions, and the access review judgement itself. Budget people time for
these; the module removes the screenshot hunt, not the responsibility.
