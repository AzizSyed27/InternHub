# tracker/scrapers/city_toronto.py
#
# Scrapes City of Toronto job listings via Playwright.
# URL: https://www.toronto.ca/city-government/jobs-at-the-city/current-job-opportunities/
#
# The City of Toronto jobs page lists postings in an HTML table.
# Playwright navigates the page and extracts job rows.

from tracker.config import PUBLIC_SECTOR_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

_JOBS_URL = "https://www.toronto.ca/city-government/jobs-at-the-city/current-job-opportunities/"


def scrape() -> list[Job]:
    if not PUBLIC_SECTOR_ENABLED.get("city_toronto"):
        return []
    if not PLAYWRIGHT_AVAILABLE:
        print("[city_toronto] WARNING: Playwright not installed; skipping")
        return []
    try:
        return _scrape()
    except Exception as exc:
        print(f"[city_toronto] WARNING: {exc}")
        return []


def _scrape() -> list[Job]:
    jobs: list[Job] = []
    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(_JOBS_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Job listings are inside a table or a list of links
        job_links = page.locator("table a, .job-listing a, .views-row a").all()

        for link_el in job_links[:60]:
            try:
                href = link_el.get_attribute("href") or ""
                title = link_el.inner_text().strip()
                if not title or not href or href in seen_urls:
                    continue
                if not href.startswith("http"):
                    href = "https://www.toronto.ca" + href
                seen_urls.add(href)

                job: Job = {
                    "id": make_job_id("toronto", "City of Toronto", title, href),
                    "title": title,
                    "company": "City of Toronto",
                    "location": "Toronto, Ontario, Canada",
                    "url": href,
                    "date_posted": "",
                    "description": "",
                    "source": "CityToronto",
                }
                if passes_filters(job, "public_sector"):
                    jobs.append(job)
            except Exception:
                continue

        browser.close()
    return jobs
