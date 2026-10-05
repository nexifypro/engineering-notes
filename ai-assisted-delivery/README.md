# AI-assisted delivery kit

Templates and a measurement script for the article **AI coding assistants make some teams slower.
Here is how we keep them fast.** on the [NexifyPro blog](https://nexifypro.com/blog/ai-coding-assistants-slower-teams).

| File | What it is for |
|---|---|
| `team-operating-agreement.md` | The one-page agreement a team signs before assistants are allowed on production code |
| `CONTEXT-FILE-TEMPLATE.md` | A repository context file (CLAUDE.md / AGENTS.md style) that encodes the conventions an assistant must follow |
| `pr-checklist-ai-assisted.md` | Pull request checklist for changes written with an assistant |
| `pr-metrics.py` | Reports PR size, time to first review, rework rate and revert rate for a GitHub repo, so you can see what the assistant is doing to your delivery |

Run the script with the GitHub CLI authenticated:

```bash
python3 pr-metrics.py nexifypro/nexifypro-website --since 2026-01-01
```

It needs only `gh` on the path and Python 3.10+. Tested on 2026-10-05.
