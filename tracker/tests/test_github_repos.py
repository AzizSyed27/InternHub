# tracker/tests/test_github_repos.py

from unittest.mock import MagicMock, patch

from tracker.scrapers.github_repos import _scrape_repo

# Minimal markdown table fixture matching SimplifyJobs format
FIXTURE_README = """
# Summer 2026 Internships

| Company | Role | Location | Application/Link | Date Posted |
| ------- | ---- | -------- | ---------------- | ----------- |
| Shopify | Software Engineer Intern | Toronto, Canada | [Apply](https://shopify.com/careers/intern) | Jan 2026 |
| Some Senior Corp | Senior Engineer | Toronto, Canada | [Apply](https://example.com/senior) | Jan 2026 |
| Google | SWE Intern | Remote | [Apply](https://careers.google.com/intern) | Feb 2026 |
"""


def _mock_urlopen(content: str):
    mock_resp = MagicMock()
    mock_resp.read.return_value = content.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_scrape_repo_returns_jobs():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_README)):
        jobs = _scrape_repo("SimplifyJobs/Summer2026-Internships")
    assert len(jobs) >= 1
    titles = [j["title"] for j in jobs]
    assert any("intern" in t.lower() or "swe" in t.lower() for t in titles)


def test_scrape_repo_excludes_senior():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_README)):
        jobs = _scrape_repo("SimplifyJobs/Summer2026-Internships")
    companies = [j["company"] for j in jobs]
    assert "Some Senior Corp" not in companies


def test_scrape_repo_job_has_required_fields():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_README)):
        jobs = _scrape_repo("SimplifyJobs/Summer2026-Internships")
    for job in jobs:
        assert job["url"].startswith("http")
        assert job["source"] == "GitHub"
        assert job["id"]  # non-empty MD5
