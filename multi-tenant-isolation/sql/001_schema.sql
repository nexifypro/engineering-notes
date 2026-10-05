-- Shared-schema multi-tenancy with row-level security.
-- Run as a superuser once. The application connects as app_user, which does not own the
-- tables and cannot bypass RLS.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE tenants (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE projects (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenants(id),
  name        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX projects_tenant_idx ON projects (tenant_id);

CREATE TABLE invoices (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenants(id),
  project_id  uuid NOT NULL REFERENCES projects(id),
  amount_cents bigint NOT NULL CHECK (amount_cents >= 0),
  status      text NOT NULL CHECK (status IN ('draft','sent','paid')),
  issued_on   date NOT NULL
);
CREATE INDEX invoices_tenant_issued_idx ON invoices (tenant_id, issued_on);

-- The tenant for the current transaction. current_setting(..., true) returns NULL when unset,
-- and NULL = anything is false, so a connection with no tenant sees nothing.
CREATE FUNCTION current_tenant() RETURNS uuid
  LANGUAGE sql STABLE PARALLEL SAFE
  RETURN nullif(current_setting('app.tenant_id', true), '')::uuid;

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;

CREATE POLICY projects_tenant_isolation ON projects
  USING (tenant_id = current_tenant())
  WITH CHECK (tenant_id = current_tenant());

CREATE POLICY invoices_tenant_isolation ON invoices
  USING (tenant_id = current_tenant())
  WITH CHECK (tenant_id = current_tenant());

-- A reporting view that respects the caller's policies (PostgreSQL 15+).
CREATE VIEW revenue_by_month WITH (security_invoker = true) AS
  SELECT tenant_id, date_trunc('month', issued_on)::date AS month, sum(amount_cents) AS revenue_cents
  FROM invoices WHERE status = 'paid'
  GROUP BY tenant_id, date_trunc('month', issued_on);

-- The application role: no table ownership, no BYPASSRLS, least privilege.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user LOGIN PASSWORD 'app_user' NOBYPASSRLS;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT ON tenants TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON projects, invoices TO app_user;
GRANT SELECT ON revenue_by_month TO app_user;

-- A reporting role that is allowed to see everything (BI service account for the warehouse export).
-- It exists to make the point: anything that connects as this role bypasses isolation, so it
-- must never be handed to a per-tenant consumer.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'reporting_admin') THEN
    CREATE ROLE reporting_admin LOGIN PASSWORD 'reporting_admin' BYPASSRLS;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO reporting_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reporting_admin;
