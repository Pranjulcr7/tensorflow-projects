from __future__ import annotations

from collections import Counter
from pathlib import Path

from .tracker import Tracker


def morning_report(tracker: Tracker, output: str | Path) -> Path:
    rows = tracker.rows()
    counts = Counter(row["state"] for row in rows)
    body = ["# Morning report", "", f"Applications tracked: **{len(rows)}**", ""]
    body += [f"- {state}: {count}" for state, count in sorted(counts.items())]
    body += ["", "## Roles", ""]
    if not rows:
        body.append("No roles discovered.")
    for row in rows:
        detail = row["blocked_reason"] or row["submission_confirmation"] or ""
        body.append(
            f"- **{row['title']}**, {row['company']} [{row['state']}] "
            f"fit={row['fit_score']:.2f} {detail} ({row['job_url']})"
        )
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n")
    return path
