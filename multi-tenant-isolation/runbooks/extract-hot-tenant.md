# Runbook: move one tenant to its own database without changing the application

Use when a single tenant's load or contractual requirements outgrow the pool. The application
code does not change: the tenant's requests are routed to a different connection string.

1. **Create the target database** with the same schema (run `sql/001_schema.sql` there). Do not seed.
2. **Publish only that tenant's rows** on the source (PostgreSQL 15+ row filters):
   ```sql
   CREATE PUBLICATION hot_tenant FOR TABLE projects, invoices
     WHERE (tenant_id = '11111111-1111-1111-1111-111111111111');
   ```
   Replication connects as a role with `BYPASSRLS` (it must see the rows to copy them); grant it
   `SELECT` and nothing else.
3. **Subscribe from the target** with `copy_data = true`; wait for the initial sync, then confirm
   row counts per table match for that tenant.
4. **Cut over**: put the tenant in read-only mode at the application edge (a few seconds), wait for
   replication lag to reach zero, switch the tenant's routing entry to the new connection string,
   lift read-only.
5. **Verify** with the leak test pointed at the new database (tenant A should still see only
   tenant A) and a smoke test of the tenant's main flows.
6. **Clean up**: drop the subscription and publication, then delete the tenant's rows from the
   source inside a maintenance window, in batches, and `VACUUM`.

Rollback before step 4 is simply dropping the subscription. After step 4, reverse the routing
entry; writes made on the target in between must be reconciled, so keep the read-only window short.
