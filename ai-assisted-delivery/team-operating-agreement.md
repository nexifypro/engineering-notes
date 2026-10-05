# Team operating agreement for AI-assisted engineering

Version 1.0 · Owner: engineering lead · Review quarterly

## What we use assistants for
- Drafting code against a written spec or ticket that names inputs, outputs and constraints.
- Tests for existing code, with the engineer deciding what to assert.
- Migrations, boilerplate, mechanical refactors, one-off scripts, documentation drafts.
- Exploring an unfamiliar codebase, API or error, as a starting point for our own verification.

## What we do not use assistants for
- Security-sensitive code (auth, crypto, access control, payments) without a second human review.
- Anything that would require pasting client data, secrets, credentials or personal data into a prompt.
- Replacing design: architecture decisions are made by people and recorded in ADRs.
- Generating tests that merely mirror the implementation; a test must express an expectation the engineer holds.

## How we work
1. **Spec before prompt.** The task is written down first: behaviour, edge cases, non-goals. The assistant gets the spec, not a vibe.
2. **Context file is current.** The repository context file is part of the definition of done for any convention change.
3. **Small diffs.** A pull request an engineer cannot read in 20 minutes is split.
4. **Tests are the contract.** The engineer writes or approves the assertions before accepting the implementation.
5. **Author owns the diff.** Whoever opens the PR can explain every line. "The assistant wrote it" is not an explanation.
6. **Reviewer budget.** Reviewers spend the time the change deserves, not the time the author saved. If review load rises for a month, we change the process, not the reviewer.
7. **Scanners run on everything.** Static analysis, dependency scanning and secret detection do not distinguish human from generated code.
8. **Data boundaries.** Only tools on the approved list, under the approved account, with the data classes allowed for that tool.

## What we measure (monthly)
- Median PR size (lines changed) and the share of PRs over 400 lines.
- Time to first review and time to merge.
- Rework rate: share of merged PRs with a follow-up fix to the same files within 14 days.
- Revert rate and change failure rate.
- Engineer-reported friction, one question, one scale, once a month.

A tool stays on the approved list while the rework and revert rates hold and engineers report it helps. Nothing else keeps it there.
