# networking/profile_parser.py
#
# Extracts structured data from a LinkedIn profile page via Playwright's page object.
# Returns a Profile TypedDict if the person matches all three criteria, else None.
#
# Match criteria (ALL three required):
#   1. College diploma from any Ontario college in config.COLLEGES
#   2. University degree from any Canadian university in config.UNIVERSITIES
#   3. Current role at one of the 35 target companies in config.TARGET_COMPANIES

import re
from typing import TypedDict

from networking.config import COLLEGES, TARGET_COMPANIES, UNIVERSITIES


class Profile(TypedDict):
    name: str
    linkedin_url: str
    current_company: str
    current_role: str
    college: str
    university: str
    connection_degree: str
    connection_note_draft: str   # populated by message_generator
    followup_message_draft: str  # populated by message_generator
    contacted: str               # blank — filled in manually
    replied: str                 # blank — filled in manually
    notes: str                   # blank — filled in manually


def parse_profile(page, url: str) -> "Profile | None":
    """
    Parse a LinkedIn profile page and return a Profile if the person matches
    all three criteria.  Returns None if any criterion is unmet or the page
    fails to load.

    `page` is a Playwright Page object already navigated to `url`.
    """
    try:
        name = _extract_name(page)
        if not name:
            return None

        current_role, current_company = _extract_current_position(page)
        college, university = _extract_education(page)
        connection_degree = _extract_connection_degree(page)

        # All three criteria must be met
        if not college or not university or not current_company:
            return None
        if not _matches_target_company(current_company):
            return None

        return Profile(
            name=name,
            linkedin_url=url,
            current_company=current_company,
            current_role=current_role,
            college=college,
            university=university,
            connection_degree=connection_degree,
            connection_note_draft="",
            followup_message_draft="",
            contacted="",
            replied="",
            notes="",
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_name(page) -> str:
    """Extract the profile's full name from the h1 heading."""
    try:
        h1 = page.locator("h1").first
        return h1.inner_text().strip()
    except Exception:
        return ""


def _extract_current_position(page) -> tuple[str, str]:
    """
    Return (current_role, current_company) from the most recent experience entry.
    LinkedIn renders experience as a list; the first item is current.
    """
    try:
        # The experience section has list items with role and company text
        exp_section = page.locator(
            "#experience ~ div li, "
            "section[data-section='experience'] li, "
            ".pvs-list__item--line-separated"
        ).first
        text = exp_section.inner_text().strip()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        role = lines[0] if lines else ""
        company = lines[1] if len(lines) > 1 else ""
        # Strip " · Full-time" etc. from company
        company = re.sub(r"\s*·.*$", "", company).strip()
        return role, company
    except Exception:
        return "", ""


def _extract_education(page) -> tuple[str, str]:
    """
    Return (college_name, university_name) matched against config lists.
    Both must be found in the education section; order doesn't matter.
    """
    try:
        edu_section = page.locator(
            "#education ~ div, "
            "section[data-section='education']"
        ).first
        edu_text = edu_section.inner_text().lower()
    except Exception:
        return "", ""

    found_college = ""
    found_university = ""

    for school in COLLEGES:
        if school.lower() in edu_text:
            found_college = school
            break

    for school in UNIVERSITIES:
        if school.lower() in edu_text:
            found_university = school
            break

    return found_college, found_university


def _extract_connection_degree(page) -> str:
    """Return '1st', '2nd', '3rd', or '' from the connection badge."""
    try:
        badge = page.locator(".dist-value, [aria-label*='degree connection']").first
        text = badge.inner_text().strip()
        match = re.search(r"(\d+)(st|nd|rd)", text)
        return match.group(0) if match else text
    except Exception:
        return ""


def _matches_target_company(company: str) -> bool:
    """Return True if the company matches any target company (case-insensitive partial)."""
    company_lower = company.lower()
    return any(t.lower() in company_lower or company_lower in t.lower() for t in TARGET_COMPANIES)
