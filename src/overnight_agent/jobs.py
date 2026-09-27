from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Protocol
from urllib.parse import urlsplit, urlunsplit


@dataclass
class Job:
    source: str
    external_id: str
    title: str
    company: str
    url: str
    description: str = ""
    location: str = ""
    employment_type: str = ""
    start_date: str = ""
    metadata: dict = field(default_factory=dict)
    fit_score: float = 0.0

    @property
    def fingerprint(self) -> str:
        canonical = f"{self.company.lower()}|{self.title.lower()}|{canonical_url(self.url)}"
        return hashlib.sha256(canonical.encode()).hexdigest()


class Connector(Protocol):
    name: str

    def discover(self) -> list[Job]: ...


class JsonFeedConnector:
    """Connector for public JSON feeds; a small adapter makes each board explicit."""

    name = "json_feed"

    def __init__(self, url: str, source: str = "json_feed") -> None:
        self.url, self.name = url, source

    def discover(self) -> list[Job]:
        req = urllib.request.Request(self.url, headers={"User-Agent": "overnight-job-agent/0.1"})
        with urllib.request.urlopen(req, timeout=20) as response:  # noqa: S310
            payload = json.load(response)
        rows = payload.get("jobs", payload) if isinstance(payload, dict) else payload
        return [self._normalize(row) for row in rows]

    def _normalize(self, row: dict) -> Job:
        return Job(
            source=self.name,
            external_id=str(row.get("id", row.get("job_id", ""))),
            title=str(row.get("title", row.get("name", ""))),
            company=str(row.get("company", row.get("company_name", ""))),
            url=str(row.get("url", row.get("absolute_url", ""))),
            description=str(row.get("description", row.get("content", ""))),
            location=str(row.get("location", row.get("location_name", ""))),
            employment_type=str(row.get("employment_type", "")),
            start_date=str(row.get("start_date", "")),
            metadata={"raw": row},
        )


class GreenhouseConnector(JsonFeedConnector):
    def __init__(self, board_token: str) -> None:
        super().__init__(
            f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true",
            source=f"greenhouse:{board_token}",
        )


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def score_job(job: Job, wanted_titles: Iterable[str]) -> float:
    text = f"{job.title} {job.description}".lower()
    phrase_hits = sum(1 for phrase in wanted_titles if phrase.lower() in text)
    level_bonus = 0.15 if re.search(r"\b(senior|new grad|university)\b", text) else 0
    job.fit_score = min(1.0, phrase_hits * 0.25 + level_bonus)
    return job.fit_score


def filter_jobs(jobs: Iterable[Job], config: dict) -> list[Job]:
    titles = config.get("titles", [])
    excluded = [x.lower() for x in config.get("exclude_keywords", [])]
    allowed_types = {x.lower() for x in config.get("employment_types", [])}
    earliest = config.get("start_on_or_after", "")
    unique: dict[str, Job] = {}
    for job in jobs:
        haystack = f"{job.title} {job.description}".lower()
        if any(term in haystack for term in excluded):
            continue
        if (
            allowed_types
            and job.employment_type
            and job.employment_type.lower() not in allowed_types
        ):
            continue
        if (
            earliest
            and job.start_date
            and date.fromisoformat(job.start_date) < date.fromisoformat(earliest)
        ):
            continue
        score_job(job, titles)
        if job.fit_score > 0:
            old = unique.get(job.fingerprint)
            if old is None or job.fit_score > old.fit_score:
                unique[job.fingerprint] = job
    return sorted(unique.values(), key=lambda item: item.fit_score, reverse=True)
