from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .jobs import Job


SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
 id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE, external_id TEXT,
 job_url TEXT NOT NULL, source TEXT NOT NULL, company TEXT, title TEXT,
 fit_score REAL NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'discovered',
 answer_provenance TEXT NOT NULL DEFAULT '{}', browser_trace TEXT,
 submission_confirmation TEXT, blocked_reason TEXT,
 discovered_at TEXT NOT NULL, updated_at TEXT NOT NULL, submitted_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, timestamp TEXT NOT NULL,
 event TEXT NOT NULL, details TEXT NOT NULL DEFAULT '{}',
 FOREIGN KEY(application_id) REFERENCES applications(id)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Tracker:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def add_job(self, job: Job) -> tuple[int, bool]:
        stamp = now()
        with self.connect() as db:
            cursor = db.execute(
                """INSERT OR IGNORE INTO applications
                (fingerprint,external_id,job_url,source,company,title,fit_score,discovered_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    job.fingerprint,
                    job.external_id,
                    job.url,
                    job.source,
                    job.company,
                    job.title,
                    job.fit_score,
                    stamp,
                    stamp,
                ),
            )
            row = db.execute(
                "SELECT id FROM applications WHERE fingerprint=?", (job.fingerprint,)
            ).fetchone()
            return int(row["id"]), cursor.rowcount == 1

    def transition(self, app_id: int, state: str, **fields) -> None:
        allowed = {
            "answer_provenance",
            "browser_trace",
            "submission_confirmation",
            "blocked_reason",
            "submitted_at",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unsupported fields: {unknown}")
        values = {
            key: json.dumps(value) if isinstance(value, (dict, list)) else value
            for key, value in fields.items()
        }
        values.update(state=state, updated_at=now())
        assignments = ",".join(f"{key}=?" for key in values)
        with self.connect() as db:
            db.execute(
                f"UPDATE applications SET {assignments} WHERE id=?", (*values.values(), app_id)
            )
            db.execute(
                "INSERT INTO events(application_id,timestamp,event,details) VALUES(?,?,?,?)",
                (app_id, now(), state, json.dumps(fields)),
            )

    def rows(self) -> list[dict]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM applications ORDER BY id")]
