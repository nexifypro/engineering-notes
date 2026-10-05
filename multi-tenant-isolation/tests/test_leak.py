"""The cross-tenant leak test.

It does not trust the routes. It walks the application's own route table, calls every GET
route as tenant A using every id that belongs to tenant B, and asserts that nothing comes
back: a 404 for single resources (never a 403, which would confirm the row exists) and no
foreign rows in any list. Add a route and it is covered automatically.
"""

from __future__ import annotations

import re
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.jobs import SendRemindersJob, run_send_reminders
from tests.conftest import psql, psql_value

ACME = {"Authorization": "Bearer token-acme"}
GLOBEX = {"Authorization": "Bearer token-globex"}
ACME_ID = UUID("11111111-1111-1111-1111-111111111111")
GLOBEX_ID = UUID("22222222-2222-2222-2222-222222222222")

client = TestClient(app)


def ids_owned_by(tenant: UUID, table: str) -> list[str]:
    out = psql(command=f"SELECT id FROM {table} WHERE tenant_id = '{tenant}'")
    return re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", out)


def get_routes():
    for route in app.routes:
        methods = getattr(route, "methods", set())
        if "GET" in methods and route.path not in ("/health", "/docs", "/openapi.json", "/docs/oauth2-redirect", "/redoc"):
            yield route.path


def test_route_table_is_not_empty():
    assert {"/projects", "/projects/{project_id}", "/invoices", "/invoices/{invoice_id}", "/reports/revenue"} <= set(get_routes())


@pytest.mark.parametrize("path", sorted(get_routes()))
def test_no_route_returns_another_tenants_rows(path):
    foreign = {"project_id": ids_owned_by(GLOBEX_ID, "projects"), "invoice_id": ids_owned_by(GLOBEX_ID, "invoices")}
    params = re.findall(r"{(\w+)}", path)
    if params:
        for foreign_id in foreign[params[0]]:
            response = client.get(path.replace("{" + params[0] + "}", foreign_id), headers=ACME)
            assert response.status_code == 404, f"{path} leaked {foreign_id}: {response.status_code}"
    else:
        body = client.get(path, headers=ACME).json()
        leaked = [row for row in body if str(row.get("id") or row.get("project_id") or "") in foreign["project_id"] + foreign["invoice_id"]]
        assert leaked == [], f"{path} returned foreign rows: {leaked}"


def test_each_tenant_sees_only_its_own_rows():
    acme = client.get("/invoices", headers=ACME).json()
    globex = client.get("/invoices", headers=GLOBEX).json()
    assert {r["id"] for r in acme} == set(ids_owned_by(ACME_ID, "invoices"))
    assert {r["id"] for r in globex} == set(ids_owned_by(GLOBEX_ID, "invoices"))
    assert client.get("/reports/revenue", headers=ACME).json() == [
        {"month": "2026-08-01", "revenue_cents": 1250000},
        {"month": "2026-09-01", "revenue_cents": 980000},
    ]


def test_writes_cannot_cross_tenants():
    globex_sent = "bbbbbbbb-1111-0000-0000-000000000002"  # status 'sent' in the seed
    # tenant A cannot flip tenant B's invoice, and gets a 404, not a 403
    assert client.post(f"/invoices/{globex_sent}/mark-paid", headers=ACME).status_code == 404
    assert psql_value(f"SELECT status FROM invoices WHERE id = '{globex_sent}'") == "sent"
    # the owner can
    assert client.post(f"/invoices/{globex_sent}/mark-paid", headers=GLOBEX).status_code == 200
    assert psql_value(f"SELECT status FROM invoices WHERE id = '{globex_sent}'") == "paid"


def test_missing_credential_never_reaches_the_database():
    assert client.get("/invoices").status_code == 401


def test_background_job_is_scoped_by_its_payload():
    psql(command="UPDATE invoices SET status = 'sent' WHERE id = 'bbbbbbbb-1111-0000-0000-000000000002'")  # independent of test order
    assert run_send_reminders(SendRemindersJob(tenant_id=ACME_ID)) == ["aaaaaaaa-1111-0000-0000-000000000003"]
    assert run_send_reminders(SendRemindersJob(tenant_id=GLOBEX_ID)) == ["bbbbbbbb-1111-0000-0000-000000000002"]


def test_a_session_without_tenant_context_refuses_to_run():
    from app.tenancy import NoTenantContext, SessionLocal
    from sqlalchemy import text

    with pytest.raises(NoTenantContext):
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))


def test_the_database_itself_enforces_it_not_the_app():
    """Even a raw query as app_user with the wrong tenant set sees nothing; and a role with
    BYPASSRLS sees everything, which is why the app never connects as one."""
    import subprocess

    def as_role(role: str, tenant: str | None) -> str:
        setup = f"SET app.tenant_id = '{tenant}';" if tenant else ""
        return subprocess.run(
            ["psql", f"postgresql://{role}:{role}@localhost:5499/tenants", "-tAc", f"{setup} SELECT count(*) FROM invoices;"],
            check=True, capture_output=True, text=True,
        ).stdout.strip().splitlines()[-1]

    assert as_role("app_user", str(ACME_ID)) == "3"
    assert as_role("app_user", str(GLOBEX_ID)) == "2"
    assert as_role("app_user", None) == "0"
    assert as_role("reporting_admin", None) == "5"
