# tracker/scrapers/playwright_jobs.py
#
# Scrapes Meta and Tesla career pages using Playwright.
# Both sites are JavaScript SPAs with no public JSON API.
#
# Requires: pip install playwright && playwright install chromium
# If Playwright is not installed, this scraper logs a warning and returns [].
#
# Each company scraper is gated by PLAYWRIGHT_JOBS_ENABLED in config.py.

from tracker.config import BIG_TECH_SEARCH_QUERY, PLAYWRIGHT_JOBS_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

# Try to import Playwright at module load time.
# If unavailable, all functions return [] with a one-time warning.
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def scrape() -> list[Job]:
    if not PLAYWRIGHT_AVAILABLE:
        print(
            "[playwright_jobs] WARNING: Playwright not installed. "
            "Run: pip install playwright && playwright install chromium"
        )
        return []

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

        if PLAYWRIGHT_JOBS_ENABLED.get("meta"):
            try:
                jobs.extend(_scrape_meta(page))
            except Exception as exc:
                print(f"[playwright_jobs/meta] WARNING: {exc}")

        if PLAYWRIGHT_JOBS_ENABLED.get("tesla"):
            try:
                jobs.extend(_scrape_tesla(page))
            except Exception as exc:
                print(f"[playwright_jobs/tesla] WARNING: {exc}")

        browser.close()
    return jobs


def _scrape_meta(page) -> list[Job]:
    """Scrape software intern listings from Meta Careers."""
    page.goto("https://www.metacareers.com/jobs/", wait_until="networkidle", timeout=30000)

    # Search for software intern roles
    try:
        search_box = page.locator('input[placeholder*="Search"]').first
        search_box.fill(BIG_TECH_SEARCH_QUERY)
        search_box.press("Enter")
        page.wait_for_timeout(3000)
    except Exception:
        pass  # Search box may not be present; fall through to parse what's loaded

    jobs: list[Job] = []
    # Job cards are typically <a> elements with a role title inside
    job_cards = page.locator("a[href*='/jobs/']").all()

    for card in job_cards[:30]:  # cap at 30 to avoid runaway scraping
        try:
            href = card.get_attribute("href") or ""
            if not href.startswith("http"):
                href = "https://www.metacareers.com" + href
            title = card.inner_text().strip().split("\n")[0]
            if not title or len(title) > 200:
                continue
            job: Job = {
                "id": make_job_id("meta", "Meta", title, href),
                "title": title,
                "company": "Meta",
                "location": "Remote",  # Meta career pages often don't expose location in card
                "url": href,
                "date_posted": "",
                "description": "",
                "source": "Meta",
            }
            if passes_filters(job, "big_tech"):
                jobs.append(job)
        except Exception:
            continue

    return jobs


def _scrape_tesla(page) -> list[Job]:
    """Scrape software intern listings from Tesla Careers."""
    page.goto(
        "https://www.tesla.com/careers/search#/?query=software+intern",
        wait_until="networkidle",
        timeout=30000,
    )
    page.wait_for_timeout(3000)

    jobs: list[Job] = []
    job_cards = page.locator("a[href*='/careers/']").all()

    for card in job_cards[:30]:
        try:
            href = card.get_attribute("href") or ""
            if not href.startswith("http"):
                href = "https://www.tesla.com" + href
            title = card.inner_text().strip().split("\n")[0]
            if not title or len(title) > 200:
                continue
            job: Job = {
                "id": make_job_id("tesla", "Tesla", title, href),
                "title": title,
                "company": "Tesla",
                "location": "Remote",
                "url": href,
                "date_posted": "",
                "description": "",
                "source": "Tesla",
            }
            if passes_filters(job, "big_tech"):
                jobs.append(job)
        except Exception:
            continue

    return jobs
