"""The medications group. Note what lives in the tool and not in the prompt: the
days-of-supply arithmetic. A model asked to work that out from a dispensed date and
a daily dose will get it right most of the time, which is the wrong number of times."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal

from mcp import types
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from pydantic import BaseModel, Field

from agentkit import Envelope, NamedPeriod, PeriodError, Unauthenticated, data, empty, error, require_identity, resolve_period
from . import data as db

PREFIX = "medications"
store = db.seed()


def reset_store() -> None:
    global store
    store = db.seed()


class RefillOut(BaseModel):
    prescription_id: str
    name: str
    days_of_supply_left: int = Field(description="Computed by the server from dose and dispensed quantity; may be negative if already out")
    runs_out_on: str = Field(description="ISO date the current supply ends")
    refills_remaining: int


class MedicationStatus(BaseModel):
    active_prescriptions: int
    due_for_refill_within_7_days: int


class RefillRequestResult(BaseModel):
    status: Literal["needs_confirmation", "requested", "needs_prescriber"]
    prescription: RefillOut | None = None
    note: str | None = Field(default=None, description="Why the request needs a prescriber, when it does")
    idempotency_key: str


server = MCPServer(
    "medications",
    instructions=(
        "Medications tools cover the patient's repeat prescriptions and refill requests. "
        "Use medications_status for the snapshot, medications_refills_due to see what runs out and when, and "
        "medications_request_refill to raise a request. days_of_supply_left is authoritative; do not recompute it. "
        "These tools never change doses and give no advice about taking medication."
    ),
)

READ = types.ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
WRITE = types.ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def _refill(p: db.Prescription) -> RefillOut:
    supply_days = p.quantity_dispensed // p.daily_dose
    runs_out = p.dispensed_on + timedelta(days=supply_days)
    return RefillOut(
        prescription_id=p.id,
        name=p.name,
        days_of_supply_left=(runs_out - db.TODAY).days,
        runs_out_on=runs_out.isoformat(),
        refills_remaining=p.refills_remaining,
    )


@server.tool(
    name="medications_status",
    title="Medications status",
    description=(
        "Use when: building the per-request snapshot or answering 'is anything due for refill'. "
        "Do not use: to list prescriptions (use medications_refills_due). "
        "Returns: counts of active prescriptions and those running out within 7 days."
    ),
    annotations=READ,
    structured_output=True,
)
async def medications_status(ctx: Context) -> Envelope[MedicationStatus]:
    try:
        who = require_identity(ctx)
        rx = store.prescriptions_for(who.subject)
    except Unauthenticated as exc:
        return error("unauthenticated", str(exc), as_of=db.NOW)
    except db.UpstreamUnavailable:
        return error("upstream_unavailable", "The pharmacy system did not respond.", retryable=True, as_of=db.NOW)
    due = sum(1 for p in rx if _refill(p).days_of_supply_left <= 7)
    return data(MedicationStatus(active_prescriptions=len(rx), due_for_refill_within_7_days=due), as_of=db.NOW)


@server.tool(
    name="medications_refills_due",
    title="Refills due",
    description=(
        "Use when: the patient asks what is running out, when, or whether a refill is needed, for a period such as next_30_days. "
        "Do not use: to request a refill (use medications_request_refill). "
        "Returns: prescriptions that run out inside the period, soonest first, with server-computed days of supply left."
    ),
    annotations=READ,
    structured_output=True,
)
async def medications_refills_due(
    period: NamedPeriod | None = "next_30_days",
    start: date | None = None,
    end: date | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
    ctx: Context = None,
) -> Envelope[list[RefillOut]]:
    try:
        who = require_identity(ctx)
        resolved = resolve_period(period, today=db.TODAY, start=start, end=end)
        rows = sorted((_refill(p) for p in store.prescriptions_for(who.subject)), key=lambda r: r.runs_out_on)
        rows = [r for r in rows if r.runs_out_on <= resolved.end]
    except Unauthenticated as exc:
        return error("unauthenticated", str(exc), as_of=db.NOW)
    except PeriodError as exc:
        return error("invalid_period", str(exc), as_of=db.NOW)
    except db.UpstreamUnavailable:
        return error("upstream_unavailable", "The pharmacy system did not respond.", retryable=True, as_of=db.NOW)
    if not rows:
        return empty("nothing_runs_out_in_period", as_of=db.NOW, resolved=resolved)
    return data(rows[:limit], as_of=db.NOW, resolved=resolved)


@server.tool(
    name="medications_request_refill",
    title="Request a refill",
    description=(
        "Use when: the patient wants a repeat of a prescription_id from medications_refills_due. Call with confirmed=false to get "
        "the proposal, show it, then with confirmed=true and the same idempotency_key once the patient agrees. "
        "Do not use: for a new medication or a dose change. "
        "Returns: needs_confirmation, requested, or needs_prescriber when no refills remain."
    ),
    annotations=WRITE,
    structured_output=True,
)
async def medications_request_refill(
    prescription_id: str,
    idempotency_key: Annotated[str, Field(min_length=8, max_length=64)],
    confirmed: bool = False,
    ctx: Context = None,
) -> Envelope[RefillRequestResult]:
    try:
        who = require_identity(ctx)
        rx = {p.id: p for p in store.prescriptions_for(who.subject)}
    except Unauthenticated as exc:
        return error("unauthenticated", str(exc), as_of=db.NOW)
    except db.UpstreamUnavailable:
        return error("upstream_unavailable", "The pharmacy system did not respond.", retryable=True, as_of=db.NOW)

    p = rx.get(prescription_id)
    if p is None:
        return error("unknown_prescription", "No such prescription for this patient.", as_of=db.NOW)
    if idempotency_key in store.refills_by_key:
        return data(RefillRequestResult(status="requested", prescription=_refill(p), idempotency_key=idempotency_key), as_of=db.NOW)
    if p.refills_remaining == 0:
        return data(RefillRequestResult(status="needs_prescriber", prescription=_refill(p), note="No repeats left; a prescriber must review before a new supply.", idempotency_key=idempotency_key), as_of=db.NOW)
    if not confirmed:
        return data(RefillRequestResult(status="needs_confirmation", prescription=_refill(p), idempotency_key=idempotency_key), as_of=db.NOW)
    p.refills_remaining -= 1
    store.refills_by_key[idempotency_key] = p.id
    return data(RefillRequestResult(status="requested", prescription=_refill(p), idempotency_key=idempotency_key), as_of=db.NOW)
