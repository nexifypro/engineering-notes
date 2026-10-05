# Platform ownership matrix

The list nobody draws until the week of transfer. Fill it in month one, review it monthly, and
treat any row with the vendor in the Owner column as a transfer blocker.

| Asset | Current owner | Target owner | Admin accounts today | Billing account | Transfer action | Done |
|-------|---------------|--------------|----------------------|-----------------|-----------------|------|
| Cloud organisation / management account | | Client | | | Move root email and MFA to client; remove vendor org admins | |
| Each cloud account / project / subscription | | Client | | | Reassign owners; rotate access keys issued to vendor staff | |
| Identity provider (SSO) tenant | | Client | | | Client owns global admin; vendor users become guests or are removed | |
| Source control organisation | | Client | | | Transfer ownership; vendor engineers become outside collaborators with expiry | |
| CI/CD (runners, pipelines, secrets) | | Client | | | Re-issue secrets; move self-hosted runners to client accounts | |
| Container / artifact registries | | Client | | | Re-point pipelines; remove vendor push credentials | |
| DNS and domain registrations | | Client | | | Registrar account in client's name; transfer locks and contacts | |
| TLS certificates and ACME accounts | | Client | | | Re-issue under client-owned ACME account or ACM | |
| Secrets manager / vault | | Client | | | Rotate everything the vendor could read; audit access | |
| Signing keys (code, mobile, packages) | | Client | | | Generate new keys under client control where re-signing is possible; escrow otherwise | |
| App Store / Play Console accounts | | Client | | | Transfer apps to client developer accounts | |
| Observability (metrics, logs, APM, error tracking) | | Client | | | Org ownership and billing to client; remove vendor admins | |
| Pager / on-call tool | | Client | | | Rota and admin to client | |
| Third-party SaaS (email, payments, analytics, CRM) | | Client | | | API keys rotated; owners reassigned | |
| Data warehouse / BI | | Client | | | Owner and billing to client; service accounts rotated | |
| Vendor contracts and support plans | | Client | | | Novate or re-sign in the client's name | |
| Documentation wiki | | Client | | | Export, import, verify links | |
| Shared mailboxes and distribution lists | | Client | | | Re-create under client domain; redirect | |
