#!/usr/bin/env python3
"""Delivery metrics that show what AI assistance is doing to a repository.

Reports, for merged pull requests since a date:
  - median and p90 lines changed, and the share of PRs over 400 lines
  - median hours to first review and to merge
  - rework rate: share of merged PRs where another PR touched the same files within 14 days
  - revert rate: share of merged PRs whose title starts with "Revert"

Uses the GitHub CLI for authentication: `gh auth login` once, then run this script.

    python3 pr-metrics.py owner/repo --since 2026-01-01
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

PR_FIELDS = "number,title,additions,deletions,createdAt,mergedAt,files,reviews"
LARGE_PR_LINES = 400
REWORK_WINDOW_DAYS = 14


def gh_json(args: list[str]) -> list[dict]:
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def hours(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 3600


def p(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", help="owner/name")
    ap.add_argument("--since", required=True, help="YYYY-MM-DD; merged PRs on or after this date")
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()

    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    prs = gh_json(["pr", "list", "--repo", args.repo, "--state", "merged", "--limit", str(args.limit),
                   "--search", f"merged:>={args.since}", "--json", PR_FIELDS])
    prs = [pr for pr in prs if pr.get("mergedAt") and parse(pr["mergedAt"]) >= since]
    if not prs:
        print("no merged pull requests in range")
        return 0

    sizes = [pr["additions"] + pr["deletions"] for pr in prs]
    to_merge = [hours(parse(pr["createdAt"]), parse(pr["mergedAt"])) for pr in prs]
    to_first_review = []
    for pr in prs:
        reviews = sorted((r for r in pr.get("reviews") or [] if r.get("submittedAt")), key=lambda r: r["submittedAt"])
        if reviews:
            to_first_review.append(hours(parse(pr["createdAt"]), parse(reviews[0]["submittedAt"])))

    # Rework: another merged PR touching any of the same files within the window after merge.
    by_file: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for pr in prs:
        for f in pr.get("files") or []:
            by_file[f["path"]].append((parse(pr["mergedAt"]), pr["number"]))
    reworked = 0
    for pr in prs:
        merged = parse(pr["mergedAt"])
        window_end = merged + timedelta(days=REWORK_WINDOW_DAYS)
        if any(merged < other_merged <= window_end and other_num != pr["number"]
               for f in pr.get("files") or [] for other_merged, other_num in by_file[f["path"]]):
            reworked += 1
    reverts = sum(1 for pr in prs if pr["title"].lower().startswith("revert"))

    n = len(prs)
    print(f"{args.repo} · {n} merged PRs since {args.since}")
    print(f"PR size (lines changed): median {statistics.median(sizes):.0f}, p90 {p(sizes, 0.9):.0f}, "
          f"over {LARGE_PR_LINES}: {sum(s > LARGE_PR_LINES for s in sizes) / n:.0%}")
    if to_first_review:
        print(f"Time to first review: median {statistics.median(to_first_review):.1f} h "
              f"({len(to_first_review)}/{n} PRs had a review)")
    else:
        print("Time to first review: no PR reviews recorded")
    print(f"Time to merge: median {statistics.median(to_merge):.1f} h, p90 {p(to_merge, 0.9):.1f} h")
    print(f"Rework rate ({REWORK_WINDOW_DAYS}-day, same files): {reworked / n:.0%}")
    print(f"Revert rate: {reverts / n:.0%}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc, file=sys.stderr)
        sys.exit(1)
