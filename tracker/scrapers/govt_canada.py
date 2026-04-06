# tracker/scrapers/govt_canada.py
#
# Scrapes Government of Canada job listings via Playwright.
# The old RSS feed (page2710 with action=rss) was removed as of 2026-04.
# The current search portal is at page2440.
#
# Requires: pip install playwright && playwright install chromium

import urllib.request

from tracker.config import GOVT_CANADA_KEYWORDS, PUBLIC_SECTOR_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

# Current GC Jobs search URL (page2710 is 404 as of 2026-04)
_GC_JOBS_SEARCH = (
    "https://emploisfp-psjobs.cfp-psc.gc.ca/psrs-srfp/applicant/page2440"
    "?searchButton=Search&lang=en&keyword={keyword}"
)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def scrape() -> list[Job]:
    if not PUBLIC_SECTOR_ENABLED.get("govt_canada"):
        return []
    if not PLAYWRIGHT_AVAILABLE:
        print("[govt_canada] WARNING: Playwright not available; skipping")
        return []
    try:
        return _scrape_playwright()
    except Exception as exc:
        print(f"[govt_canada] WARNING: Playwright scraper failed: {exc}")
        return []


def _scrape_playwright() -> list[Job]:
    """Search GC Jobs via Playwright for each configured keyword."""
    jobs: list[Job] = []
    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        for keyword in GOVT_CANADA_KEYWORDS:
            try:
                page.goto(
                    _GC_JOBS_SEARCH.format(keyword=urllib.request.quote(keyword)),
                    wait_until="networkidle",
                    timeout=30000,
                )
                # Job listing rows
                rows = page.locator("table.resultTable tr, .search-result-item").all()
                for row in rows:
                    try:
                        link_el = row.locator("a").first
                        href = link_el.get_attribute("href") or ""
                        title = link_el.inner_text().strip()
                        if not title or not href or href in seen_urls:
                            continue
                        if not href.startswith("http"):
                            href = "https://emploisfp-psjobs.cfp-psc.gc.ca" + href
                        seen_urls.add(href)
                        job: Job = {
                            "id": make_job_id("gc", "Government of Canada", title, href),
                            "title": title,
                            "company": "Government of Canada",
                            "location": "Canada",
                            "url": href,
                            "date_posted": "",
                            "description": "",
                            "source": "GovtCanada",
                        }
                        if passes_filters(job, "public_sector"):
                            jobs.append(job)
                    except Exception:
                        continue
            except Exception as exc:
                print(f"[govt_canada/playwright] WARNING: keyword={keyword}: {exc}")

        browser.close()
    return jobs
