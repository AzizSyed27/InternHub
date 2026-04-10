# tracker/scrapers/ontario_public.py
#
# Scrapes Ontario Public Service (OPS) job listings via Playwright.
#
# STATUS (2026-04): DISABLED — broken.
#   Old URL: https://www.ontario.ca/page/current-ontario-public-service-job-opportunities
#   → Returns 404 (page removed).
#   New landing page: https://ontario.ca/page/careers-ontario-public-service
#   → Links to https://www.gojobs.gov.on.ca/Jobs.aspx for job listings.
#   → gojobs.gov.on.ca is protected by Radware CAPTCHA and blocks headless Chromium.
#
# To re-enable: find a way past the Radware bot protection on gojobs.gov.on.ca,
# or use the ontario.ca API if one becomes available.
# PUBLIC_SECTOR_ENABLED["ontario_public"] is set to False in config.py.

from tracker.config import PUBLIC_SECTOR_ENABLED
from tracker.scrapers import Job

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def scrape() -> list[Job]:
    if not PUBLIC_SECTOR_ENABLED.get("ontario_public"):
        return []
    print(
        "[ontario_public] WARNING: OPS job portal (gojobs.gov.on.ca) is protected by "
        "Radware CAPTCHA and cannot be scraped with headless Chromium. Skipping."
    )
    return []
