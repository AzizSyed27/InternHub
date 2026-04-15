# tracker/scrapers/big_tech.py
#
# Scrapes job listings from Big Tech internal career page JSON APIs.
# These are the same endpoints used by each company's own careers website.
# No authentication required, but they may add rate limiting or change without notice.
#
# Location filtering is handled by API query parameters (BIG_TECH_LOCATIONS),
# so passes_filters() is called with tier="big_tech" — location check is skipped.
#
# Uber is currently stubbed pending DevTools validation of their endpoint.
# To activate Uber: find the XHR request on jobs.uber.com, fill in _scrape_uber(),
# and add "uber" to the enabled set.

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from tracker.config import BIG_TECH_ENABLED, BIG_TECH_LOCATIONS, BIG_TECH_SEARCH_QUERY
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def scrape() -> list[Job]:
    all_jobs: list[Job] = []
    scrapers = {
        "amazon":    _scrape_amazon,
        "google":    _scrape_google,
        "microsoft": _scrape_microsoft,
        "apple":     _scrape_apple,
        "uber":      _scrape_uber,
    }
    for name, fn in scrapers.items():
        if not BIG_TECH_ENABLED.get(name):
            continue
        try:
            jobs = fn()
            # Deduplicate by URL within this company before appending
            seen_urls: set[str] = set()
            for job in jobs:
                if job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    all_jobs.append(job)
        except Exception as exc:
            print(f"[big_tech] WARNING: {name} scraper failed: {exc}")
    return all_jobs


# ---------------------------------------------------------------------------
# Amazon
# ---------------------------------------------------------------------------

# Amazon's API does exact keyword matching (no stemming): "intern" and "internship"
# return different result sets and both are needed to catch all intern postings.
# The loc_query parameter is ignored by Amazon's API (confirmed 2026-04 — any value
# including nonexistent locations returns the same result count), so we query once
# per search term without location filtering.
_AMAZON_QUERIES = ["software intern", "software internship"]


def _scrape_amazon() -> list[Job]:
    jobs: list[Job] = []
    seen_urls: set[str] = set()
    for query in _AMAZON_QUERIES:
        try:
            params = urllib.parse.urlencode({
                "base_query": query,
                "result_limit": 100,
            })
            url = f"https://www.amazon.jobs/en/search.json?{params}"
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            # As of 2026-04, Amazon's API returns results under "jobs" (flat list).
            # The old "hits" key is now an integer count, not the job list.
            for job_item in data.get("jobs", []):
                title = job_item.get("title", "")
                job_url = "https://www.amazon.jobs" + job_item.get("job_path", "")
                loc = job_item.get("normalized_location", "") or job_item.get("location", "") or ""
                description = job_item.get("description_short", "") or ""
                posted = job_item.get("posted_date", "") or ""
                job: Job = {
                    "id": make_job_id("amazon", "Amazon", title, job_url),
                    "title": title,
                    "company": "Amazon",
                    "location": loc,
                    "url": job_url,
                    "date_posted": posted[:10] if posted else "",
                    "description": description[:500],
                    "source": "BigTech",
                }
                if job["url"] not in seen_urls and passes_filters(job, "big_tech"):
                    seen_urls.add(job["url"])
                    jobs.append(job)
        except Exception as exc:
            print(f"[big_tech/amazon] WARNING: query={query!r}: {exc}")
    return jobs


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

def _scrape_google() -> list[Job]:
    jobs: list[Job] = []
    for location in BIG_TECH_LOCATIONS:
        try:
            params = urllib.parse.urlencode({
                "q": BIG_TECH_SEARCH_QUERY,
                "location": location,
                "hl": "en",
            })
            url = f"https://careers.google.com/api/jobs/jobs-v1/search/?{params}"
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            for item in data.get("jobs", []):
                title = item.get("title", "")
                job_url = "https://careers.google.com/jobs/results/" + item.get("job_id", "")
                locs = item.get("locations", [])
                loc = locs[0] if locs else ""
                description = item.get("description", "") or ""
                job: Job = {
                    "id": make_job_id("google", "Google", title, job_url),
                    "title": title,
                    "company": "Google",
                    "location": loc,
                    "url": job_url,
                    "date_posted": "",
                    "description": description[:500],
                    "source": "BigTech",
                }
                if passes_filters(job, "big_tech"):
                    jobs.append(job)
        except Exception as exc:
            print(f"[big_tech/google] WARNING: location={location}: {exc}")
    return jobs


# ---------------------------------------------------------------------------
# Microsoft
# ---------------------------------------------------------------------------

def _scrape_microsoft() -> list[Job]:
    """
    Scrape Microsoft internship listings via the Eightfold PCSX search API.

    apply.careers.microsoft.com is powered by Eightfold AI. The PCSX search endpoint
    is publicly accessible without authentication.

    Endpoint (confirmed 2026-04):
      GET https://apply.careers.microsoft.com/api/pcsx/search
    Response: {"status": 200, "data": {"positions": [...], "count": N}}
    Position fields: id, name, locations (list), postedTs (unix ts), positionUrl
    Job URL: https://apply.careers.microsoft.com{positionUrl}
    """
    jobs: list[Job] = []
    seen_ids: set[str] = set()
    start = 0
    page_size = 100
    while True:
        try:
            params = urllib.parse.urlencode({
                "domain": "microsoft.com",
                "query": BIG_TECH_SEARCH_QUERY,
                "location": "",
                "start": start,
                "num_jobs": page_size,
            })
            url = f"https://apply.careers.microsoft.com/api/pcsx/search?{params}"
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            print(f"[big_tech/microsoft] WARNING: {exc}")
            break

        positions = data.get("data", {}).get("positions", [])
        if not positions:
            break
        for item in positions:
            pos_id = str(item.get("id", ""))
            title = item.get("name", "")
            if not pos_id or not title or pos_id in seen_ids:
                continue
            seen_ids.add(pos_id)
            locs = item.get("locations", [])
            location = locs[0] if locs else ""
            pos_url = item.get("positionUrl", f"/careers/job/{pos_id}")
            job_url = "https://apply.careers.microsoft.com" + pos_url
            posted_ts = item.get("postedTs")
            if posted_ts:
                from datetime import datetime, timezone
                posted = datetime.fromtimestamp(posted_ts, tz=timezone.utc).strftime("%Y-%m-%d")
            else:
                posted = ""
            job: Job = {
                "id": make_job_id("microsoft", "Microsoft", title, job_url),
                "title": title,
                "company": "Microsoft",
                "location": location,
                "url": job_url,
                "date_posted": posted,
                "description": "",
                "source": "BigTech",
            }
            if passes_filters(job, "big_tech"):
                jobs.append(job)

        total = data.get("data", {}).get("count", 0)
        start += len(positions)
        if start >= total or len(positions) < page_size:
            break
    return jobs


# ---------------------------------------------------------------------------
# Apple
# Uses the internal JSON API that the Apple Jobs website calls internally.
# Endpoint: POST https://jobs.apple.com/api/role/search
# ---------------------------------------------------------------------------

def _scrape_apple() -> list[Job]:
    jobs: list[Job] = []
    seen_ids: set[str] = set()

    for location in BIG_TECH_LOCATIONS:
        try:
            payload = json.dumps({
                "query": BIG_TECH_SEARCH_QUERY,
                "filters": {},
                "page": 1,
                "locale": "en-us",
                "location": location,
            }).encode()
            req = urllib.request.Request(
                "https://jobs.apple.com/api/role/search",
                data=payload,
                headers={**_HEADERS, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            for item in data.get("searchResults", []):
                title = item.get("postingTitle", "")
                job_id = item.get("positionId", "")
                if not title or not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                job_url = f"https://jobs.apple.com/en-us/details/{job_id}"
                loc = item.get("location", {}).get("name", "") if isinstance(item.get("location"), dict) else ""
                description = item.get("jobSummary", "") or ""
                posted = item.get("postDateStr", "") or ""
                job: Job = {
                    "id": make_job_id("apple", "Apple", title, job_url),
                    "title": title,
                    "company": "Apple",
                    "location": loc,
                    "url": job_url,
                    "date_posted": posted[:10] if posted else "",
                    "description": description[:500],
                    "source": "BigTech",
                }
                if passes_filters(job, "big_tech"):
                    jobs.append(job)
        except Exception as exc:
            print(f"[big_tech/apple] WARNING: location={location}: {exc}")
    return jobs


# ---------------------------------------------------------------------------
# Uber — STUB
# TODO: Validate the exact endpoint and response schema via DevTools on
# jobs.uber.com. Look for an XHR/fetch request to an internal /api/ endpoint
# when the jobs page loads, then implement _scrape_uber() below.
# ---------------------------------------------------------------------------

def _scrape_uber() -> list[Job]:
    # Stub — returns empty until the endpoint is validated
    return []
