# networking/linkedin_scraper.py
#
# LinkedIn browser automation via Playwright.
# Handles login, alumni page navigation, and profile visits.
#
# Rate limits (from config.py):
#   PAGE_LOAD_DELAY      — 3–7s between page navigations
#   PROFILE_VISIT_DELAY  — 8–15s between individual profile visits
#   MAX_PROFILES_PER_RUN — hard cap on profile visits per session
#
# IMPORTANT: This tool never sends any messages or connection requests.
# All outreach is done manually from the generated CSV.

import random
import time

from playwright.sync_api import Page, sync_playwright

from networking.config import (
    MAX_PROFILES_PER_RUN,
    PAGE_LOAD_DELAY,
    PROFILE_VISIT_DELAY,
)
from networking.profile_parser import Profile, parse_profile

_LINKEDIN_BASE = "https://www.linkedin.com"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login(page: Page, email: str, password: str) -> None:
    """
    Log into LinkedIn with the provided credentials.
    Raises an exception if login fails (wrong credentials, captcha, etc.).
    """
    page.goto(f"{_LINKEDIN_BASE}/login", wait_until="networkidle")
    page.fill("#username", email)
    page.fill("#password", password)
    page.click('button[type="submit"]')

    # Wait for redirect to feed — if login fails, we'll land on /login or /checkpoint
    page.wait_for_url("**/feed/**", timeout=15000)
    print("[linkedin] Logged in successfully.")


# ---------------------------------------------------------------------------
# Alumni URL construction
# ---------------------------------------------------------------------------

def get_alumni_url(school: str, company: str) -> str:
    """
    Construct the LinkedIn alumni search URL for a given school filtered by company.
    LinkedIn alumni pages: linkedin.com/school/{school-slug}/people/?currentCompany={company}
    School slug is the school name lowercased with spaces replaced by dashes.
    """
    school_slug = school.lower().replace(" ", "-").replace("(", "").replace(")", "")
    company_encoded = company.replace(" ", "%20")
    return (
        f"{_LINKEDIN_BASE}/school/{school_slug}/people/"
        f"?currentCompany={company_encoded}"
    )


# ---------------------------------------------------------------------------
# Alumni list scraping
# ---------------------------------------------------------------------------

def scrape_alumni_list(page: Page, school: str, company: str) -> list[str]:
    """
    Navigate to the alumni page for this school + company combination,
    and return a list of profile URLs found on the page.
    Returns an empty list on any error.
    """
    url = get_alumni_url(school, company)
    try:
        page.goto(url, wait_until="networkidle", timeout=20000)
        _random_delay(PAGE_LOAD_DELAY)

        # Profile cards on alumni pages link to /in/ profiles
        profile_links = page.locator("a[href*='/in/']").all()
        urls: list[str] = []
        seen: set[str] = set()

        for link in profile_links:
            href = link.get_attribute("href") or ""
            if "/in/" not in href:
                continue
            # Normalize: strip query params and anchors
            profile_url = href.split("?")[0].split("#")[0]
            if not profile_url.startswith("http"):
                profile_url = _LINKEDIN_BASE + profile_url
            if profile_url not in seen:
                seen.add(profile_url)
                urls.append(profile_url)

        return urls

    except Exception as exc:
        print(f"[linkedin] WARNING: could not load alumni page {url}: {exc}")
        return []


# ---------------------------------------------------------------------------
# Profile visit
# ---------------------------------------------------------------------------

def visit_profile(page: Page, url: str) -> "Profile | None":
    """
    Navigate to a LinkedIn profile page, wait for it to load, and parse it.
    Returns a Profile dict if the person matches all criteria, else None.
    Applies PROFILE_VISIT_DELAY before navigating.
    """
    _random_delay(PROFILE_VISIT_DELAY)
    try:
        page.goto(url, wait_until="networkidle", timeout=20000)
        _random_delay((1, 2))  # brief settle time
        return parse_profile(page, url)
    except Exception as exc:
        print(f"[linkedin] WARNING: failed to visit {url}: {exc}")
        return None


# ---------------------------------------------------------------------------
# High-level scrape runner
# ---------------------------------------------------------------------------

def run_scraper(
    email: str,
    password: str,
    schools: list[str],
    companies: list[str],
) -> list[Profile]:
    """
    Full scrape session:
      1. Login
      2. For each (school, company) pair, collect profile URLs
      3. Visit each profile (up to MAX_PROFILES_PER_RUN total)
      4. Return matched Profile objects

    This is the function called by networking/main.py.
    """
    matched_profiles: list[Profile] = []
    profile_urls: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # Step 1: Login
        login(page, email, password)

        # Step 2: Collect profile URLs
        for school in schools:
            for company in companies:
                if len(profile_urls) >= MAX_PROFILES_PER_RUN * 3:
                    # Collected enough candidates; stop browsing alumni pages
                    break
                print(f"[linkedin] Scraping: {school} × {company}")
                urls = scrape_alumni_list(page, school, company)
                profile_urls.extend(urls)
                _random_delay(PAGE_LOAD_DELAY)

        # Deduplicate
        seen: set[str] = set()
        unique_urls = [u for u in profile_urls if u not in seen and not seen.add(u)]

        # Step 3: Visit profiles
        visited = 0
        for url in unique_urls:
            if visited >= MAX_PROFILES_PER_RUN:
                break
            print(f"[linkedin] Visiting profile {visited + 1}/{MAX_PROFILES_PER_RUN}: {url}")
            profile = visit_profile(page, url)
            visited += 1
            if profile:
                matched_profiles.append(profile)
                print(f"[linkedin] Match found: {profile['name']} @ {profile['current_company']}")

        browser.close()

    print(f"[linkedin] Done. {len(matched_profiles)} matches from {visited} profiles visited.")
    return matched_profiles


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_delay(delay_range: tuple[int | float, int | float]) -> None:
    """Sleep for a random duration within the given (min, max) range."""
    time.sleep(random.uniform(delay_range[0], delay_range[1]))
