# tracker/scrapers/github_repos.py
#
# Parses SimplifyJobs internship/new-grad HTML tables from GitHub.
# These repos maintain a README.md with an HTML table of job postings.
# The scraper fetches the raw README and extracts rows from the <tbody>.
#
# Supported repos (configured in config.py):
#   SimplifyJobs/Summer2026-Internships
#   SimplifyJobs/New-Grad-Positions
#
# Table column order: Company | Role | Location | Application | Age
# The Application cell contains two links: [0] direct apply URL, [1] Simplify profile (skipped).

import urllib.request
from html.parser import HTMLParser

from tracker.config import GITHUB_REPOS
from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

# SimplifyJobs repos use 'dev' as their default branch; fall back to 'main'
_RAW_BRANCHES = ["dev", "main"]
_RAW_URL = "https://raw.githubusercontent.com/{repo}/{branch}/README.md"


class _TableParser(HTMLParser):
    """Extracts <tr> rows from the HTML table in the SimplifyJobs README."""

    def __init__(self):
        super().__init__()
        self._in_tbody = False
        self._in_tr = False
        self._in_td = False
        self._cell: dict = {"text": "", "links": []}
        self._row: list = []
        self.rows: list[list[dict]] = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._in_tr = True
            self._row = []
        elif tag == "td" and self._in_tr:
            self._in_td = True
            self._cell = {"text": "", "links": []}
        elif tag == "a" and self._in_td:
            href = attrs_d.get("href", "")
            if href and href.startswith("http"):
                self._cell["links"].append(href)

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "tr" and self._in_tbody:
            if self._row:
                self.rows.append(self._row)
            self._in_tr = False
        elif tag == "td" and self._in_tr:
            self._row.append(self._cell)
            self._in_td = False

    def handle_data(self, data):
        if self._in_td:
            stripped = data.strip()
            if stripped:
                # Join multiple location strings (from <br>-separated locations) with ", "
                if self._cell["text"]:
                    self._cell["text"] += ", " + stripped
                else:
                    self._cell["text"] = stripped


def scrape() -> list[Job]:
    jobs: list[Job] = []
    for repo in GITHUB_REPOS:
        try:
            jobs.extend(_scrape_repo(repo))
        except Exception as exc:
            print(f"[github_repos] WARNING: failed to scrape {repo}: {exc}")
    return jobs


def _fetch_readme(repo: str) -> str:
    """Fetch raw README.md, trying dev branch first then main."""
    for branch in _RAW_BRANCHES:
        try:
            url = _RAW_URL.format(repo=repo, branch=branch)
            req = urllib.request.Request(url, headers={"User-Agent": "InternHub/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            continue
    raise RuntimeError(f"could not fetch README from any branch: {_RAW_BRANCHES}")


def _scrape_repo(repo: str) -> list[Job]:
    content = _fetch_readme(repo)

    parser = _TableParser()
    parser.feed(content)

    jobs: list[Job] = []
    for row in parser.rows:
        if len(row) < 4:
            continue

        company  = row[0]["text"].strip()
        title    = row[1]["text"].strip()
        location = row[2]["text"].strip()

        # First link in the Application cell is the direct apply URL.
        # The second link is the Simplify profile page — skip it.
        apply_links = row[3]["links"]
        if not apply_links:
            continue
        apply_url = apply_links[0]

        if not company or not title or not apply_url:
            continue

        job: Job = {
            "id": make_job_id("github", company, title, apply_url),
            "title": title,
            "company": company,
            "location": location,
            "url": apply_url,
            "date_posted": "",
            "description": "",
            "source": "GitHub",
        }

        if passes_filters(job, "github"):
            jobs.append(job)

    return jobs
