# tracker/scrapers/workday.py
#
# Scrapes job listings from Workday ATS using the internal CXS JSON API.
# This is the same endpoint Workday career pages use internally — no auth required.
#
# Endpoint pattern:
#   POST https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
#   Body: {"searchText": "software intern", "limit": 20, "offset": 0}
#
# To add a new company:
#   1. Open their Workday careers page in DevTools → Network tab
#   2. Find the XHR POST request to /wday/cxs/.../jobs
#   3. Extract the tenant slug and site name from the URL
#   4. Add them to WORKDAY_COMPANIES in config.py

import json
import urllib.request

from tracker.config import BIG_TECH_SEARCH_QUERY, WORKDAY_COMPANIES
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_API_PATTERN = "https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"


def scrape() -> list[Job]:
    jobs: list[Job] = []
    for company_name, (tenant, site) in WORKDAY_COMPANIES.items():
        try:
            jobs.extend(_scrape_company(company_name, tenant, site))
        except Exception as exc:
            print(f"[workday] WARNING: failed to scrape {company_name}: {exc}")
    return jobs


def _scrape_company(company_name: str, tenant: str, site: str) -> list[Job]:
    url = _API_PATTERN.format(tenant=tenant, site=site)
    payload = json.dumps({
        "searchText": BIG_TECH_SEARCH_QUERY,
        "limit": 20,
        "offset": 0,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "InternHub/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    jobs: list[Job] = []
    for posting in data.get("jobPostings", []):
        title = posting.get("title", "")
        # externalPath is a relative path like /en/job/R12345
        path = posting.get("externalPath", "")
        job_url = f"https://{tenant}.wd5.myworkdayjobs.com{path}" if path else ""
        loc_obj = posting.get("locationsText", "") or posting.get("primaryLocation", "") or ""
        location = loc_obj if isinstance(loc_obj, str) else ""
        posted = posting.get("postedOn", "") or ""

        job: Job = {
            "id": make_job_id("workday", company_name, title, job_url),
            "title": title,
            "company": company_name,
            "location": location,
            "url": job_url,
            "date_posted": posted[:10] if posted else "",
            "description": "",
            "source": "Workday",
        }

        if passes_filters(job, "big_tech"):
            jobs.append(job)

    return jobs
