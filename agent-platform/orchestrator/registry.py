"""One logical tool endpoint.

The orchestrator connects to every configured group server, unions their tool
lists, enforces the name-prefix convention, and exposes one list of tool
definitions plus one block of guidance. When a second consumer arrives (a staff
console, a voice channel), this registry is replaced by a gateway with the same
contract and nothing above it changes.
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

from mcp import types
from mcp.client.client import Client
from mcp.server.mcpserver import MCPServer


class RegistryError(ValueError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._clients: dict[str, Client] = {}
        self._tools: list[types.Tool] = []
        self._group_of: dict[str, str] = {}
        self.guidance: dict[str, str] = {}

    async def __aenter__(self) -> "ToolRegistry":
        await self._stack.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._stack.__aexit__(*exc)

    async def connect(self, group: str, target: MCPServer | str) -> None:
        """Connect a group server: an in-process MCPServer or a Streamable HTTP URL."""
        if group in self._clients:
            raise RegistryError(f"group {group!r} connected twice")
        client = await self._stack.enter_async_context(Client(target))
        tools = (await client.list_tools()).tools
        for tool in tools:
            if not tool.name.startswith(f"{group}_"):
                raise RegistryError(f"tool {tool.name!r} from group {group!r} does not carry the group prefix")
            if tool.name in self._group_of:
                raise RegistryError(f"tool name {tool.name!r} published by two servers")
            self._group_of[tool.name] = group
        self._clients[group] = client
        self._tools.extend(tools)
        self.guidance[group] = client.instructions or ""

    @property
    def tools(self) -> list[types.Tool]:
        return list(self._tools)

    def status_tools(self) -> list[str]:
        return [t.name for t in self._tools if t.name.endswith("_status")]

    def guidance_text(self) -> str:
        return "\n\n".join(f"{group}: {text}".strip() for group, text in self.guidance.items() if text)

    def anthropic_tools(self) -> list[dict[str, Any]]:
        """Tool definitions for the Messages API. The last one carries the cache
        breakpoint so the whole tool block is a cached prefix."""
        defs = [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema} for t in self._tools]
        if defs:
            defs[-1] = {**defs[-1], "cache_control": {"type": "ephemeral"}}
        return defs

    async def call(self, name: str, arguments: dict[str, Any] | None, *, auth: str | None) -> types.CallToolResult:
        group = self._group_of.get(name)
        if group is None:
            raise RegistryError(f"unknown tool {name!r}")
        meta = {"authorization": f"Bearer {auth}"} if auth else None
        return await self._clients[group].call_tool(name, arguments or {}, meta=meta)
