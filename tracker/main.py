#!/usr/bin/env python3
# tracker/main.py
#
# Internship Tracker — main orchestrator.
# Fired every 5 minutes by launchd (see launchd.plist).
#
# On first run (empty seen_jobs.json): seeds the database with all currently-live
# postings WITHOUT sending emails, to avoid a flood of notifications on setup.
# On subsequent runs: checks each scraper's interval, runs those that are due,
# and sends one email per new posting found.

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import tracker.db as db
from tracker.config import SCRAPER_INTERVALS
from tracker.emailer import send_email

# ---------------------------------------------------------------------------
# PID guard — prevents two instances running at the same time
# ---------------------------------------------------------------------------

_PID_FILE = Path(__file__).parent / "tracker.pid"


def _acquire_pid() -> bool:
    """
    Write our PID to tracker.pid.
    Return False if another instance is already running (PID file exists and
    the process is alive).  Return True if we successfully took the lock.
    """
    if _PID_FILE.exists():
        try:
            existing_pid = int(_PID_FILE.read_text().strip())
            # On POSIX, sending signal 0 checks if the process exists
            os.kill(existing_pid, 0)
            print(f"[main] Another instance is running (PID {existing_pid}). Exiting.")
            return False
        except (ProcessLookupError, ValueError):
            # Process doesn't exist — stale PID file, safe to overwrite
            pass
    _PID_FILE.write_text(str(os.getpid()))
    return True


def _release_pid() -> None:
    try:
        _PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Scraper registry — lazy imports so missing Playwright doesn't crash startup
# ---------------------------------------------------------------------------

def _load_scrapers() -> dict:
    """
    Return a dict of {scraper_name: scrape_fn}.
    Each import is wrapped in try/except so a missing optional dependency
    only disables that one scraper, not the whole run.
    """
    scrapers = {}

    def _try_register(name: str, module_path: str):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            scrapers[name] = mod.scrape
        except Exception as exc:
            print(f"[main] WARNING: could not load scraper '{name}': {exc}")

    _try_register("github_repos",   "tracker.scrapers.github_repos")
    _try_register("greenhouse",     "tracker.scrapers.greenhouse")
    _try_register("lever",          "tracker.scrapers.lever")
    _try_register("big_tech",       "tracker.scrapers.big_tech")
    _try_register("workday",        "tracker.scrapers.workday")
    _try_register("hackernews",     "tracker.scrapers.hackernews")
    _try_register("yc",             "tracker.scrapers.yc")
    _try_register("meta",           "tracker.scrapers.playwright_jobs")   # shared module
    _try_register("tesla",          "tracker.scrapers.playwright_jobs")   # shared module
    _try_register("govt_canada",    "tracker.scrapers.govt_canada")
    _try_register("ontario_public", "tracker.scrapers.ontario_public")
    _try_register("opg",            "tracker.scrapers.opg")
    _try_register("city_toronto",   "tracker.scrapers.city_toronto")

    # playwright_jobs.scrape() handles both meta and tesla internally,
    # so register it once under a unified key to avoid calling it twice
    if "meta" in scrapers and "tesla" in scrapers:
        scrapers["playwright_jobs"] = scrapers.pop("meta")
        scrapers.pop("tesla", None)
        # Remap interval key
        SCRAPER_INTERVALS["playwright_jobs"] = min(
            SCRAPER_INTERVALS.get("meta", 30),
            SCRAPER_INTERVALS.get("tesla", 60),
        )

    return scrapers


# ---------------------------------------------------------------------------
# Interval check
# ---------------------------------------------------------------------------

def _is_due(name: str) -> bool:
    """Return True if enough time has passed since this scraper last ran."""
    interval_minutes = SCRAPER_INTERVALS.get(name, 5)
    last = db.get_last_run(name)
    if last is None:
        return True
    elapsed = (datetime.now(timezone.utc) - last).total_seconds() / 60
    return elapsed >= interval_minutes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not _acquire_pid():
        sys.exit(0)

    try:
        scrapers = _load_scrapers()
        seeded = db.is_seeded()

        if not seeded:
            print("[main] First run detected — seeding database (no emails will be sent).")
            new_count = 0
            for name, scrape_fn in scrapers.items():
                try:
                    jobs = scrape_fn()
                    for job in jobs:
                        if db.is_new(job["id"]):
                            db.mark_seen(job["id"])
                            new_count += 1
                    db.set_last_run(name)
                except Exception as exc:
                    print(f"[main] WARNING: {name} failed during seed: {exc}")
            print(f"[main] Seed complete. {new_count} postings indexed. Run again to start receiving emails.")
            return

        # Normal run — only run scrapers that are due
        total_new = 0
        emails_sent = 0

        for name, scrape_fn in scrapers.items():
            if not _is_due(name):
                continue
            try:
                jobs = scrape_fn()
                db.set_last_run(name)
                for job in jobs:
                    if db.is_new(job["id"]):
                        db.mark_seen(job["id"])
                        total_new += 1
                        try:
                            send_email(job)
                            emails_sent += 1
                        except Exception as exc:
                            print(f"[main] WARNING: failed to send email for '{job['title']}': {exc}")
            except Exception as exc:
                print(f"[main] WARNING: {name} scraper failed: {exc}")

        print(f"[main] Done. {total_new} new jobs found, {emails_sent} emails sent.")

    finally:
        _release_pid()


if __name__ == "__main__":
    main()
