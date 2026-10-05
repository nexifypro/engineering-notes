"""Tenant context: resolved once per request from the credential, carried in a context
variable, and applied to every transaction with SET LOCAL.

Three things make this safe:
1. The tenant comes from the token, never from a query parameter or body field.
2. SET LOCAL is transaction-scoped, so a pooled connection cannot leak the previous
   tenant to the next request (session-level SET would, under transaction pooling).
3. It is applied by a Session event, so no route, job or report can forget it.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ.get("TENANTS_DATABASE_URL", "postgresql+psycopg://app_user:app_user@localhost:5499/tenants")

# Demo credential mapping. In production the tenant claim comes from your identity provider's
# access token and is verified, not looked up.
TOKENS: dict[str, UUID] = {
    "token-acme": UUID("11111111-1111-1111-1111-111111111111"),
    "token-globex": UUID("22222222-2222-2222-2222-222222222222"),
}

current_tenant: ContextVar[UUID | None] = ContextVar("current_tenant", default=None)


class NoTenantContext(RuntimeError):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _apply_tenant(session: Session, transaction, connection) -> None:
    """Runs at the start of every transaction on every Session: the tenant travels with the
    transaction, not with the connection."""
    tenant = current_tenant.get()
    if tenant is None:
        raise NoTenantContext("a database transaction was opened without a tenant in context")
    # SET LOCAL cannot take a bind parameter; set_config(..., true) is the parameterised form
    # and is equally transaction-scoped.
    connection.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {"tenant": str(tenant)})


def tenant_from_token(authorization: str | None) -> UUID | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return TOKENS.get(token)
