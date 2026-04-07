# tracker/scrapers/hackernews.py
#
# Scrapes the monthly "Ask HN: Who is Hiring?" thread on Hacker News.
# Uses the Algolia HN Search API to find the current month's thread
# dynamically — no hardcoded story IDs.
#
# Algolia HN API docs: https://hn.algolia.com/api

import json
import re
import urllib.parse
import urllib.request

from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job

_SEARCH_URL = (
    "https://hn.algolia.com/api/v1/search"
    "?query=Ask+HN+Who+is+hiring&tags=story,ask_hn&hitsPerPage=5"
)
_ITEM_URL = "https://hn.algolia.com/api/v1/items/{story_id}"
_HN_COMMENT_URL = "https://news.ycombinator.com/item?id={id}"

# Regex to find a URL in a comment body (HTML)
_URL_RE = re.compile(r'href="(https?://[^"]+)"')
# Strip HTML tags for text extraction
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def scrape() -> list[Job]:
    try:
        story_id = _find_hiring_story_id()
    except Exception as exc:
        print(f"[hackernews] WARNING: failed to find Who is Hiring thread: {exc}")
        return []

    if not story_id:
        print("[hackernews] WARNING: could not find current Who is Hiring thread")
        return []

    try:
        return _parse_story(story_id)
    except Exception as exc:
        print(f"[hackernews] WARNING: failed to parse story {story_id}: {exc}")
        return []


def _find_hiring_story_id() -> str | None:
    """Return the HN item ID of the most recent Who is Hiring thread."""
    req = urllib.request.Request(_SEARCH_URL, headers={"User-Agent": "InternHub/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    for hit in data.get("hits", []):
        title = hit.get("title", "").lower()
        if "who is hiring" in title or "who's hiring" in title:
            return str(hit.get("objectID", ""))
    return None


def _parse_story(story_id: str) -> list[Job]:
    url = _ITEM_URL.format(story_id=story_id)
    req = urllib.request.Request(url, headers={"User-Agent": "InternHub/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    jobs: list[Job] = []
    for comment in data.get("children", []):
        job = _comment_to_job(comment)
        if job and passes_filters(job, "community"):
            jobs.append(job)
    return jobs


def _comment_to_job(comment: dict) -> Job | None:
    """Extract a Job from a single top-level HN comment."""
    body_html = comment.get("text", "") or ""
    if not body_html:
        return None

    text = _HTML_TAG_RE.sub(" ", body_html).strip()
    comment_id = str(comment.get("id", ""))
    comment_url = _HN_COMMENT_URL.format(id=comment_id)

    # Best-effort: first line is usually "Company | Role | Location | ..."
    first_line = text.split("\n")[0].strip()
    parts = [p.strip() for p in first_line.split("|")]

    company = parts[0] if len(parts) > 0 else "Unknown"
    title = parts[1] if len(parts) > 1 else first_line[:80]
    location = parts[2] if len(parts) > 2 else ""

    # Try to find an explicit apply URL in the comment
    apply_url_match = _URL_RE.search(body_html)
    apply_url = apply_url_match.group(1) if apply_url_match else comment_url

    return Job(
        id=make_job_id("hn", company, title, apply_url),
        title=title,
        company=company,
        location=location,
        url=apply_url,
        date_posted="",
        description=text[:500],
        source="HackerNews",
    )
