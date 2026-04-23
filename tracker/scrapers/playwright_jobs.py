# tracker/scrapers/playwright_jobs.py
#
# Scrapes Meta, Tesla, Google, Apple, and Uber career pages using Playwright.
#
# Meta: Uses response interception to capture the GraphQL API response
# at metacareers.com/graphql. The old CSS selector approach broke when
# Meta redesigned their careers SPA in 2026-04.
#
# Tesla: Blocked by Cloudflare bot protection as of 2026-04. Returns []
# with a warning. Re-test on future runs; may require playwright-stealth
# or a manual check of their careers page for a public API.
#
# Google: DOM scraper (old careers.google.com JSON API deprecated 2026-04).
# Paginates via "Next" button (aria-label) or infinite scroll fallback.
#
# Apple: DOM scraper added 2026-04. The old /api/role/search endpoint
# (big_tech.py) returns a 404 redirect; /api/v1/search requires CSRF auth
# that doesn't fire in headless mode. Job data is rendered into the DOM.
# Navigates to en-ca/search filtered to Canada+USA+Software+Internships.
#
# Uber: Response interceptor on www.uber.com/ca/en/careers/list/ (SPA).
# jobs.uber.com is Cloudflare-blocked; www.uber.com is accessible.
#
# Google for Jobs: DOM scraper on google.com/search?...&ibp=htl;jobs — the
# aggregator vertical, NOT careers.google.com (which is _scrape_google).
# Iterates a short list of SWE-intern query variants, clicks each card to
# read the detail pane, and picks the "Apply on {company domain}" link. Uses
# only semantic selectors (role=, aria-*) because classnames are obfuscated.
# Bails on recaptcha / consent interstitials without retrying. Default ON
# but gated at a 4-hour interval to minimize bot-detection exposure.
#
# Requires: pip install playwright && playwright install chromium
# If Playwright is not installed, this scraper logs a warning and returns [].
#
# Each company scraper is gated by PLAYWRIGHT_JOBS_ENABLED in config.py.

from urllib.parse import urlparse

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

        if PLAYWRIGHT_JOBS_ENABLED.get("apple"):
            try:
                jobs.extend(_scrape_apple(page))
            except Exception as exc:
                print(f"[playwright_jobs/apple] WARNING: {exc}")

        if PLAYWRIGHT_JOBS_ENABLED.get("uber"):
            try:
                jobs.extend(_scrape_uber(page))
            except Exception as exc:
                print(f"[playwright_jobs/uber] WARNING: {exc}")

        if PLAYWRIGHT_JOBS_ENABLED.get("intern_list"):
            try:
                jobs.extend(_scrape_intern_list(page))
            except Exception as exc:
                print(f"[playwright_jobs/intern_list] WARNING: {exc}")

        if PLAYWRIGHT_JOBS_ENABLED.get("google_jobs"):
            try:
                jobs.extend(_scrape_google_jobs(page))
            except Exception as exc:
                print(f"[playwright_jobs/google_jobs] WARNING: {exc}")

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
    Scrape Google internship listings via DOM parsing, exhausting all pages.

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

    Pagination: tries "Next" button first (aria-label="Go to next page"), then falls
    back to infinite-scroll detection. MAX_PAGES / MAX_SCROLL_ROUNDS guard against
    runaway loops at peak recruiting season when result counts are high.
    """
    _BASE = "https://www.google.com/about/careers/applications/"
    _MAX_PAGES = 10        # cap for "Next" button pagination
    _MAX_SCROLL_ROUNDS = 15  # cap for infinite-scroll attempts

    page.goto(
        _BASE + "jobs/results?employment_type=INTERN&q=software",
        wait_until="networkidle",
        timeout=30000,
    )
    page.wait_for_timeout(2000)

    jobs: list[Job] = []
    seen_urls: set[str] = set()

    def _harvest_cards():
        """Parse all currently visible job cards and append new ones to jobs."""
        for card in page.locator("li.lLd3Je").all():
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

    _harvest_cards()

    if not seen_urls:
        print("[playwright_jobs/google] WARNING: 0 job cards found — selector li.lLd3Je may have changed")
        return []

    # --- Stage 1: "Next" button pagination ---
    # ARIA attributes are semantically stable even when obfuscated class names change.
    next_btn = page.locator('[aria-label="Go to next page"]')
    if next_btn.count() > 0:
        for _ in range(_MAX_PAGES - 1):
            try:
                if next_btn.count() == 0 or not next_btn.first.is_visible():
                    break
                next_btn.first.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                _harvest_cards()
            except Exception:
                break  # stop pagination on any error; return what we have
    else:
        # --- Stage 2: Infinite scroll fallback ---
        for _ in range(_MAX_SCROLL_ROUNDS):
            prev = len(seen_urls)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2500)
            _harvest_cards()
            if len(seen_urls) == prev:
                break  # no new cards loaded; we've reached the end

    return jobs


def _scrape_uber(page) -> list[Job]:
    """
    Scrape Uber internship listings by intercepting XHR responses on the careers SPA.

    URL: https://www.uber.com/ca/en/careers/list/?query=Intern&department=University
      - "University" department filter surfaces intern/co-op postings
      - jobs.uber.com is blocked by Cloudflare (403); www.uber.com is accessible

    Approach: response interception (same pattern as _scrape_meta).
    The SPA fetches job data via one or more XHR/fetch calls after page load.
    We capture all JSON responses from uber.com and heuristically find the
    one that contains a list of job objects (identified by a "title" field).

    Job URL (confirmed from uber.com search results):
      https://www.uber.com/global/en/careers/list/{jobId}/
    """
    captured: list[dict] = []

    def _on_response(resp):
        if "uber.com" not in resp.url:
            return
        try:
            body = resp.json()
        except Exception:
            return
        # Find a list of job objects: check top-level, then one level deep
        jobs_list = None
        if isinstance(body, list) and body and isinstance(body[0], dict) and "title" in body[0]:
            jobs_list = body
        elif isinstance(body, dict):
            for val in body.values():
                if isinstance(val, list) and val and isinstance(val[0], dict) and "title" in val[0]:
                    jobs_list = val
                    break
                if isinstance(val, dict):
                    for inner_val in val.values():
                        if isinstance(inner_val, list) and inner_val and isinstance(inner_val[0], dict) and "title" in inner_val[0]:
                            jobs_list = inner_val
                            break
                    if jobs_list:
                        break
        if jobs_list:
            captured.extend(jobs_list)

    page.on("response", _on_response)
    page.goto(
        "https://www.uber.com/ca/en/careers/list/?query=Intern&department=University",
        wait_until="networkidle",
        timeout=30000,
    )
    page.wait_for_timeout(2000)
    page.remove_listener("response", _on_response)

    if not captured:
        print(
            "[playwright_jobs/uber] WARNING: 0 jobs captured — "
            "XHR response structure may have changed; inspect Network tab on "
            "www.uber.com/ca/en/careers/list/?query=Intern&department=University"
        )
        return []

    jobs: list[Job] = []
    seen_ids: set[str] = set()
    for item in captured[:100]:
        try:
            job_id = str(
                item.get("id", "") or item.get("jobId", "") or item.get("requisitionId", "")
            )
            title = item.get("title", "") or item.get("jobTitle", "")
            if not job_id or not title or job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            location = item.get("location", "") or item.get("city", "") or ""
            if isinstance(location, dict):
                location = location.get("name", "") or location.get("city", "") or ""
            job_url = f"https://www.uber.com/global/en/careers/list/{job_id}/"
            job: Job = {
                "id": make_job_id("uber", "Uber", title, job_url),
                "title": title,
                "company": "Uber",
                "location": str(location),
                "url": job_url,
                "date_posted": "",
                "description": "",
                "source": "Uber",
            }
            if passes_filters(job, "big_tech"):
                jobs.append(job)
        except Exception:
            continue

    return jobs


def _scrape_apple(page) -> list[Job]:
    """
    Scrape Apple internship listings via DOM parsing with pagination.

    Apple's careers site is a React SPA. The old /api/role/search endpoint (big_tech.py)
    returns a 404 redirect. The internal /api/v1/search endpoint requires CSRF auth that
    doesn't fire in headless mode — job data is rendered directly into the DOM instead.

    Target URL (confirmed 2026-04):
      https://jobs.apple.com/en-ca/search?location=canada-CANC+united-states-USA
        &key=Software&team=internships-STDNT-INTRN

    DOM structure (confirmed 2026-04):
      Job list:    ul#search-job-list
      Job links:   a[href*='/details/'] — each card has TWO links (title + "See full role
                   description"); the title link has a .job-posted-date sibling; the second
                   link does not — skip any link whose date sibling is empty
      Location:    span.table--advanced-search__location-sub
      Date:        span.job-posted-date
      Pagination:  nav.rc-pagination — "Next Page" button (aria-label)
    """
    _SEARCH_URL = (
        "https://jobs.apple.com/en-ca/search"
        "?location=canada-CANC+united-states-USA"
        "&key=Software"
        "&team=internships-STDNT-INTRN"
    )
    _MAX_PAGES = 20

    # Use "load" (not "networkidle") — Apple's page keeps persistent analytics
    # connections open that prevent networkidle from ever being reached.
    # Instead, wait for the first job card link to appear in the DOM, which
    # confirms the SPA has fetched and rendered the results.
    page.goto(_SEARCH_URL, wait_until="load", timeout=30000)
    page.wait_for_selector(
        "ul#search-job-list a[href*='/details/']",
        state="visible",
        timeout=15000,
    )
    page.wait_for_timeout(500)

    jobs: list[Job] = []
    seen_hrefs: set[str] = set()

    def _harvest():
        items = page.evaluate("""() => {
            const results = [];
            const links = document.querySelectorAll("ul#search-job-list a[href*='/details/']");
            links.forEach(a => {
                const li = a.closest('li');
                if (!li) return;
                const dateEl = li.querySelector('.job-posted-date');
                // Each card has two <a> tags with the same href: the title link
                // (which has a .job-posted-date sibling) and "See full role description"
                // (no date sibling). Skip the second one.
                if (!dateEl || !dateEl.innerText.trim()) return;
                const locEl = li.querySelector('.table--advanced-search__location-sub');
                results.push({
                    title:    a.innerText.trim(),
                    href:     a.getAttribute('href'),
                    location: locEl ? locEl.innerText.trim() : '',
                    date:     dateEl.innerText.trim(),
                });
            });
            return results;
        }""")
        for item in items:
            href = (item.get("href") or "").split("?")[0]
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            title = item.get("title", "")
            if not title:
                continue
            job_url = "https://jobs.apple.com" + href
            job: Job = {
                "id": make_job_id("apple", "Apple", title, job_url),
                "title": title,
                "company": "Apple",
                "location": item.get("location", ""),
                "url": job_url,
                "date_posted": item.get("date", ""),
                "description": "",
                "source": "Apple",
            }
            if passes_filters(job, "big_tech"):
                jobs.append(job)

    _harvest()

    if not seen_hrefs:
        print("[playwright_jobs/apple] WARNING: 0 job cards found — ul#search-job-list selector may have changed")
        return []

    # Paginate via "Next Page" button (aria-label is semantically stable)
    next_btn = page.locator('[aria-label="Next Page"]')
    for _ in range(_MAX_PAGES - 1):
        try:
            if next_btn.count() == 0 or not next_btn.first.is_enabled():
                break
            next_btn.first.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            _harvest()
        except Exception:
            break

    return jobs


def _scrape_intern_list(page) -> list[Job]:
    """
    Scrape intern-list.com SWE internship listings (US + Canada) via DOM parsing.

    intern-list.com (powered by Jobright) embeds job tables from jobright.ai.
    We navigate directly to the embed URLs to avoid dealing with tab interactions.

    Embed URLs (confirmed 2026-04):
      US:     https://jobright.ai/minisites-jobs/intern/us/swe?embed=true
      Canada: https://jobright.ai/minisites-jobs/intern/ca/swe?embed=true

    DOM structure (confirmed 2026-04):
      Rows:     tr[data-index]             — stable data attribute; virtual scroll
      Title:    td:nth-child(2) innerText  — cell index 1
      Location: td:nth-child(6) innerText  — cell index 5 (may have "Multi Locations: ..." prefix)
      Company:  td:nth-child(7) innerText  — cell index 6
      Apply:    a[href*="/jobs/info/"]     — links to jobright.ai job detail page

    Pagination: virtual scroll — table renders ~20 rows per viewport.
    Scroll the nearest overflow container until no new rows appear.

    Tier: "github" (same as SimplifyJobs — aggregate curated board; bypass location filter).
    Job URLs: jobright.ai/jobs/info/{id} (UTM params stripped).
    """
    _EMBED_URLS = [
        "https://jobright.ai/minisites-jobs/intern/us/swe?embed=true",
        "https://jobright.ai/minisites-jobs/intern/ca/swe?embed=true",
    ]
    _MAX_SCROLL_ROUNDS = 30

    jobs: list[Job] = []

    for embed_url in _EMBED_URLS:
        # Per-URL dedup set: the US and CA pages can share hrefs for the same
        # posting, and a shared set would silently drop Canadian rows whose
        # href was already seen on the US pass, plus trip the scroll-loop
        # early-exit on a viewport of US-duplicates before reaching Canada-only
        # rows further down.
        seen_hrefs: set[str] = set()

        # wait_until="load" (not "networkidle") — jobright.ai holds persistent
        # analytics connections similar to Apple/YC, so networkidle can 30s-
        # timeout on one URL and poison the whole intern_list run. The
        # wait_for_selector below handles the actual "rows visible" wait.
        page.goto(embed_url, wait_until="load", timeout=30000)
        page.wait_for_selector("tr[data-index]", state="visible", timeout=15000)
        page.wait_for_timeout(1000)

        def _harvest():
            items = page.evaluate("""() => {
                return [...document.querySelectorAll('tr[data-index]')].map(tr => {
                    const cells = tr.querySelectorAll('td');
                    const applyLink = tr.querySelector('a[href*="/jobs/info/"]');
                    return {
                        title:    cells[1] ? cells[1].innerText.trim() : '',
                        location: cells[5] ? cells[5].innerText.trim() : '',
                        company:  cells[6] ? cells[6].innerText.trim() : '',
                        href:     applyLink ? applyLink.getAttribute('href') : null,
                    };
                }).filter(r => r.title && r.href);
            }""")
            for item in items:
                href = item["href"].split("?")[0]  # strip UTM params for clean dedup key
                if not href or href in seen_hrefs:
                    continue
                seen_hrefs.add(href)
                title = item["title"]
                company = item["company"] or "Unknown"
                # "Multi Locations: Seattle, WA; United States" → "Seattle, WA"
                location = item["location"] or ""
                if location.startswith("Multi Locations: "):
                    location = location[len("Multi Locations: "):].split(";")[0].strip()
                job: Job = {
                    "id": make_job_id("intern_list", company, title, href),
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": href,
                    "date_posted": "",
                    "description": "",
                    "source": "intern-list.com",
                }
                if passes_filters(job, "github"):
                    jobs.append(job)

        _harvest()

        # Scroll the virtual table's viewport div to trigger row loading.
        # Container is 2 levels above the table: div[overflowY=auto] (index_bodyViewport).
        # Walks up the DOM to find the nearest scrollable ancestor as a fallback.
        for _ in range(_MAX_SCROLL_ROUNDS):
            prev = len(seen_hrefs)
            page.evaluate("""() => {
                const table = document.querySelector('tr[data-index]')?.closest('table');
                let el = table?.parentElement;
                while (el) {
                    const oy = window.getComputedStyle(el).overflowY;
                    if (oy === 'auto' || oy === 'scroll') {
                        el.scrollTop = el.scrollHeight;
                        return;
                    }
                    el = el.parentElement;
                }
                window.scrollTo(0, document.body.scrollHeight);
            }""")
            page.wait_for_timeout(1500)
            _harvest()
            if len(seen_hrefs) == prev:
                break  # no new rows loaded; reached end of virtual scroll

        # Per-URL summary — useful signal if the CA pass starts returning 0
        # hrefs (broken selector / page.goto timeout) which historically masked
        # Canadian-only postings like RBC Global Asset Management (2026-04).
        print(
            f"[intern_list] {embed_url}: "
            f"{len(seen_hrefs)} unique hrefs, {len(jobs)} jobs accumulated"
        )

    if not jobs:
        print(
            "[playwright_jobs/intern_list] WARNING: 0 jobs found — "
            "check tr[data-index] selector on jobright.ai/minisites-jobs/intern/us/swe?embed=true"
        )

    return jobs


def _scrape_google_jobs(page) -> list[Job]:
    """
    Scrape the Google for Jobs aggregator at google.com/search?...&ibp=htl;jobs.

    NOT careers.google.com — that is `_scrape_google()` above, which covers only
    Google's own postings. This scraper surfaces the aggregator vertical that
    indexes JobPosting schema.org markup from across the web (company sites,
    Greenhouse, Workday, LinkedIn, Indeed). Heavy overlap with existing ATS
    scrapers is expected; marginal value is postings from small/mid companies
    that are not individually integrated.

    Strategy (confirmed 2026-04):
      - Loops three SWE-intern query variants; dedupes by final apply URL
      - Uses only semantic selectors (role=list, role=listitem, role=heading,
        aria-level); Google's CSS classnames are obfuscated and churn often
      - Reads title / company / location from each card's text (avoids the
        fragile detail-pane walk). Location line typically looks like
        "City, Region · via Source" — split on "·" to drop the via-suffix.
      - Clicks the card to render the right-hand detail pane, then harvests
        Apply links with aria-label or text containing "apply" and picks one
        by priority: (1) company-domain match → (2) non-aggregator host →
        (3) first available link. Aggregator hosts (LinkedIn, Indeed, etc.)
        are deprioritized to prefer the company's own careers page.
      - Bails on recaptcha / consent interstitials and returns []; does NOT
        retry in-session so the IP does not get hammered.

    Fragility tripwires:
      - If >30% of harvested cards have empty company, selectors have drifted:
        WARN and return [] rather than emitting low-quality postings.
      - If 0 jobs total → WARN with hints for where to re-verify in DevTools.

    Gated by PLAYWRIGHT_JOBS_ENABLED["google_jobs"]; runs on a 4-hour
    SCRAPER_INTERVAL to minimize Google bot-detection exposure of the
    residential IP. tier="github" bypasses LOCATIONS_INCLUDE — this is an
    aggregator like SimplifyJobs / intern-list, not a Canada-filtered source.
    """
    _URL_TEMPLATE = "https://www.google.com/search?q={q}&ibp=htl;jobs"
    _QUERIES = [
        "software engineering intern",
        "software internship",
        "software developer intern",
    ]
    _MAX_SCROLL_ROUNDS = 8
    _MAX_CARDS_PER_QUERY = 25
    _AGGREGATOR_HOSTS = {
        "linkedin.com", "www.linkedin.com",
        "indeed.com", "www.indeed.com",
        "glassdoor.com", "www.glassdoor.com",
        "ziprecruiter.com", "www.ziprecruiter.com",
        "simplyhired.com", "www.simplyhired.com",
    }

    def _is_challenge_page() -> bool:
        """True for hard challenges only (recaptcha, /sorry/, 'unusual traffic').
        Does NOT treat the cookie-consent interstitial as a challenge — that is
        handled by _dismiss_consent_if_needed() below."""
        try:
            url = (page.url or "").lower()
            if "/sorry/" in url:
                return True
            if page.locator('iframe[src*="recaptcha"]').count() > 0:
                return True
            body_text = (page.locator("body").inner_text(timeout=2000) or "").lower()
            if "unusual traffic" in body_text:
                return True
        except Exception:
            pass
        return False

    def _dismiss_consent_if_needed() -> bool:
        """Google's 'Before you continue to Google Search' interstitial is shown
        to fresh browser contexts without a CONSENT cookie. Click through it.
        Returns True if consent was dismissed OR not shown; False if still blocked
        after trying."""
        try:
            url = (page.url or "").lower()
            body_text = (page.locator("body").inner_text(timeout=2000) or "").lower()
        except Exception:
            return True  # can't read — assume we're OK and let downstream checks fire

        on_consent = "consent.google.com" in url or "before you continue" in body_text
        if not on_consent:
            return True

        # Prefer "Reject all" (avoids tracking-cookie burden); fall back to Accept.
        for selector in (
            'button:has-text("Reject all")',
            'button[aria-label="Reject all"]',
            'button:has-text("Accept all")',
            'button[aria-label="Accept all"]',
            'button:has-text("I agree")',
        ):
            try:
                btn = page.locator(selector).first
                if btn.count() == 0 or not btn.is_visible():
                    continue
                btn.click(timeout=5000)
                page.wait_for_load_state("load", timeout=15000)
                page.wait_for_timeout(1500)
                # Re-check: did we actually leave the consent page?
                new_url = (page.url or "").lower()
                if "consent.google.com" not in new_url:
                    return True
            except Exception:
                continue

        return False

    def _pick_apply_url(urls: list[str], company: str) -> str:
        if not urls:
            return ""
        company_slug = "".join(c for c in company.lower() if c.isalnum())
        if company_slug:
            for href in urls:
                host_alnum = "".join(
                    c for c in (urlparse(href).hostname or "").lower() if c.isalnum()
                )
                if company_slug in host_alnum:
                    return href
        for href in urls:
            host = (urlparse(href).hostname or "").lower()
            if host and host not in _AGGREGATOR_HOSTS:
                return href
        return urls[0]

    jobs: list[Job] = []
    seen_urls: set[str] = set()
    empty_company = 0
    total = 0

    try:
        page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
    except Exception:
        pass

    for query in _QUERIES:
        url = _URL_TEMPLATE.format(q=query.replace(" ", "+"))
        try:
            page.goto(url, wait_until="load", timeout=30000)
        except Exception as exc:
            print(f"[playwright_jobs/google_jobs] WARNING: goto failed for {query!r}: {exc}")
            continue
        page.wait_for_timeout(2500)

        if not _dismiss_consent_if_needed():
            print(
                "[playwright_jobs/google_jobs] WARNING: consent interstitial could not be "
                "dismissed (button selectors may have changed) — bailing."
            )
            return []

        if _is_challenge_page():
            print(
                "[playwright_jobs/google_jobs] WARNING: bot challenge detected "
                "(recaptcha / /sorry/ / unusual traffic) — bailing without retry."
            )
            return []

        rail = page.locator('div[role="main"] [role="list"]').first
        try:
            rail.wait_for(state="visible", timeout=10000)
        except Exception:
            # No list rendered for this query — skip to next
            continue

        # Scroll the jobs rail until no new cards load or we hit the cap
        for _ in range(_MAX_SCROLL_ROUNDS):
            prev = rail.locator('[role="listitem"]').count()
            try:
                rail.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            except Exception:
                break
            page.wait_for_timeout(1500)
            curr = rail.locator('[role="listitem"]').count()
            if curr == prev or curr >= _MAX_CARDS_PER_QUERY:
                break

        cards = rail.locator('[role="listitem"]').all()[:_MAX_CARDS_PER_QUERY]
        for card in cards:
            try:
                title_loc = card.locator('[role="heading"][aria-level="3"]').first
                if title_loc.count() == 0:
                    continue
                title = title_loc.inner_text().strip()
                if not title:
                    continue

                # Parse company + location from the card's visible text lines.
                card_text = card.inner_text() or ""
                lines = [ln.strip() for ln in card_text.splitlines() if ln.strip()]
                t_idx = next((i for i, ln in enumerate(lines) if ln == title), 0)
                company = ""
                location = ""
                for ln in lines[t_idx + 1 : t_idx + 4]:
                    if not company:
                        company = ln
                        continue
                    # Typical: "Mountain View, CA · via LinkedIn" → drop via-suffix
                    location = ln.split("·")[0].strip() if "·" in ln else ln
                    break

                total += 1
                if not company:
                    empty_company += 1

                try:
                    card.click(timeout=5000)
                    page.wait_for_timeout(1200)
                except Exception:
                    continue

                if _is_challenge_page():
                    print(
                        "[playwright_jobs/google_jobs] WARNING: challenge detected mid-run — bailing"
                    )
                    return []

                # Harvest apply links from whichever detail pane is now visible
                apply_urls: list[str] = []
                try:
                    for a in page.locator('a[href^="http"]').all():
                        try:
                            aria = (a.get_attribute("aria-label") or "").lower()
                            text = (a.inner_text() or "").lower()
                        except Exception:
                            continue
                        if "apply" not in aria and "apply" not in text:
                            continue
                        href = a.get_attribute("href") or ""
                        host = (urlparse(href).hostname or "").lower()
                        if "google." in host:
                            continue  # skip Google's own search/redirect links
                        if href and href not in apply_urls:
                            apply_urls.append(href)
                except Exception:
                    pass

                job_url = _pick_apply_url(apply_urls, company)
                if not job_url or job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                job: Job = {
                    "id": make_job_id("google_jobs", company or "unknown", title, job_url),
                    "title": title,
                    "company": company or "unknown",
                    "location": location,
                    "url": job_url,
                    "date_posted": "",
                    "description": "",
                    "source": "Google Jobs",
                }
                if passes_filters(job, "github"):
                    jobs.append(job)
            except Exception:
                continue

    # Fragility tripwire — detail/card selectors have drifted.
    if total >= 10 and (empty_company / total) > 0.3:
        print(
            f"[playwright_jobs/google_jobs] WARNING: {empty_company}/{total} cards had empty "
            "company — card selectors likely drifted. Returning []."
        )
        return []

    if not jobs:
        print(
            "[playwright_jobs/google_jobs] WARNING: 0 jobs — verify role=list / role=listitem "
            "still wrap cards on google.com/search?...&ibp=htl;jobs or check for challenge page."
        )

    return jobs
