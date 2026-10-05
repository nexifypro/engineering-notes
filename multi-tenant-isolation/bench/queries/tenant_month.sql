SELECT sum(amount_cents) FROM invoices WHERE tenant_id = current_setting('app.tenant_id')::uuid AND issued_on >= date '2026-09-01' AND issued_on < date '2026-10-01';
