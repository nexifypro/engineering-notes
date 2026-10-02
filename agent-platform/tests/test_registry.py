import pytest
from mcp.server.mcpserver import MCPServer

from orchestrator.registry import RegistryError, ToolRegistry
from orchestrator.snapshot import build_snapshot
from servers import appointments, medications

pytestmark = pytest.mark.anyio


async def test_registry_unions_tools_and_guidance():
    async with ToolRegistry() as reg:
        await reg.connect("appointments", appointments.server)
        await reg.connect("medications", medications.server)
        names = [t.name for t in reg.tools]
        assert names == sorted(names, key=names.index) and len(names) == 7
        assert reg.status_tools() == ["appointments_status", "medications_status"]
        assert "appointments:" in reg.guidance_text() and "medications:" in reg.guidance_text()
        defs = reg.anthropic_tools()
        assert set(defs[0]) == {"name", "description", "input_schema"}
        assert defs[-1]["cache_control"] == {"type": "ephemeral"}
        assert "cache_control" not in defs[0]


async def test_registry_rejects_tools_without_the_group_prefix():
    rogue = MCPServer("rogue", instructions="x")

    @rogue.tool(name="other_thing", description="Use when. Do not use. Returns.")
    async def other_thing() -> dict:
        return {}

    async with ToolRegistry() as reg:
        with pytest.raises(RegistryError):
            await reg.connect("rogue", rogue)


async def test_snapshot_is_built_from_status_tools_in_parallel(token):
    async with ToolRegistry() as reg:
        await reg.connect("appointments", appointments.server)
        await reg.connect("medications", medications.server)
        snap = await build_snapshot(reg, auth=token)
    assert snap["appointments"]["data"]["days_until_next"] == 3
    assert snap["medications"]["data"]["due_for_refill_within_7_days"] == 1
    assert "date" in snap


async def test_snapshot_survives_one_group_failing(token):
    medications.store.fail_next("medications")
    async with ToolRegistry() as reg:
        await reg.connect("appointments", appointments.server)
        await reg.connect("medications", medications.server)
        snap = await build_snapshot(reg, auth=token)
    assert snap["appointments"]["outcome"] == "data"
    assert snap["medications"]["outcome"] == "error"
