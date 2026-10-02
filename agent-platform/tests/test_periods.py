from datetime import date

import pytest
from mcp.client.client import Client

from agentkit import PeriodError, resolve_period
from servers import appointments
from tests.conftest import meta_for

TODAY = date(2026, 10, 5)  # a Monday


def test_named_periods_resolve_against_the_server_clock():
    assert resolve_period("this_week", today=TODAY).model_dump() == {"period": "this_week", "start": "2026-10-05", "end": "2026-10-11"}
    assert resolve_period("this_month", today=TODAY).end == "2026-10-31"
    assert resolve_period("last_30_days", today=TODAY).start == "2026-09-06"


def test_explicit_ranges_are_validated():
    with pytest.raises(PeriodError):
        resolve_period("today", today=TODAY, start=TODAY, end=TODAY)
    with pytest.raises(PeriodError):
        resolve_period(None, today=TODAY, start=TODAY, end=TODAY.replace(year=2024))
    with pytest.raises(PeriodError):
        resolve_period("fortnight", today=TODAY)


@pytest.mark.anyio
async def test_tools_echo_the_resolved_range(token):
    async with Client(appointments.server) as client:
        r = await client.call_tool("appointments_upcoming", {"period": "next_7_days"}, meta=meta_for(token))
    assert r.structured_content["resolved"] == {"period": "next_7_days", "start": "2026-10-05", "end": "2026-10-11"}
    assert [a["id"] for a in r.structured_content["data"]] == ["apt-1001"]
