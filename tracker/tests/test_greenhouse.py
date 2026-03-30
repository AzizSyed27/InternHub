# tracker/tests/test_greenhouse.py

import json
from unittest.mock import MagicMock, patch

from tracker.scrapers.greenhouse import _scrape_company

FIXTURE_RESPONSE = {
    "jobs": [
        {
            "title": "Software Engineer Intern",
            "absolute_url": "https://boards.greenhouse.io/shopify/jobs/123",
            "location": {"name": "Toronto, Canada"},
            "content": "Join our team as a software intern.",
            "updated_at": "2026-03-15T12:00:00.000Z",
        },
        {
            "title": "Senior Software Engineer",
            "absolute_url": "https://boards.greenhouse.io/shopify/jobs/456",
            "location": {"name": "Toronto, Canada"},
            "content": "We need a senior engineer.",
            "updated_at": "2026-03-10T09:00:00.000Z",
        },
        {
            "title": "Software Intern",
            "absolute_url": "https://boards.greenhouse.io/shopify/jobs/789",
            "location": {"name": "New York, USA"},
            "content": "NYC office internship.",
            "updated_at": "2026-03-20T00:00:00.000Z",
        },
    ]
}


def _mock_urlopen(data: dict):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_returns_matching_jobs():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Shopify", "shopify")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Software Engineer Intern"


def test_excludes_senior():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Shopify", "shopify")
    assert all("senior" not in j["title"].lower() for j in jobs)


def test_excludes_wrong_location():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Shopify", "shopify")
    assert all("new york" not in j["location"].lower() for j in jobs)


def test_date_parsed():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Shopify", "shopify")
    assert jobs[0]["date_posted"] == "2026-03-15"


def test_source_is_greenhouse():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Shopify", "shopify")
    assert all(j["source"] == "Greenhouse" for j in jobs)
