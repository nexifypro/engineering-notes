"""The appointments group: one domain, one server, one prefix, one guidance
paragraph, one cheap status tool. Owned by the team that owns scheduling."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from mcp import types
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from pydantic import BaseModel, Field

from agentkit import Envelope, NamedPeriod, PeriodError, Unauthenticated, data, empty, error, require_identity, resolve_period
from . import data as db

PREFIX = "appointments"
store = db.seed()


def reset_store() -> None:
    global store
    store = db.seed()


class AppointmentOut(BaseModel):
    id: str
    clinician: str
    clinician_type: str
    starts_at: str = Field(description="ISO 8601 with offset")
    location: str


class AppointmentStatus(BaseModel):
    next_appointment: AppointmentOut | None
    days_until_next: int | None = Field(description="Whole days from today; 0 means today")
    booked_in_next_30_days: int


class SlotOut(BaseModel):
    slot_id: str
    clinician: str
    clinician_type: str
    starts_at: str
    location: str


class BookingResult(BaseModel):
    status: Literal["needs_confirmation", "booked"]
    proposal: SlotOut | None = Field(default=None, description="What will be booked; show this to the user and ask")
    appointment: AppointmentOut | None = None
    idempotency_key: str


server = MCPServer(
    "appointments",
    instructions=(
        "Appointments tools cover the patient's booked visits and open slots at the clinic network. "
        "Use appointments_status for a one-line summary, appointments_upcoming for what is booked, "
        "appointments_available_slots before offering times, and appointments_book to reserve a slot. "
        "Times are already in the clinic's local time; quote them as returned. These tools do not give "
        "clinical advice and do not cover prescriptions."
    ),
)

READ = types.ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
WRITE = types.ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def _out(a: db.Appointment) -> AppointmentOut:
    return AppointmentOut(id=a.id, clinician=a.clinician, clinician_type=a.clinician_type, starts_at=a.starts_at.isoformat(), location=a.location)


def _slot(s: db.Slot) -> SlotOut:
    return SlotOut(slot_id=s.id, clinician=s.clinician, clinician_type=s.clinician_type, starts_at=s.starts_at.isoformat(), location=s.location)


@server.tool(
    name="appointments_status",
    title="Appointments status",
    description=(
        "Use when: building the per-request snapshot or answering 'when is my next appointment'. "
        "Do not use: to list several appointments (use appointments_upcoming). "
        "Returns: the next booked appointment, whole days until it, and how many are booked in the next 30 days."
    ),
    annotations=READ,
    structured_output=True,
)
async def appointments_status(ctx: Context) -> Envelope[AppointmentStatus]:
    try:
        who = require_identity(ctx)
        upcoming = [a for a in store.appointments_for(who.subject) if a.starts_at.date() >= db.TODAY]
    except Unauthenticated as exc:
        return error("unauthenticated", str(exc), as_of=db.NOW)
    except db.UpstreamUnavailable:
        return error("upstream_unavailable", "The scheduling system did not respond.", retryable=True, as_of=db.NOW)
    nxt = upcoming[0] if upcoming else None
    return data(
        AppointmentStatus(
            next_appointment=_out(nxt) if nxt else None,
            days_until_next=(nxt.starts_at.date() - db.TODAY).days if nxt else None,
            booked_in_next_30_days=sum(1 for a in upcoming if (a.starts_at.date() - db.TODAY).days < 30),
        ),
        as_of=db.NOW,
    )


@server.tool(
    name="appointments_upcoming",
    title="Upcoming appointments",
    description=(
        "Use when: the patient asks what is booked, for a period such as this_week or next_30_days, or an explicit start/end. "
        "Do not use: to find free times (use appointments_available_slots). "
        "Returns: booked appointments in the resolved period, soonest first, with the exact date range used."
    ),
    annotations=READ,
    structured_output=True,
)
async def appointments_upcoming(
    period: NamedPeriod | None = "next_30_days",
    start: date | None = None,
    end: date | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
    ctx: Context = None,
) -> Envelope[list[AppointmentOut]]:
    try:
        who = require_identity(ctx)
        resolved = resolve_period(period, today=db.TODAY, start=start, end=end)
        rows = [a for a in store.appointments_for(who.subject) if resolved.start <= a.starts_at.date().isoformat() <= resolved.end]
    except Unauthenticated as exc:
        return error("unauthenticated", str(exc), as_of=db.NOW)
    except PeriodError as exc:
        return error("invalid_period", str(exc), as_of=db.NOW)
    except db.UpstreamUnavailable:
        return error("upstream_unavailable", "The scheduling system did not respond.", retryable=True, as_of=db.NOW)
    if not rows:
        return empty("no_appointments_in_period", as_of=db.NOW, resolved=resolved)
    return data([_out(a) for a in rows[:limit]], as_of=db.NOW, resolved=resolved)


@server.tool(
    name="appointments_available_slots",
    title="Available slots",
    description=(
        "Use when: the patient wants to book or move an appointment and needs options. "
        "Do not use: to report what is already booked. "
        "Returns: open slots in the period, soonest first, filtered by clinician type; pass a slot_id to appointments_book."
    ),
    annotations=READ,
    structured_output=True,
)
async def appointments_available_slots(
    clinician_type: Literal["gp", "nurse", "physio", "any"] = "any",
    period: NamedPeriod | None = "next_7_days",
    start: date | None = None,
    end: date | None = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 5,
    ctx: Context = None,
) -> Envelope[list[SlotOut]]:
    try:
        require_identity(ctx)
        resolved = resolve_period(period, today=db.TODAY, start=start, end=end)
        rows = [
            s for s in store.open_slots()
            if resolved.start <= s.starts_at.date().isoformat() <= resolved.end
            and (clinician_type == "any" or s.clinician_type == clinician_type)
        ]
    except Unauthenticated as exc:
        return error("unauthenticated", str(exc), as_of=db.NOW)
    except PeriodError as exc:
        return error("invalid_period", str(exc), as_of=db.NOW)
    except db.UpstreamUnavailable:
        return error("upstream_unavailable", "The scheduling system did not respond.", retryable=True, as_of=db.NOW)
    if not rows:
        return empty("no_open_slots_in_period", as_of=db.NOW, resolved=resolved)
    return data([_slot(s) for s in rows[:limit]], as_of=db.NOW, resolved=resolved)


@server.tool(
    name="appointments_book",
    title="Book an appointment",
    description=(
        "Use when: the patient has chosen a slot_id from appointments_available_slots. Call once with confirmed=false to get "
        "the proposal, show it, and only after the patient agrees call again with confirmed=true and the same idempotency_key. "
        "Do not use: without a slot_id, or to change clinical details. "
        "Returns: status needs_confirmation with the proposal, or status booked with the appointment."
    ),
    annotations=WRITE,
    structured_output=True,
)
async def appointments_book(
    slot_id: str,
    reason: Annotated[str, Field(max_length=200, description="Short reason for the visit, in the patient's words")],
    idempotency_key: Annotated[str, Field(min_length=8, max_length=64, description="Client-generated key; reuse it when confirming or retrying")],
    confirmed: bool = False,
    ctx: Context = None,
) -> Envelope[BookingResult]:
    try:
        who = require_identity(ctx)
        store._check("appointments")
    except Unauthenticated as exc:
        return error("unauthenticated", str(exc), as_of=db.NOW)
    except db.UpstreamUnavailable:
        return error("upstream_unavailable", "The scheduling system did not respond.", retryable=True, as_of=db.NOW)

    if idempotency_key in store.bookings_by_key:
        existing = store.appointments[store.bookings_by_key[idempotency_key]]
        return data(BookingResult(status="booked", appointment=_out(existing), idempotency_key=idempotency_key), as_of=db.NOW)

    slot = store.slots.get(slot_id)
    if slot is None or slot.taken:
        return error("slot_unavailable", "That slot is no longer available; offer the patient other slots.", as_of=db.NOW)

    if not confirmed:
        return data(BookingResult(status="needs_confirmation", proposal=_slot(slot), idempotency_key=idempotency_key), as_of=db.NOW)

    slot.taken = True
    appt = db.Appointment(store.next_id("apt"), who.subject, slot.clinician, slot.clinician_type, slot.starts_at, slot.location)
    store.appointments[appt.id] = appt
    store.bookings_by_key[idempotency_key] = appt.id
    return data(BookingResult(status="booked", appointment=_out(appt), idempotency_key=idempotency_key), as_of=db.NOW)
