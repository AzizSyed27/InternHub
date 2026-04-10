# tracker/scrapers/greenhouse.py
#
# Scrapes job listings from the Greenhouse ATS public JSON API.
# No authentication required — Greenhouse boards are publicly readable.
# API docs: https://developers.greenhouse.io/job-board.html

import json
import urllib.request
from datetime import datetime, timezone

from tracker.config import GREENHOUSE_COMPANIES
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_API_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def scrape() -> list[Job]:
    jobs: list[Job] = []
    for company_name, slug in GREENHOUSE_COMPANIES.items():
        try:
            jobs.extend(_scrape_company(company_name, slug))
        except Exception as exc:
            print(f"[greenhouse] WARNING: failed to scrape {company_name}: {exc}")
    return jobs


def _scrape_company(company_name: str, slug: str) -> list[Job]:
    url = _API_URL.format(slug=slug)
    req = urllib.request.Request(url, headers={"User-Agent": "InternHub/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    jobs: list[Job] = []
    for posting in data.get("jobs", []):
        title = posting.get("title", "")
        apply_url = posting.get("absolute_url", "")
        location = posting.get("location", {}).get("name", "")
        description = posting.get("content", "") or ""
        updated_at = posting.get("updated_at", "")

        # Parse date from ISO string like "2026-03-15T12:00:00.000Z"
        date_posted = _parse_date(updated_at)

        job: Job = {
            "id": make_job_id("greenhouse", company_name, title, apply_url),
            "title": title,
            "company": company_name,
            "location": location,
            "url": apply_url,
            "date_posted": date_posted,
            "description": description[:500],
            "source": "Greenhouse",
        }

        if passes_filters(job, "big_tech"):
            jobs.append(job)

    return jobs


def _parse_date(ts: str) -> str:
    """Return YYYY-MM-DD from an ISO timestamp string, or empty string."""
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return ""
