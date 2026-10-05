"""A small multi-tenant API. Every route reads through the same Session, and the Session
applies the tenant. There is no `WHERE tenant_id = ...` anywhere in this file; the database
enforces it, and the leak test proves it."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .tenancy import SessionLocal, current_tenant, tenant_from_token

app = FastAPI(title="tenant-isolation-demo")


@app.middleware("http")
async def bind_tenant(request: Request, call_next):
    tenant = tenant_from_token(request.headers.get("authorization"))
    if tenant is None:
        # Unauthenticated callers never reach a Session; there is nothing to leak.
        if request.url.path.startswith(("/docs", "/openapi.json", "/health")):
            return await call_next(request)
        return JSONResponse({"detail": "missing or unknown credential"}, status_code=401)
    token = current_tenant.set(tenant)
    try:
        return await call_next(request)
    finally:
        current_tenant.reset(token)


def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


DB = Annotated[Session, Depends(db)]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/projects")
def list_projects(session: DB):
    rows = session.execute(text("SELECT id, name FROM projects ORDER BY name")).mappings().all()
    return [dict(r) for r in rows]


@app.get("/projects/{project_id}")
def get_project(project_id: UUID, session: DB):
    row = session.execute(text("SELECT id, name FROM projects WHERE id = :id"), {"id": project_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404)  # never 403: a 403 confirms the row exists
    return dict(row)


@app.get("/invoices")
def list_invoices(session: DB, status: str | None = None):
    sql = "SELECT id, project_id, amount_cents, status, issued_on FROM invoices"
    params: dict = {}
    if status:
        sql += " WHERE status = :status"
        params["status"] = status
    rows = session.execute(text(sql + " ORDER BY issued_on"), params).mappings().all()
    return [dict(r) for r in rows]


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: UUID, session: DB):
    row = session.execute(text("SELECT id, project_id, amount_cents, status, issued_on FROM invoices WHERE id = :id"), {"id": invoice_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404)
    return dict(row)


@app.get("/reports/revenue")
def revenue(session: DB):
    rows = session.execute(text("SELECT month, revenue_cents FROM revenue_by_month ORDER BY month")).mappings().all()
    return [dict(r) for r in rows]


@app.post("/invoices/{invoice_id}/mark-paid")
def mark_paid(invoice_id: UUID, session: DB):
    with session.begin():
        updated = session.execute(text("UPDATE invoices SET status = 'paid' WHERE id = :id AND status = 'sent' RETURNING id"), {"id": invoice_id}).first()
    if updated is None:
        raise HTTPException(status_code=404)
    return {"id": str(invoice_id), "status": "paid"}
