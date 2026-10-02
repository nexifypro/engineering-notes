# Agent platform reference implementation

Code for the article **Stop stuffing the prompt: an agent platform where domain teams own the
tools** on the [NexifyPro blog](https://nexifypro.com/blog/stop-stuffing-the-prompt).

A patient-portal assistant for a clinic network, built the way the article argues for:

- `agentkit/` is the shared kit every tool server is built on: the three-outcome result
  envelope, named-period resolution, identity taken from the request (never a parameter), and
  the contract checklist as code.
- `servers/` are two domain groups, `appointments` and `medications`, each an MCP server with a
  prefix, one guidance paragraph, one cheap status tool, reads, and one write that proposes first
  and executes on confirmation with an idempotency key. In a real system each lives in the
  repository of the team that owns the data.
- `orchestrator/` is the one model loop: a registry that unions the servers into one logical
  endpoint, a snapshot built from the status tools, and a loop whose request is shaped for prompt
  caching. It knows nothing about any domain.
- `tests/` are the reviewing team's gate: the contract checks every published tool, plus tests
  that empty and error are different, that identity cannot be spoofed, that writes are idempotent,
  and that the loop keeps answering when one tool fails.

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest -q

# live, needs a key
export ANTHROPIC_API_KEY=...
python -m orchestrator.cli "When is my next appointment, and is anything running out?" --patient pat-1
```

Tested on 2026-10-02 with Python 3.14, `mcp` 2.2.0 and `anthropic` 1.11.0. Logistics only: the
assistant books slots and raises refill requests; it gives no clinical advice.
