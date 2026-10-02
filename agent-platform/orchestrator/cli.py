"""Ask the assistant a question from the command line.

    export ANTHROPIC_API_KEY=...
    python -m orchestrator.cli "When is my next appointment and is anything running out?" --patient pat-1

Both group servers run in-process over the in-memory transport; swap the targets for
Streamable HTTP URLs to talk to servers deployed by their own teams.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from agentkit import issue_token
from servers import appointments, medications

from .loop import AgentLoop
from .registry import ToolRegistry


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--patient", default="pat-1")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    async with ToolRegistry() as registry:
        await registry.connect("appointments", appointments.server)
        await registry.connect("medications", medications.server)
        loop = AgentLoop(registry, **({"model": args.model} if args.model else {}))
        answer = await loop.run(args.question, auth=issue_token(args.patient))

    print(answer.text)
    print("\n--- tool calls ---")
    for call in answer.tool_calls:
        print(f"{call.name} {json.dumps(call.arguments)} -> {call.outcome}")
    print("--- usage ---")
    print(json.dumps(answer.usage))
    print(f"turns: {answer.turns}")


if __name__ == "__main__":
    asyncio.run(main())
