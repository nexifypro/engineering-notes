"""The only context injected without the model asking: a few hundred tokens from
each group's status tool, fetched in parallel. Adding a field is a deliberate
decision by a group owner, not the default."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from .registry import ToolRegistry


async def build_snapshot(registry: ToolRegistry, *, auth: str | None, now: datetime | None = None) -> dict[str, Any]:
    names = registry.status_tools()
    results = await asyncio.gather(*(registry.call(n, {}, auth=auth) for n in names), return_exceptions=True)
    snapshot: dict[str, Any] = {"date": (now or datetime.now(timezone.utc)).date().isoformat()}
    for name, result in zip(names, results):
        group = name.removesuffix("_status")
        if isinstance(result, BaseException):
            snapshot[group] = {"outcome": "error", "error": {"code": "status_unavailable", "message": str(result)}}
        else:
            snapshot[group] = result.structured_content or {"outcome": "error", "error": {"code": "no_structured_content"}}
    return snapshot
