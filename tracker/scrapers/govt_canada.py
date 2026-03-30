# tracker/scrapers/govt_canada.py
#
# Scrapes Government of Canada job listings (jobs.gc.ca / GC Jobs).
# Strategy: try the REST/RSS feed first; fall back to Playwright if it
# returns no results or raises.
#
# REST feed: GC Jobs exposes an XML job feed. The URL may change — verify
# via the Government of Canada Open Data portal or DevTools on jobs.gc.ca.
#
# Playwright fallback: searches jobs.gc.ca for each keyword in GOVT_CANADA_KEYWORDS.

import json
import re
import urllib.request
import xml.etree.ElementTree as ET

from tracker.config import GOVT_CANADA_KEYWORDS, PUBLIC_SECTOR_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

# GC Jobs RSS feed (verify this URL is still active)
_RSS_URL = "https://emploisfp-psjobs.cfp-psc.gc.ca/psrs-srfp/applicant/page2710?postingId=&lang=en&qualEd=&qualEx=&qualLan=&qualLoc=&keyword={keyword}&searchButton=Search&action=rss"
_GC_JOBS_SEARCH = "https://emploisfp-psjobs.cfp-psc.gc.ca/psrs-srfp/applicant/page2710?searchButton=Search&lang=en&keyword={keyword}"

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def scrape() -> list[Job]:
    if not PUBLIC_SECTOR_ENABLED.get("govt_canada"):
        return []

    jobs: list[Job] = []

    # Attempt 1 — RSS
    try:
        jobs = _scrape_rss()
    except Exception as exc:
        print(f"[govt_canada] RSS attempt failed: {exc}")

    # Attempt 2 — Playwright fallback if RSS returned nothing
    if not jobs:
        if not PLAYWRIGHT_AVAILABLE:
            print("[govt_canada] WARNING: Playwright not available; skipping Playwright fallback")
            return []
        try:
            jobs = _scrape_playwright()
        except Exception as exc:
            print(f"[govt_canada] WARNING: Playwright fallback failed: {exc}")

    return jobs


def _scrape_rss() -> list[Job]:
    """Fetch and parse the GC Jobs RSS feed for each configured keyword."""
    jobs: list[Job] = []
    seen_urls: set[str] = set()

    for keyword in GOVT_CANADA_KEYWORDS:
        url = _RSS_URL.format(keyword=urllib.request.quote(keyword))
        req = urllib.request.Request(url, headers={"User-Agent": "InternHub/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        root = ET.fromstring(content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        # Try Atom format first, then RSS
        entries = root.findall(".//atom:entry", ns) or root.findall(".//item")
        for entry in entries:
            title_el = entry.find("atom:title", ns) or entry.find("title")
            link_el = entry.find("atom:link", ns) or entry.find("link")
            summary_el = entry.find("atom:summary", ns) or entry.find("description")

            title = title_el.text if title_el is not None else ""
            link = (link_el.get("href") or link_el.text) if link_el is not None else ""
            description = summary_el.text if summary_el is not None else ""

            if not title or not link or link in seen_urls:
                continue
            seen_urls.add(link)

            job: Job = {
                "id": make_job_id("gc", "Government of Canada", title, link),
                "title": title,
                "company": "Government of Canada",
                "location": "Canada",
                "url": link,
                "date_posted": "",
                "description": (description or "")[:500],
                "source": "GovtCanada",
            }
            if passes_filters(job, "public_sector"):
                jobs.append(job)

    return jobs


def _scrape_playwright() -> list[Job]:
    """Search jobs.gc.ca via Playwright for each configured keyword."""
    jobs: list[Job] = []
    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        for keyword in GOVT_CANADA_KEYWORDS:
            try:
                page.goto(
                    f"https://emploisfp-psjobs.cfp-psc.gc.ca/psrs-srfp/applicant/page2710"
                    f"?searchButton=Search&lang=en&keyword={urllib.request.quote(keyword)}",
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
