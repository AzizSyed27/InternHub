# tracker/scrapers/yc.py
#
# Scrapes internship listings from YC's Work at a Startup platform.
# workatastartup.com is a React SPA with no interceptable JSON API —
# job data is server-rendered directly into the DOM.
#
# URL: workatastartup.com/internships — dedicated internship listing page,
# shows only intern roles (unlike the /companies filter URL which shows all
# jobs at companies that happen to have intern openings).
#
# Authentication: if YC_EMAIL + YC_PASSWORD are set in .env, the scraper logs
# in via account.ycombinator.com to access the full listing (~72 jobs).
# Without credentials, falls back to the 15 jobs visible to logged-out users.
#
# Login form selectors (confirmed 2026-04):
#   Email:    #ycid-input   (type=text, name=username)
#   Password: #password-input
#   Submit:   button[type="submit"]
#
# DOM structure (confirmed 2026-04):
#   Job link:     a[href*='/jobs/'] — inner text is the job title
#   Company link: sibling a[href*='/companies/'] span.font-bold — company name
#   Location:     last •-delimited bullet in the card (after salary range)
#
# Requires: pip install playwright && playwright install chromium
# If Playwright is not installed, this scraper logs a warning and returns [].

import os

from tracker.config import PLAYWRIGHT_JOBS_ENABLED
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_JOBS_URL  = "https://www.workatastartup.com/internships"
_LOGIN_URL = (
    "https://account.ycombinator.com/authenticate"
    "?continue=https%3A%2F%2Fwww.workatastartup.com%2F"
)
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


def _login(page, email: str, password: str) -> bool:
    """Log into YC account. Returns True on success, False on failure.

    After submit the page stays at account.ycombinator.com (session cookie set
    but redirect requires a follow-up navigation). We just wait for load state
    and then navigate to workatastartup.com directly — the cookie carries over.
    """
    try:
        page.goto(_LOGIN_URL, wait_until="load", timeout=20000)
        page.wait_for_timeout(1000)
        page.fill("#ycid-input", email)
        page.fill("#password-input", password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("load", timeout=20000)
        page.wait_for_timeout(1500)
        # Confirm we left the /authenticate page (any YC account page = success)
        if "/authenticate" in page.url:
            print("[yc] WARNING: Still on login page — credentials may be wrong")
            return False
        print("[yc] Logged in successfully.")
        return True
    except Exception as exc:
        print(f"[yc] WARNING: Login failed ({exc}) — falling back to unauthenticated scraping")
        return False


def _scrape_playwright() -> list[Job]:
    yc_email    = os.getenv("YC_EMAIL", "")
    yc_password = os.getenv("YC_PASSWORD", "")

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

        if yc_email and yc_password:
            _login(page, yc_email, yc_password)
        else:
            print("[yc] INFO: YC_EMAIL/YC_PASSWORD not set — scraping without login (15 jobs max)")

        # Use "load" not "networkidle" — SPA keeps persistent connections open.
        page.goto(_JOBS_URL, wait_until="load", timeout=30000)
        page.wait_for_timeout(3000)

        items = page.evaluate("""() => {
            const results = [];
            const jobLinks = document.querySelectorAll("a[href*='/jobs/']");
            jobLinks.forEach(jobLink => {
                const title = jobLink.innerText.trim();
                if (!title) return;

                const href = jobLink.getAttribute('href') || '';

                // Company name: two DOM structures depending on auth state.
                // Logged-in:  company link contains <img alt="Company Name"> (text is empty)
                // Logged-out: company link contains <span class="font-bold">Company (W25)</span>
                let company = '';
                let el = jobLink.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!el) break;
                    const compImg = el.querySelector("a[href*='/companies/'] img[alt]");
                    if (compImg && compImg.alt) {
                        company = compImg.alt.trim();
                        break;
                    }
                    const compSpan = el.querySelector("a[href*='/companies/'] span.font-bold");
                    if (compSpan) {
                        // Strip YC batch suffix e.g. "Browser Use (W25)" -> "Browser Use"
                        company = compSpan.innerText.trim().replace(/\\s*\\([A-Z]\\d+\\)$/, '');
                        break;
                    }
                    el = el.parentElement;
                }

                // Location: first <span> in the metadata div after the job title container
                // (works for logged-in view). Falls back to last •-delimited bullet
                // for the logged-out compact card layout.
                let location = '';
                const metaDiv = jobLink.parentElement?.nextElementSibling;
                if (metaDiv) {
                    const firstSpan = metaDiv.querySelector('span');
                    if (firstSpan) location = firstSpan.innerText.trim();
                }
                if (!location) {
                    let cardEl = jobLink.parentElement;
                    for (let i = 0; i < 5; i++) {
                        if (!cardEl) break;
                        const text = cardEl.innerText || '';
                        const parts = text.split('•').map(s => s.trim()).filter(Boolean);
                        const last = parts[parts.length - 1] || '';
                        if (last && last.length < 100 && !last.includes('$') &&
                            !last.includes('Engineering') && !last.includes('monthly')) {
                            location = last;
                            break;
                        }
                        cardEl = cardEl.parentElement;
                    }
                }

                results.push({ title, href, company, location });
            });
            return results;
        }""")

        browser.close()

    if not items:
        print("[yc] WARNING: 0 job cards found — selector a[href*='/jobs/'] may have changed")
        return []

    jobs: list[Job] = []
    seen_hrefs: set[str] = set()

    for item in items[:100]:
        try:
            href = item.get("href", "")
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            title    = item.get("title", "")
            company  = item.get("company", "")
            location = item.get("location", "")

            if not title or len(title) > 200:
                continue

            job_url = _BASE_URL + href if href.startswith("/") else href

            job: Job = {
                "id":          make_job_id("yc", company, title, job_url),
                "title":       title,
                "company":     company,
                "location":    location,
                "url":         job_url,
                "date_posted": "",
                "description": "",
                "source":      "YC",
            }
            if passes_filters(job, "github"):  # skip location filter — YC is a curated list like SimplifyJobs
                jobs.append(job)
        except Exception:
            continue

    return jobs
