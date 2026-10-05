# Multi-tenant isolation with PostgreSQL row-level security

Code for the article **Tenant isolation belongs in the database, not the dashboard** on the
[NexifyPro blog](https://nexifypro.com/blog/tenant-isolation-belongs-in-the-database).

- `sql/` the schema: tenant-keyed tables, `FORCE ROW LEVEL SECURITY`, policies on
  `current_tenant()`, a `security_invoker` reporting view, an application role that cannot bypass
  RLS and a reporting role that can (and therefore must never be handed to a per-tenant consumer).
- `app/` a FastAPI service where no query filters by tenant. The tenant is resolved from the
  credential into a context variable and applied with `SET LOCAL` by a SQLAlchemy Session event,
  so every request, report and background job is covered. `jobs.py` shows the worker pattern.
- `tests/test_leak.py` the cross-tenant leak test: walks the route table, calls every route as
  tenant A with tenant B's ids, asserts 404s and no foreign rows; plus checks that writes cannot
  cross tenants, that a Session without a tenant refuses to run, and that the database enforces
  the rule even for raw queries.
- `prisma/tenant-extension.ts` the same pattern for Node with a Prisma client extension.
- `bench/pgbench.sh` measures what RLS costs on point lookups and per-tenant aggregates.
- `runbooks/extract-hot-tenant.md` moving one tenant to its own database with logical replication.

## Run it

```bash
# a local PostgreSQL 17 on port 5499 with a superuser named postgres and a database named tenants
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q                      # creates the schema and seed, runs the leak test
SECONDS_PER_RUN=15 bench/pgbench.sh
```

Tested on 2026-10-05 with PostgreSQL 17.11, Python 3.14, SQLAlchemy 2.0, FastAPI 0.11x.
