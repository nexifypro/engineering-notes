"""The tool contract checklist, as code.

The reviewing team does not read every tool by eye. It runs this against the
server's published tool list (what the model will actually see) and blocks the
merge on violations. Every rule here corresponds to a way an agent answers badly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from mcp import types

IDENTITY_PARAMS = {"patient_id", "user_id", "member_id", "customer_id", "account_id", "subject"}
REQUIRED_DESCRIPTION_SECTIONS = ("Use when", "Do not use", "Returns")
MAX_LIST_LIMIT = 50
MAX_INSTRUCTION_WORDS = 150


@dataclass(frozen=True)
class Violation:
    tool: str
    code: str
    detail: str

    def __str__(self) -> str:
        return f"{self.tool}: {self.code} ({self.detail})"


def _returns_list(output_schema: dict[str, Any] | None) -> bool:
    if not output_schema:
        return False
    return '"type": "array"' in json.dumps(output_schema.get("properties", {}).get("data", {}))


def check_tools(tools: list[types.Tool], *, prefix: str, instructions: str | None) -> list[Violation]:
    violations: list[Violation] = []

    if not instructions or not instructions.strip():
        violations.append(Violation("<server>", "missing_instructions", "server must publish one guidance paragraph"))
    elif len(instructions.split()) > MAX_INSTRUCTION_WORDS:
        violations.append(Violation("<server>", "instructions_too_long", f"> {MAX_INSTRUCTION_WORDS} words"))

    for tool in tools:
        name = tool.name
        if not re.fullmatch(rf"{re.escape(prefix)}_[a-z][a-z0-9_]*", name):
            violations.append(Violation(name, "name_prefix", f"expected {prefix}_<verb_noun> in snake_case"))
        if not tool.title:
            violations.append(Violation(name, "missing_title", "set a human-readable title"))

        ann = tool.annotations
        if ann is None or ann.read_only_hint is None:
            violations.append(Violation(name, "missing_read_only_hint", "declare read_only_hint explicitly"))
        is_write = bool(ann) and ann.read_only_hint is False

        desc = tool.description or ""
        missing = [s for s in REQUIRED_DESCRIPTION_SECTIONS if s.lower() not in desc.lower()]
        if missing:
            violations.append(Violation(name, "description_sections", f"missing: {', '.join(missing)}"))

        props: dict[str, Any] = (tool.input_schema or {}).get("properties", {})
        leaked = sorted(set(props) & IDENTITY_PARAMS)
        if leaked:
            violations.append(Violation(name, "identity_parameter", f"identity must come from the request, not {leaked}"))

        if not tool.output_schema:
            violations.append(Violation(name, "missing_output_schema", "return a typed envelope (structured_output=True)"))
        else:
            outcome = tool.output_schema.get("properties", {}).get("outcome", {})
            if sorted(outcome.get("enum", [])) != ["data", "empty", "error"]:
                violations.append(Violation(name, "missing_outcome", "outcome must be the data/empty/error enum"))
            if _returns_list(tool.output_schema):
                limit = props.get("limit")
                if not limit or limit.get("maximum") is None or limit.get("maximum") > MAX_LIST_LIMIT or "default" not in limit:
                    violations.append(Violation(name, "unbounded_list", f"list results need limit with a default and maximum <= {MAX_LIST_LIMIT}"))

        if is_write:
            if "idempotency_key" not in props:
                violations.append(Violation(name, "write_without_idempotency_key", "writes must take idempotency_key"))
            if "confirmed" not in props:
                violations.append(Violation(name, "write_without_confirmed", "writes must propose first (confirmed=false) and execute on confirmed=true"))

    return violations
