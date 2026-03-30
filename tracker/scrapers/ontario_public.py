# tracker/scrapers/ontario_public.py
#
# Scrapes Ontario Public Service (OPS) job listings via Playwright.
# URL: https://www.ontario.ca/page/current-ontario-public-service-job-opportunities
#
# The OPS job board is a server-rendered page with a searchable listing.
# Playwright is used to navigate and extract job cards.

from tracker.config import GOVT_CANADA_KEYWORDS, PUBLIC_SECTOR_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

_BASE_URL = "https://www.ontario.ca/page/current-ontario-public-service-job-opportunities"


def scrape() -> list[Job]:
    if not PUBLIC_SECTOR_ENABLED.get("ontario_public"):
        return []
    if not PLAYWRIGHT_AVAILABLE:
        print("[ontario_public] WARNING: Playwright not installed; skipping")
        return []
    try:
        return _scrape()
    except Exception as exc:
        print(f"[ontario_public] WARNING: {exc}")
        return []


def _scrape() -> list[Job]:
    jobs: list[Job] = []
    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(_BASE_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # The OPS page lists jobs as links — extract all job listing links
        job_links = page.locator("a[href*='careers.gov.on.ca'], a[href*='ontario.ca/page/']").all()

        for link_el in job_links[:50]:
            try:
                href = link_el.get_attribute("href") or ""
                title = link_el.inner_text().strip()
                if not title or not href or href in seen_urls:
                    continue
                if not href.startswith("http"):
                    href = "https://www.ontario.ca" + href
                seen_urls.add(href)

                job: Job = {
                    "id": make_job_id("ops", "Ontario Public Service", title, href),
                    "title": title,
                    "company": "Ontario Public Service",
                    "location": "Ontario, Canada",
                    "url": href,
                    "date_posted": "",
                    "description": "",
                    "source": "OPS",
                }
                if passes_filters(job, "public_sector"):
                    jobs.append(job)
            except Exception:
                continue

        browser.close()
    return jobs
