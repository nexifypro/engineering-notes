"""Named periods, resolved on the server against the server's clock.

Models are bad at dates and worse at time zones. A tool that accepts
``period="last_month"`` and echoes back ``2026-09-01..2026-09-30`` removes a whole
class of wrong answers, and lets the answer quote exact dates.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal, get_args

from .envelope import ResolvedPeriod

NamedPeriod = Literal[
    "today",
    "tomorrow",
    "this_week",
    "next_7_days",
    "next_30_days",
    "this_month",
    "last_30_days",
    "last_90_days",
]

MAX_RANGE_DAYS = 366


class PeriodError(ValueError):
    """Raised for an invalid period request; tools turn it into an error outcome."""


def resolve_period(
    period: str | None,
    *,
    today: date,
    start: date | None = None,
    end: date | None = None,
) -> ResolvedPeriod:
    """Resolve a named period or an explicit range to inclusive ISO dates."""
    if start or end:
        if period:
            raise PeriodError("Give either a named period or start/end, not both")
        if not (start and end):
            raise PeriodError("Both start and end are required for a custom range")
        if end < start:
            raise PeriodError("end must not be before start")
        if (end - start).days > MAX_RANGE_DAYS:
            raise PeriodError(f"Range longer than {MAX_RANGE_DAYS} days; narrow it")
        return ResolvedPeriod(period="custom", start=start.isoformat(), end=end.isoformat())

    if period not in get_args(NamedPeriod):
        raise PeriodError(f"Unknown period {period!r}; use one of {', '.join(get_args(NamedPeriod))}")

    if period == "today":
        s, e = today, today
    elif period == "tomorrow":
        s = e = today + timedelta(days=1)
    elif period == "this_week":
        s = today - timedelta(days=today.weekday())
        e = s + timedelta(days=6)
    elif period == "next_7_days":
        s, e = today, today + timedelta(days=6)
    elif period == "next_30_days":
        s, e = today, today + timedelta(days=29)
    elif period == "this_month":
        s = today.replace(day=1)
        e = (s.replace(month=s.month % 12 + 1, year=s.year + (s.month // 12)) - timedelta(days=1))
    elif period == "last_30_days":
        s, e = today - timedelta(days=29), today
    else:  # last_90_days
        s, e = today - timedelta(days=89), today
    return ResolvedPeriod(period=period, start=s.isoformat(), end=e.isoformat())
