"""The three-outcome result envelope.

A tool result is one of exactly three things:

- ``data``   the tool found something; ``data`` is populated.
- ``empty``  the tool looked and there is confirmed nothing; ``reason`` says why
             (``no_active_goal``, ``no_appointments_in_period``).
- ``error``  the tool could not look; ``error`` carries a code and whether a retry
             might help.

The distinction matters because a model that receives a failed fetch and an empty
list in the same shape will tell the user they have no appointments when the
appointments service was simply down. Absence is never inferred from failure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResolvedPeriod(BaseModel):
    """The concrete date range a named period resolved to, echoed back so the
    answer can quote exact dates instead of 'last month'."""

    period: str = Field(description="The period as requested, e.g. next_30_days or custom")
    start: str = Field(description="First day, ISO date, inclusive")
    end: str = Field(description="Last day, ISO date, inclusive")


class ToolError(BaseModel):
    code: str = Field(description="Stable machine-readable code, e.g. upstream_unavailable")
    message: str = Field(description="One sentence a model can relay to the user")
    retryable: bool = Field(default=False, description="Whether the same call may succeed shortly")


class Envelope(BaseModel, Generic[T]):
    outcome: Literal["data", "empty", "error"] = Field(
        description="data: results in `data`; empty: confirmed nothing, see `reason`; "
        "error: could not check, see `error`. Never treat error as empty."
    )
    data: T | None = None
    reason: str | None = Field(default=None, description="Why the result is empty")
    error: ToolError | None = None
    resolved: ResolvedPeriod | None = Field(default=None, description="Date range used, when a period was given")
    as_of: str = Field(description="Server timestamp the answer is valid for, ISO 8601")


def _now(as_of: datetime | None) -> str:
    return (as_of or datetime.now(timezone.utc)).isoformat(timespec="seconds")


def data(value: T, *, as_of: datetime | None = None, resolved: ResolvedPeriod | None = None) -> Envelope[T]:
    return Envelope(outcome="data", data=value, resolved=resolved, as_of=_now(as_of))


def empty(reason: str, *, as_of: datetime | None = None, resolved: ResolvedPeriod | None = None) -> Envelope[T]:
    return Envelope(outcome="empty", reason=reason, resolved=resolved, as_of=_now(as_of))


def error(code: str, message: str, *, retryable: bool = False, as_of: datetime | None = None) -> Envelope[T]:
    return Envelope(outcome="error", error=ToolError(code=code, message=message, retryable=retryable), as_of=_now(as_of))
