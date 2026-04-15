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

        if PLAYWRIGHT_JOBS_ENABLED.get("google"):
            try:
                jobs.extend(_scrape_google(page))
            except Exception as exc:
                print(f"[playwright_jobs/google] WARNING: {exc}")

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


def _scrape_google(page) -> list[Job]:
    """
    Scrape Google internship listings via DOM parsing.

    Google's careers page is an Angular SPA at:
      https://www.google.com/about/careers/applications/jobs/results?employment_type=INTERN&q=software

    The old careers.google.com/api/jobs/jobs-v1/search/ endpoint is deprecated (301 → 404).
    Job data does not appear in any interceptable JSON response — it is rendered directly
    into the DOM. We parse the rendered job cards instead.

    DOM structure (confirmed 2026-04):
      Job cards:    li.lLd3Je
      Title:        h3.QJPWVe (inner text)
      Link:         a[href] — relative path like "jobs/results/{id}-{slug}?..."
      Location:     .wVoYLb inner text — "...\nplace\n{city, country}\nbar_chart\n..."
    """
    _BASE = "https://www.google.com/about/careers/applications/"
    page.goto(
        _BASE + "jobs/results?employment_type=INTERN&q=software",
        wait_until="networkidle",
        timeout=30000,
    )
    page.wait_for_timeout(2000)

    cards = page.locator("li.lLd3Je").all()
    if not cards:
        print("[playwright_jobs/google] WARNING: 0 job cards found — selector li.lLd3Je may have changed")
        return []

    jobs: list[Job] = []
    seen_urls: set[str] = set()
    for card in cards:
        try:
            title = card.locator("h3.QJPWVe").inner_text().strip()
            if not title:
                continue
            href = card.locator("a").first.get_attribute("href") or ""
            if not href:
                continue
            # href is relative: "jobs/results/{id}-{slug}?..."  — strip query params
            job_url = _BASE + href.split("?")[0]
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)
            # Location is in .wVoYLb text after the "place" icon marker
            wv_text = card.locator(".wVoYLb").first.inner_text()
            loc_parts = wv_text.split("place\n")
            location = loc_parts[1].split("\n")[0].strip() if len(loc_parts) > 1 else ""
            job: Job = {
                "id": make_job_id("google", "Google", title, job_url),
                "title": title,
                "company": "Google",
                "location": location,
                "url": job_url,
                "date_posted": "",
                "description": "",
                "source": "Google",
            }
            if passes_filters(job, "big_tech"):
                jobs.append(job)
        except Exception:
            continue

    return jobs
