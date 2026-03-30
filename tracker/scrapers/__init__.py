# tracker/scrapers/__init__.py
#
# Shared data contract for all scrapers.
# Every scraper returns a list[Job]. No scraper imports from another scraper.

from typing import TypedDict


class Job(TypedDict):
    id: str           # md5(source_prefix + company + title + url) — set by make_job_id() in filters.py
    title: str
    company: str
    location: str
    url: str
    date_posted: str  # YYYY-MM-DD, or empty string if unknown
    description: str  # first 500 chars of the job description
    source: str       # "GitHub" | "Greenhouse" | "Lever" | "BigTech" | "Workday"
                      # | "HackerNews" | "YC" | "Meta" | "Tesla"
                      # | "GovtCanada" | "OPS" | "OPG" | "CityToronto"
