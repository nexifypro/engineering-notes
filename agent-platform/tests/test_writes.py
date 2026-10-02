"""Writes propose first, execute on confirmation, and are idempotent."""

import pytest
from mcp.client.client import Client

from servers import appointments, medications
from tests.conftest import meta_for

pytestmark = pytest.mark.anyio


async def test_booking_requires_confirmation_then_is_idempotent(token):
    args = {"slot_id": "slot-1", "reason": "follow-up", "idempotency_key": "book-slot-1-abc"}
    async with Client(appointments.server) as client:
        proposal = await client.call_tool("appointments_book", args, meta=meta_for(token))
        assert proposal.structured_content["data"]["status"] == "needs_confirmation"
        assert proposal.structured_content["data"]["proposal"]["slot_id"] == "slot-1"
        assert appointments.store.slots["slot-1"].taken is False  # nothing happened yet

        booked = await client.call_tool("appointments_book", {**args, "confirmed": True}, meta=meta_for(token))
        assert booked.structured_content["data"]["status"] == "booked"
        appt_id = booked.structured_content["data"]["appointment"]["id"]

        again = await client.call_tool("appointments_book", {**args, "confirmed": True}, meta=meta_for(token))
        assert again.structured_content["data"]["appointment"]["id"] == appt_id  # same booking, not a second one

        taken = await client.call_tool("appointments_book", {**args, "idempotency_key": "another-key-123", "confirmed": True}, meta=meta_for(token))
        assert taken.structured_content["outcome"] == "error"
        assert taken.structured_content["error"]["code"] == "slot_unavailable"


async def test_refill_with_no_repeats_left_routes_to_a_prescriber(token):
    async with Client(medications.server) as client:
        r = await client.call_tool("medications_request_refill", {"prescription_id": "rx-2", "idempotency_key": "refill-rx-2-xyz", "confirmed": True}, meta=meta_for(token))
    assert r.structured_content["data"]["status"] == "needs_prescriber"


async def test_refill_proposal_then_request(token):
    args = {"prescription_id": "rx-1", "idempotency_key": "refill-rx-1-xyz"}
    async with Client(medications.server) as client:
        first = await client.call_tool("medications_request_refill", args, meta=meta_for(token))
        assert first.structured_content["data"]["status"] == "needs_confirmation"
        done = await client.call_tool("medications_request_refill", {**args, "confirmed": True}, meta=meta_for(token))
        assert done.structured_content["data"]["status"] == "requested"
        assert done.structured_content["data"]["prescription"]["refills_remaining"] == 1


async def test_write_tools_are_annotated_as_writes():
    async with Client(appointments.server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    assert tools["appointments_book"].annotations.read_only_hint is False
    assert tools["appointments_upcoming"].annotations.read_only_hint is True
