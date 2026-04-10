# tracker/scrapers/playwright_jobs.py
#
# Scrapes Meta and Tesla career pages using Playwright.
#
# Meta: Uses response interception to capture the GraphQL API response
# at metacareers.com/graphql. The old CSS selector approach broke when
# Meta redesigned their careers SPA in 2026-04.
#
# Tesla: Blocked by Cloudflare bot protection as of 2026-04. Returns []
# with a warning. Re-test on future runs; may require playwright-stealth
# or a manual check of their careers page for a public API.
#
# Requires: pip install playwright && playwright install chromium
# If Playwright is not installed, this scraper logs a warning and returns [].
#
# Each company scraper is gated by PLAYWRIGHT_JOBS_ENABLED in config.py.

from tracker.config import PLAYWRIGHT_JOBS_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

# Try to import Playwright at module load time.
# If unavailable, all functions return [] with a one-time warning.
try:
    from playwright.sync_api import sync_playwright
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
            # Tesla blocks headless Chromium via Cloudflare as of 2026-04.
            # Skipping to avoid wasting time on a guaranteed Access Denied.
            print(
                "[playwright_jobs/tesla] WARNING: Tesla careers page blocks headless "
                "Chromium (Cloudflare). Skipping. Re-test manually or find a public API."
            )

        browser.close()
    return jobs


def _scrape_meta(page) -> list[Job]:
    """
    Scrape Meta job listings by intercepting their GraphQL API response.

    Meta redesigned their careers SPA in 2026-04; the old CSS selector
    (a[href*='/jobs/']) no longer finds job cards. Their page makes a
    GraphQL call to /graphql on load; we intercept the response and parse
    the structured JSON directly.

    Response shape (2026-04):
      {"data": {"job_search_with_featured_jobs": {"all_jobs": [
        {"id": "...", "title": "...", "locations": ["City, ST"], ...}
      ]}}}

    Job URL: https://www.metacareers.com/jobs/{id}/
    """
    captured: list[dict] = []

    def _on_response(resp):
        if "metacareers.com/graphql" not in resp.url:
            return
        try:
            body = resp.json()
            job_list = (
                body.get("data", {})
                    .get("job_search_with_featured_jobs", {})
                    .get("all_jobs", [])
            )
            if job_list:
                captured.extend(job_list)
        except Exception:
            pass

    page.on("response", _on_response)
    page.goto(
        "https://www.metacareers.com/jobs/?q=software+intern",
        wait_until="networkidle",
        timeout=30000,
    )
    page.wait_for_timeout(2000)
    page.remove_listener("response", _on_response)

    jobs: list[Job] = []
    seen_ids: set[str] = set()
    for item in captured[:50]:
        try:
            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            if not job_id or not title or job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            locs = item.get("locations", [])
            location = locs[0] if locs else "Remote"
            job_url = f"https://www.metacareers.com/jobs/{job_id}/"
            job: Job = {
                "id": make_job_id("meta", "Meta", title, job_url),
                "title": title,
                "company": "Meta",
                "location": location,
                "url": job_url,
                "date_posted": "",
                "description": "",
                "source": "Meta",
            }
            if passes_filters(job, "big_tech"):
                jobs.append(job)
        except Exception:
            continue

    return jobs
