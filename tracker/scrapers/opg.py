# tracker/scrapers/opg.py
#
# Scrapes Ontario Power Generation (OPG) job listings via Playwright.
# URL: https://jobs.opg.com
#
# OPG uses a Workday-backed jobs site rendered as an SPA.
# Playwright navigates the search page and extracts job cards.

import urllib.parse

from tracker.config import PUBLIC_SECTOR_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

_SEARCH_TERMS = ["software", "technology", "student", "co-op", "intern"]
_BASE_URL = "https://jobs.opg.com"
_SEARCH_URL = "https://jobs.opg.com/search?q={term}"


def scrape() -> list[Job]:
    if not PUBLIC_SECTOR_ENABLED.get("opg"):
        return []
    if not PLAYWRIGHT_AVAILABLE:
        print("[opg] WARNING: Playwright not installed; skipping")
        return []
    try:
        return _scrape()
    except Exception as exc:
        print(f"[opg] WARNING: {exc}")
        return []


def _scrape() -> list[Job]:
    jobs: list[Job] = []
    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        for term in _SEARCH_TERMS:
            try:
                # Navigate directly to search results — avoids interacting with the
                # hidden search input on the home page (not visible, causes timeout).
                page.goto(
                    _SEARCH_URL.format(term=urllib.parse.quote(term)),
                    wait_until="networkidle",
                    timeout=30000,
                )
                page.wait_for_timeout(2000)

                job_cards = page.locator("a[href*='/job/'], a[href*='/careers/']").all()
                for card in job_cards[:20]:
                    try:
                        href = card.get_attribute("href") or ""
                        title = card.inner_text().strip().split("\n")[0]
                        if not title or not href or href in seen_urls:
                            continue
                        if not href.startswith("http"):
                            href = _BASE_URL + href
                        seen_urls.add(href)

                        job: Job = {
                            "id": make_job_id("opg", "OPG", title, href),
                            "title": title,
                            "company": "OPG",
                            "location": "Ontario, Canada",
                            "url": href,
                            "date_posted": "",
                            "description": "",
                            "source": "OPG",
                        }
                        if passes_filters(job, "public_sector"):
                            jobs.append(job)
                    except Exception:
                        continue
            except Exception as exc:
                print(f"[opg] WARNING: term={term}: {exc}")

        browser.close()
    return jobs
