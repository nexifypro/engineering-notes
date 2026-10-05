"""Background jobs are where tenant context is usually lost. The job payload must carry the
tenant, and the worker must set it before touching the Session, exactly as a request does."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text

from .tenancy import SessionLocal, current_tenant


@dataclass(frozen=True)
class SendRemindersJob:
    tenant_id: UUID  # mandatory; a job without a tenant cannot be enqueued


def run_send_reminders(job: SendRemindersJob) -> list[str]:
    token = current_tenant.set(job.tenant_id)
    try:
        with SessionLocal() as session:
            rows = session.execute(text("SELECT id FROM invoices WHERE status = 'sent'")).scalars().all()
            return [str(r) for r in rows]
    finally:
        current_tenant.reset(token)
