"""Identity travels with the request. No tool can be asked about another patient."""

import pytest
from mcp.client.client import Client

from agentkit import issue_token
from servers import appointments, medications
from tests.conftest import meta_for

pytestmark = pytest.mark.anyio


async def test_no_credentials_is_an_error_outcome(token):
    async with Client(appointments.server) as client:
        r = await client.call_tool("appointments_upcoming", {})
    assert r.structured_content["outcome"] == "error"
    assert r.structured_content["error"]["code"] == "unauthenticated"


async def test_a_forged_token_is_rejected():
    forged = issue_token("pat-1", secret=b"not-the-real-secret")
    async with Client(appointments.server) as client:
        r = await client.call_tool("appointments_upcoming", {}, meta=meta_for(forged))
    assert r.structured_content["error"]["code"] == "unauthenticated"


async def test_each_patient_sees_only_their_own_data(token, other_token):
    async with Client(appointments.server) as client:
        mine = await client.call_tool("appointments_upcoming", {}, meta=meta_for(token))
        theirs = await client.call_tool("appointments_upcoming", {}, meta=meta_for(other_token))
    assert {a["id"] for a in mine.structured_content["data"]} == {"apt-1001", "apt-1002"}
    assert {a["id"] for a in theirs.structured_content["data"]} == {"apt-2001"}


@pytest.mark.parametrize("module", [appointments, medications])
async def test_no_tool_accepts_an_identity_parameter(module):
    async with Client(module.server) as client:
        tools = (await client.list_tools()).tools
    for tool in tools:
        assert not ({"patient_id", "user_id", "member_id"} & set(tool.input_schema.get("properties", {}))), tool.name
