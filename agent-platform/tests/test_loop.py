"""The loop, exercised with a scripted model so no network is needed."""

import json
from types import SimpleNamespace

import pytest

from orchestrator.loop import AgentLoop
from orchestrator.registry import ToolRegistry
from servers import appointments, medications

pytestmark = pytest.mark.anyio


def text_block(text):
    return SimpleNamespace(type="text", text=text, model_dump=lambda exclude_none=True: {"type": "text", "text": text})


def tool_use(id_, name, input_):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_,
                           model_dump=lambda exclude_none=True: {"type": "tool_use", "id": id_, "name": name, "input": input_})


class ScriptedModel:
    """Returns pre-written responses in order and records every request it saw."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = self

    async def create(self, **request):
        self.requests.append(request)
        content, stop = self.responses.pop(0)
        return SimpleNamespace(content=content, stop_reason=stop,
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20, cache_read_input_tokens=80, cache_creation_input_tokens=0))


async def registry():
    reg = ToolRegistry()
    await reg.__aenter__()
    await reg.connect("appointments", appointments.server)
    await reg.connect("medications", medications.server)
    return reg


async def test_request_is_shaped_for_caching(token):
    reg = await registry()
    try:
        model = ScriptedModel([([text_block("Hello")], "end_turn")])
        answer = await AgentLoop(reg, client=model).run("hi", auth=token)
        req = model.requests[0]
        assert list(req) == ["model", "max_tokens", "tools", "system", "messages"]
        assert req["tools"][-1]["cache_control"] == {"type": "ephemeral"}
        assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert "2026" not in req["system"][0]["text"]  # the date never sits in the cached prefix
        first = req["messages"][0]["content"][0]["text"]
        assert first.startswith("Snapshot for this request") and '"date"' in first
        assert answer.text == "Hello" and answer.turns == 1
        assert answer.usage["cache_read_input_tokens"] == 80
    finally:
        await reg.__aexit__(None, None, None)


async def test_tool_calls_are_dispatched_and_results_returned(token):
    reg = await registry()
    try:
        model = ScriptedModel([
            ([tool_use("t1", "medications_refills_due", {"period": "next_30_days"}), tool_use("t2", "appointments_upcoming", {})], "tool_use"),
            ([text_block("Metformin runs out on 11 October; your next appointment is on 8 October.")], "end_turn"),
        ])
        answer = await AgentLoop(reg, client=model).run("What should I know this month?", auth=token)
        assert answer.turns == 2
        assert [c.name for c in answer.tool_calls] == ["medications_refills_due", "appointments_upcoming"]
        assert all(c.outcome == "data" and not c.is_error for c in answer.tool_calls)
        results = model.requests[1]["messages"][-1]["content"]
        assert {r["tool_use_id"] for r in results} == {"t1", "t2"}
        assert json.loads(results[0]["content"])["outcome"] == "data"
    finally:
        await reg.__aexit__(None, None, None)


async def test_a_failing_tool_does_not_fail_the_answer(token):
    medications.store.set_down("medications")
    reg = await registry()
    try:
        model = ScriptedModel([
            ([tool_use("t1", "medications_refills_due", {}), tool_use("t2", "appointments_status", {})], "tool_use"),
            ([text_block("I could not reach the pharmacy system; your next appointment is in 3 days.")], "end_turn"),
        ])
        answer = await AgentLoop(reg, client=model).run("anything due?", auth=token)
        outcomes = {c.name: c.outcome for c in answer.tool_calls}
        assert outcomes == {"medications_refills_due": "error", "appointments_status": "data"}
        assert "could not reach" in answer.text
    finally:
        await reg.__aexit__(None, None, None)
