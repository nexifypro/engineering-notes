"""The reviewing team's gate: every published tool passes the checklist, and the
checklist catches the mistakes it exists to catch."""

import pytest
from mcp import types
from mcp.client.client import Client
from mcp.server.mcpserver import MCPServer

from pydantic import BaseModel

from agentkit import check_tools
from servers import appointments, medications

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("module", [appointments, medications])
async def test_servers_pass_the_contract(module):
    async with Client(module.server) as client:
        tools = (await client.list_tools()).tools
        violations = check_tools(tools, prefix=module.PREFIX, instructions=client.instructions)
    assert violations == [], "\n".join(map(str, violations))


class Receipt(BaseModel):
    ok: bool


async def test_contract_catches_a_badly_shaped_tool():
    bad = MCPServer("bad")  # no instructions

    @bad.tool(name="listTransactions", description="Lists transactions.")  # wrong name, no title, no sections
    async def list_transactions(user_id: str) -> list[dict]:  # identity as a parameter, no envelope
        return []

    @bad.tool(name="bad_pay", title="Pay", description="Use when paying. Do not use otherwise. Returns a receipt.",
              annotations=types.ToolAnnotations(read_only_hint=False), structured_output=True)
    async def pay(amount: float) -> Receipt:  # a write with no idempotency key, no confirmation step, no envelope
        return Receipt(ok=True)

    async with Client(bad) as client:
        tools = (await client.list_tools()).tools
        codes = {v.code for v in check_tools(tools, prefix="bad", instructions=client.instructions)}

    assert {"missing_instructions", "name_prefix", "missing_title", "missing_read_only_hint", "description_sections",
            "identity_parameter", "missing_outcome",
            "write_without_idempotency_key", "write_without_confirmed"} <= codes
