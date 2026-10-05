# Ownership-readiness scorecard

Agree the thresholds at signing. Score every gate monthly from month one, in the same meeting as
the delivery review. Transfer starts when every gate is green for two consecutive months, not when
a calendar date arrives.

Scoring: **Green** meets threshold · **Amber** within reach next month with a named action · **Red** no plan.

| # | Gate | Threshold | Evidence | Owner |
|---|------|-----------|----------|-------|
| 1 | Bus factor | Every critical system has at least two people on the client side who have shipped a change to it in the last 90 days | Commit and deploy history by person | Client engineering lead |
| 2 | Deploy without the vendor | The client team has run a production deployment and a rollback end to end with no vendor engineer present | Deployment log with names | Client engineering lead |
| 3 | On-call | The client staffs the on-call rota; vendor engineers are escalation only, with a declining share each month | Rota, pager assignments, escalation count | Client ops lead |
| 4 | Runbooks | Every alert that paged in the last quarter has a runbook that a client engineer has used | Alert list cross-referenced with runbook links | Client ops lead |
| 5 | Incident ownership | The last two incidents were led and written up by client engineers | Postmortems with author names | Client engineering lead |
| 6 | Hiring pipeline | Open roles for the transferred team are owned, posted and interviewed by the client | Job postings, interview panel composition | Client HR + engineering lead |
| 7 | Access | The vendor holds no standing admin on cloud accounts, identity provider, source control, DNS, secrets or app stores; break-glass access is time-boxed and logged | Access review export | Client security owner |
| 8 | Knowledge | Architecture decisions, system map, data flows and vendor contracts are in the client's wiki and have been reviewed by a client engineer | Review sign-off list | Client engineering lead |
| 9 | Budget | Cloud and SaaS spend is billed to client-owned accounts and reviewed monthly by a client owner | Billing account ownership, review notes | Client finance + engineering lead |
| 10 | Velocity without the vendor | Throughput and change failure rate stayed within agreed bands during a two-week period with vendor engineers in observer mode | Delivery metrics for the trial window | Both |

## Agreed at signing

- Transfer trigger: all ten gates green for two consecutive months, or the contractual date, whichever comes first.
- If the date arrives with red gates: the named remediation plan per red gate, the cost of the extension, and who bears it.
- Vendor retention incentive: a success fee or holdback released at transfer, not a day rate that rewards delay.
