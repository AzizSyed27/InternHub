# tracker/scrapers/github_repos.py
#
# Parses SimplifyJobs internship/new-grad markdown tables from GitHub.
# These repos maintain a README.md with a pipe-delimited table of job postings.
# The scraper fetches the raw README and extracts rows that contain apply links.
#
# Supported repos (configured in config.py):
#   SimplifyJobs/Summer2026-Internships
#   SimplifyJobs/New-Grad-Positions

import re
import urllib.request
from datetime import datetime, timezone

from tracker.config import GITHUB_REPOS
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

# SimplifyJobs repos use 'dev' as their default branch; fall back to 'main'
_RAW_BRANCHES = ["dev", "main"]
_RAW_URL = "https://raw.githubusercontent.com/{repo}/{branch}/README.md"

# Matches a markdown link: [text](url)
_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^\)]+)\)")


def scrape() -> list[Job]:
    jobs: list[Job] = []
    for repo in GITHUB_REPOS:
        try:
            jobs.extend(_scrape_repo(repo))
        except Exception as exc:
            print(f"[github_repos] WARNING: failed to scrape {repo}: {exc}")
    return jobs


def _scrape_repo(repo: str) -> list[Job]:
    content = None
    for branch in _RAW_BRANCHES:
        try:
            url = _RAW_URL.format(repo=repo, branch=branch)
            req = urllib.request.Request(url, headers={"User-Agent": "InternHub/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            break  # found a valid branch
        except Exception:
            continue
    if content is None:
        raise RuntimeError(f"could not fetch README from any branch: {_RAW_BRANCHES}")

    jobs: list[Job] = []
    for line in content.splitlines():
        if "|" not in line:
            continue
        # Skip header / separator rows
        if re.match(r"^\s*\|[\s\-:]+\|", line):
            continue

        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue

        # Find the first cell containing a markdown link — that's the apply URL
        apply_url = ""
        company = ""
        title = ""

        for i, cell in enumerate(cells):
            match = _LINK_RE.search(cell)
            if match and not apply_url:
                apply_url = match.group(2)
                # Cell 0 is usually company, cell 1 is role
                company = _LINK_RE.sub(match.group(1), cells[0]).strip() or cells[0].strip()
                title = cells[1].strip() if len(cells) > 1 else ""
                break

        if not apply_url:
            continue

        # Best-effort location: look for a cell that looks like a location
        location = _find_location_cell(cells)
        date_posted = _find_date_cell(cells)

        job: Job = {
            "id": make_job_id("github", company, title, apply_url),
            "title": title or "Software Internship",
            "company": company,
            "location": location,
            "url": apply_url,
            "date_posted": date_posted,
            "description": "",
            "source": "GitHub",
        }

        if passes_filters(job, "community"):
            jobs.append(job)

    return jobs


def _find_location_cell(cells: list[str]) -> str:
    """Return the first cell that looks like a geographic location."""
    location_hints = ["remote", "canada", "toronto", "usa", "united states", "new york",
                      "san francisco", "seattle", "on-site", "hybrid", ","]
    for cell in cells:
        clean = _LINK_RE.sub("", cell).strip()
        if any(hint in clean.lower() for hint in location_hints):
            return clean
    # Fallback: third cell if it exists and isn't clearly a date or URL
    if len(cells) > 2:
        candidate = _LINK_RE.sub("", cells[2]).strip()
        if candidate and "http" not in candidate:
            return candidate
    return ""


def _find_date_cell(cells: list[str]) -> str:
    """Return an ISO date string if any cell looks like a date, else empty."""
    month_names = ["jan", "feb", "mar", "apr", "may", "jun",
                   "jul", "aug", "sep", "oct", "nov", "dec"]
    for cell in cells:
        clean = _LINK_RE.sub("", cell).strip().lower()
        if any(m in clean for m in month_names) and len(clean) < 20:
            return clean  # Return as-is; full ISO parse would be fragile
    return ""
