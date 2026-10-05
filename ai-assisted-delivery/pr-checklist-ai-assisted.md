# Pull request checklist: AI-assisted changes

Paste into the PR template. Tick honestly; reviewers rely on it.

**Author**
- [ ] The task had a written spec (ticket or comment) before any code was generated.
- [ ] I can explain every line in this diff without the assistant.
- [ ] Tests express expectations I hold; none were accepted just because they passed.
- [ ] I ran the full test and lint commands locally after the last edit.
- [ ] No client data, secrets or personal data went into a prompt.
- [ ] Generated code touching auth, crypto, access control or payments is flagged below for second review.
- [ ] The repository context file still describes how this code works.

**What the assistant produced vs what I verified by hand**
<!-- e.g. "Assistant drafted the parser and tests; I wrote the edge-case tests for empty input and verified the regex against the three real log samples in fixtures/." -->

**Reviewer**
- [ ] Diff is small enough to read properly (if not, request a split).
- [ ] The tests would fail if the behaviour regressed (read the assertions, not the names).
- [ ] Error handling and logging follow the repository conventions.
- [ ] Nothing in the change widens data access, permissions or network exposure without a reason stated here.
