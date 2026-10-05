\set id random(1, 1000)
SELECT amount_cents FROM invoices WHERE tenant_id = current_setting('app.tenant_id')::uuid AND id = (SELECT id FROM invoices_bench_ids WHERE n = :id);
