# tracker/scrapers/github_repos.py
#
# Parses internship HTML or markdown pipe tables from GitHub READMEs.
# Supports two formats:
#   HTML <table> — used by SimplifyJobs (switched from markdown in 2026-04)
#   Markdown pipe tables — used by negarprh/Canadian-Tech-Internships-2026
#
# Supported repos (configured in config.py):
#   SimplifyJobs/Summer2026-Internships
#   negarprh/Canadian-Tech-Internships-2026
#   SimplifyJobs/New-Grad-Positions  (disabled)
#
# Table column order expected: Company | Role | Location | Apply | ...
# The Apply cell must be column index 3 and contain at least one HTTP link.

import re
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


def _parse_markdown_table(content: str) -> list[list[dict]]:
    """Parse GitHub-flavored markdown pipe tables into the same row/cell format as _TableParser."""
    rows = []
    lines = content.splitlines()
    header_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        if "---" in stripped:
            continue
        if header_idx is None:
            header_idx = i
            continue
        if i == header_idx + 1:
            continue
        cells_raw = [c.strip() for c in stripped[1:-1].split("|")]
        cells = []
        for raw in cells_raw:
            links = re.findall(r'\[.*?\]\((https?://[^)]+)\)', raw)
            text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', raw).strip()
            cells.append({"text": text, "links": links})
        if cells:
            rows.append(cells)
    return rows


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

    if "<table" in content:
        parser = _TableParser()
        parser.feed(content)
        rows = parser.rows
    else:
        rows = _parse_markdown_table(content)

    jobs: list[Job] = []
    for row in rows:
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
