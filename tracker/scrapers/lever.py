# tracker/scrapers/lever.py
#
# Scrapes job listings from the Lever ATS public JSON API.
# No authentication required.
# API: https://api.lever.co/v0/postings/{slug}?mode=json&limit=250

import json
import urllib.request
from datetime import datetime, timezone

from tracker.config import LEVER_COMPANIES
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_API_URL = "https://api.lever.co/v0/postings/{slug}?mode=json&limit=250"


def scrape() -> list[Job]:
    jobs: list[Job] = []
    for company_name, slug in LEVER_COMPANIES.items():
        try:
            jobs.extend(_scrape_company(company_name, slug))
        except Exception as exc:
            print(f"[lever] WARNING: failed to scrape {company_name}: {exc}")
    return jobs


def _scrape_company(company_name: str, slug: str) -> list[Job]:
    url = _API_URL.format(slug=slug)
    req = urllib.request.Request(url, headers={"User-Agent": "InternHub/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        postings = json.loads(resp.read().decode())

    jobs: list[Job] = []
    for posting in postings:
        title = posting.get("text", "")
        apply_url = posting.get("hostedUrl", "")
        location = posting.get("categories", {}).get("location", "")
        # descriptionPlain may be absent; fall back to empty string
        description = posting.get("descriptionPlain", "") or ""
        # createdAt is Unix timestamp in milliseconds
        created_ms = posting.get("createdAt", 0)
        date_posted = _ms_to_date(created_ms)

        job: Job = {
            "id": make_job_id("lever", company_name, title, apply_url),
            "title": title,
            "company": company_name,
            "location": location,
            "url": apply_url,
            "date_posted": date_posted,
            "description": description[:500],
            "source": "Lever",
        }

        if passes_filters(job, "big_tech"):
            jobs.append(job)

    return jobs


def _ms_to_date(ms: int) -> str:
    """Convert Unix milliseconds to YYYY-MM-DD string, or empty string."""
    if not ms:
        return ""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return ""
