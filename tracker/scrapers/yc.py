# tracker/scrapers/yc.py
#
# Scrapes job listings from YC's Work at a Startup platform.
# workatastartup.com is a React SPA with no stable public JSON API.
# The previous /jobs.json endpoint returned HTTP 500 as of 2026-04.
#
# Requires: pip install playwright && playwright install chromium
# If Playwright is not installed, this scraper logs a warning and returns [].

from tracker.config import PLAYWRIGHT_JOBS_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_JOBS_URL = "https://www.workatastartup.com/jobs?q=intern"
_BASE_URL  = "https://www.workatastartup.com"

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def scrape() -> list[Job]:
    if not PLAYWRIGHT_JOBS_ENABLED.get("yc"):
        return []
    if not PLAYWRIGHT_AVAILABLE:
        print(
            "[yc] WARNING: Playwright not installed. "
            "Run: pip install playwright && playwright install chromium"
        )
        return []
    try:
        return _scrape_playwright()
    except Exception as exc:
        print(f"[yc] WARNING: Playwright scraper failed: {exc}")
        return []


def _scrape_playwright() -> list[Job]:
    jobs: list[Job] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.goto(_JOBS_URL, wait_until="networkidle", timeout=30000)

        try:
            page.wait_for_selector("a[href*='/jobs/']", timeout=15000)
        except Exception:
            pass  # proceed with whatever rendered

        job_cards = page.locator("a[href*='/jobs/']").all()

        for card in job_cards[:50]:  # cap to avoid runaway scraping
            try:
                href = card.get_attribute("href") or ""
                if not href:
                    continue
                if href.startswith("/"):
                    href = _BASE_URL + href
                if not href.startswith("http"):
                    continue

                raw_text = card.inner_text().strip()
                lines = [ln.strip() for ln in raw_text.split("\n") if ln.strip()]
                if not lines:
                    continue

                title = lines[0]
                if not title or len(title) > 200:
                    continue

                company_name = lines[1] if len(lines) > 1 else ""

                # Best-effort location: find a line with a known location keyword
                location = ""
                for ln in lines[2:]:
                    lower = ln.lower()
                    if any(kw in lower for kw in (
                        "remote", "san francisco", "new york", "toronto",
                        "london", "canada", "usa", "united states", ", "
                    )):
                        location = ln
                        break

                job: Job = {
                    "id": make_job_id("yc", company_name, title, href),
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "url": href,
                    "date_posted": "",
                    "description": raw_text[:500],
                    "source": "YC",
                }

                if passes_filters(job, "community"):
                    jobs.append(job)

            except Exception:
                continue  # skip malformed cards

        browser.close()

    return jobs
