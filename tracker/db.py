# tracker/db.py
#
# Thin persistence layer over seen_jobs.json.
# Tracks which job IDs have already triggered an email, and when each
# scraper last ran.  All functions read/write atomically through load_db()
# and save_db() to keep the JSON consistent.

import json
from datetime import datetime, timezone
from pathlib import Path

# seen_jobs.json lives next to this file inside tracker/
DB_PATH = Path(__file__).parent / "seen_jobs.json"

_EMPTY_DB: dict = {"seen_ids": [], "last_run": {}}


def load_db() -> dict:
    """
    Read seen_jobs.json from disk.
    Creates the file with an empty structure if it doesn't exist yet
    (e.g. first run after cloning the repo).
    """
    if not DB_PATH.exists():
        save_db(dict(_EMPTY_DB) | {"seen_ids": [], "last_run": {}})
    with DB_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_db(db: dict) -> None:
    """Write the in-memory db dict back to seen_jobs.json."""
    with DB_PATH.open("w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2)


def is_new(job_id: str) -> bool:
    """Return True if this job ID has NOT been seen before."""
    db = load_db()
    return job_id not in db["seen_ids"]


def mark_seen(job_id: str) -> None:
    """Record job_id so it won't trigger another email."""
    db = load_db()
    if job_id not in db["seen_ids"]:
        db["seen_ids"].append(job_id)
        save_db(db)


def get_last_run(scraper: str) -> datetime | None:
    """
    Return the last time this scraper ran as an aware UTC datetime,
    or None if it has never run.
    """
    db = load_db()
    ts = db["last_run"].get(scraper)
    if ts is None:
        return None
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def set_last_run(scraper: str) -> None:
    """Record now as the last run time for this scraper."""
    db = load_db()
    db["last_run"][scraper] = datetime.now(timezone.utc).isoformat()
    save_db(db)


def is_seeded() -> bool:
    """
    Return True if seen_ids is non-empty.
    Used by main.py to detect a first run: on first run seen_ids is empty,
    so we do a seed pass (mark everything as seen without emailing) to
    avoid a flood of emails for all currently-live postings.
    """
    db = load_db()
    return len(db["seen_ids"]) > 0
