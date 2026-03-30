# tracker/scrapers/yc.py
#
# Scrapes job listings from YC's Work at a Startup platform.
# The /jobs.json endpoint returns a public JSON feed of all active jobs.

import json
import urllib.request

from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_API_URL = "https://www.workatastartup.com/jobs.json"


def scrape() -> list[Job]:
    try:
        req = urllib.request.Request(
            _API_URL,
            headers={"User-Agent": "InternHub/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"[yc] WARNING: failed to fetch jobs: {exc}")
        return []

    jobs: list[Job] = []
    for item in data:
        title = item.get("title", "")
        company_name = item.get("company_name", "") or item.get("company", {}).get("name", "")
        apply_url = item.get("url", "") or item.get("job_url", "")
        locations = item.get("job_locations", [])
        location = ", ".join(locations) if isinstance(locations, list) else str(locations)
        description = item.get("description", "") or ""

        job: Job = {
            "id": make_job_id("yc", company_name, title, apply_url),
            "title": title,
            "company": company_name,
            "location": location,
            "url": apply_url,
            "date_posted": "",
            "description": description[:500],
            "source": "YC",
        }

        if passes_filters(job, "community"):
            jobs.append(job)

    return jobs
