#!/usr/bin/env bash
# Measures the cost of RLS fairly: both roles run the same query with an explicit tenant filter;
# for app_user the policy is evaluated on top, for reporting_admin (BYPASSRLS) it is not.
# 100 tenants x 1,000 invoices. Prints TPS and latency.
set -euo pipefail
PORT="${PGPORT:-5499}"
ADMIN="postgresql://postgres@localhost:${PORT}/tenants"
SECONDS_PER_RUN="${SECONDS_PER_RUN:-15}"

psql "$ADMIN" -q -v ON_ERROR_STOP=1 <<'SQL'
TRUNCATE invoices, projects, tenants CASCADE;
INSERT INTO tenants (id, name) SELECT gen_random_uuid(), 'tenant ' || g FROM generate_series(1, 100) g;
INSERT INTO projects (tenant_id, name) SELECT id, 'project' FROM tenants;
INSERT INTO invoices (tenant_id, project_id, amount_cents, status, issued_on)
  SELECT p.tenant_id, p.id, (random() * 100000)::bigint, (ARRAY['draft','sent','paid'])[1 + (random() * 2)::int],
         date '2026-01-01' + (random() * 300)::int
  FROM projects p, generate_series(1, 1000);
DROP TABLE IF EXISTS invoices_bench_ids;
CREATE TABLE invoices_bench_ids AS
  SELECT row_number() OVER () AS n, id FROM invoices
  WHERE tenant_id = (SELECT id FROM tenants ORDER BY name LIMIT 1);
CREATE INDEX ON invoices_bench_ids (n);
GRANT SELECT ON invoices_bench_ids TO app_user, reporting_admin;
ANALYZE;
SQL
TENANT=$(psql "$ADMIN" -tAc "SELECT id FROM tenants ORDER BY name LIMIT 1")

run() { # role query
  local role=$1 q=$2
  PGOPTIONS="-c app.tenant_id=${TENANT}" pgbench "postgresql://${role}:${role}@localhost:${PORT}/tenants" \
    -n -c 8 -j 4 -T "$SECONDS_PER_RUN" -f "bench/queries/${q}.sql" 2>/dev/null \
    | awk -v r="$role" -v q="$q" '/^tps/ {tps=$3} /latency average/ {lat=$4} END {printf "%-16s %-14s tps=%-9s latency_avg_ms=%s\n", role, q, tps, lat; }' role="$role" q="$q"
}
echo "PostgreSQL $(psql "$ADMIN" -tAc 'show server_version') · 100 tenants · 100,000 invoices · 8 clients · ${SECONDS_PER_RUN}s per run"
for q in point_lookup tenant_month; do
  run reporting_admin "$q"   # BYPASSRLS: explicit tenant_id filter in the query, no policy
  run app_user "$q"          # same query; the policy is added on top
done
