# tracker/filters.py
#
# Filtering logic applied to every job before it triggers an email.
# All scrapers call passes_filters() before returning results.

import hashlib

from tracker.config import (
    APPLIED_COMPANIES,
    KEYWORDS_EXCLUDE,
    KEYWORDS_INCLUDE,
    LOCATIONS_INCLUDE,
)
from tracker.scrapers import Job


def make_job_id(source_prefix: str, company: str, title: str, url: str) -> str:
    """
    Stable deduplication ID: md5 of the four identifying fields concatenated.
    Same posting from the same source always produces the same ID.
    """
    raw = f"{source_prefix}{company}{title}{url}".lower()
    return hashlib.md5(raw.encode()).hexdigest()


def passes_filters(job: Job, tier: str) -> bool:
    """
    Return True if the job should be emailed.

    tier="big_tech"  → keyword check + applied-company check only (no location).
                        Tier 2 and Tier 3 scrapers pass location via API query
                        parameters instead, so client-side location filtering
                        would double-filter and drop valid results.
    all other tiers  → keyword check + location check + applied-company check.
    """
    title_lower = job["title"].lower()
    title_desc = (job["title"] + " " + job["description"]).lower()

    # --- Applied-company check (all tiers) ---
    if job["company"] in APPLIED_COMPANIES:
        return False

    # --- Keyword include check — title OR description (all tiers) ---
    if not any(kw.lower() in title_desc for kw in KEYWORDS_INCLUDE):
        return False

    # --- Keyword exclude check — title ONLY (all tiers) ---
    # Applied to title only so that descriptions mentioning "leadership",
    # "leading edge", "senior engineer mentorship", etc. don't false-positive.
    # Seniority is indicated by the job title, not what appears in the description.
    if any(kw.lower() in title_lower for kw in KEYWORDS_EXCLUDE):
        return False

    # --- Location check (skipped for big_tech tier) ---
    if tier != "big_tech":
        location = job["location"].lower()
        if not any(loc.lower() in location for loc in LOCATIONS_INCLUDE):
            return False

    return True
