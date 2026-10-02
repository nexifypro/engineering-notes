"""Empty and error are different things, and the model can tell them apart."""

import pytest
from mcp.client.client import Client

from servers import appointments, medications
from tests.conftest import meta_for

pytestmark = pytest.mark.anyio


async def test_no_refills_due_is_empty_with_a_reason(token):
    async with Client(medications.server) as client:
        r = await client.call_tool("medications_refills_due", {"period": "today"}, meta=meta_for(token))
    assert r.is_error is False
    assert r.structured_content["outcome"] == "empty"
    assert r.structured_content["reason"] == "nothing_runs_out_in_period"
    assert r.structured_content["resolved"]["start"] == "2026-10-05"


async def test_upstream_outage_is_an_error_not_empty(token):
    medications.store.fail_next("medications")
    async with Client(medications.server) as client:
        r = await client.call_tool("medications_refills_due", {}, meta=meta_for(token))
    body = r.structured_content
    assert body["outcome"] == "error"
    assert body["error"]["code"] == "upstream_unavailable"
    assert body["error"]["retryable"] is True
    assert body["data"] is None and body["reason"] is None


async def test_deterministic_maths_lives_in_the_tool(token):
    async with Client(medications.server) as client:
        r = await client.call_tool("medications_refills_due", {"period": "next_30_days"}, meta=meta_for(token))
    rows = {row["name"]: row for row in r.structured_content["data"]}
    # Metformin: 56 tablets at 2/day = 28 days, dispensed 22 days ago -> 6 days left, runs out 2026-10-11
    assert rows["Metformin 500mg"]["days_of_supply_left"] == 6
    assert rows["Metformin 500mg"]["runs_out_on"] == "2026-10-11"
    # Atorvastatin: 28 at 1/day, dispensed 5 days ago -> 23 days left
    assert rows["Atorvastatin 20mg"]["days_of_supply_left"] == 23


async def test_status_tool_is_cheap_and_complete(token):
    async with Client(appointments.server) as client:
        r = await client.call_tool("appointments_status", {}, meta=meta_for(token))
    body = r.structured_content["data"]
    assert body["next_appointment"]["id"] == "apt-1001"
    assert body["days_until_next"] == 3
    assert body["booked_in_next_30_days"] == 2
