# <Repository name>

<!-- Keep this file short enough to read in two minutes. It is read by assistants on every task
     and by humans when they join. If a rule is not worth a sentence here, it is not a rule. -->

## What this is
One paragraph: what the system does, who uses it, what it must never do.

## How to run and test
```bash
<install>        # one command
<test>           # one command; the assistant must run this before claiming a change works
<lint/typecheck> # one command
```

## Conventions that are not obvious from the code
- Language/runtime versions and the package manager we use (and the ones we do not).
- Layering: where business logic lives, what may import what.
- Error handling: the one way we return errors; what is logged, what is never logged.
- Data access: ORM or query style, migrations tool, how tenant or user scoping is enforced.
- Naming and file placement rules worth stating.

## Testing rules
- What a change must include (unit, integration, contract) and where tests live.
- Fixtures and factories to reuse instead of inventing new ones.
- What is forbidden: sleeping in tests, hitting real services, asserting on log output, etc.

## Things that look wrong but are intentional
- A short list, with one line of reasoning each, so nobody "fixes" them.

## Off limits
- Files, directories or systems the assistant must not modify (generated code, vendored code, infra state, secrets).
- Data that must never appear in prompts, fixtures or logs.

## Definition of done for a pull request
- Tests added or updated and passing; lint clean; context file updated if a convention changed;
  PR description states what was generated and what was verified by hand.
