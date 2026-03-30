# tracker/tests/test_lever.py

import json
from unittest.mock import MagicMock, patch

from tracker.scrapers.lever import _scrape_company

FIXTURE_RESPONSE = [
    {
        "text": "Software Engineer Intern",
        "hostedUrl": "https://jobs.lever.co/stripe/abc123",
        "categories": {"location": "Toronto, Canada"},
        "descriptionPlain": "Join Stripe as a software intern.",
        "createdAt": 1742000000000,  # ~2025-03-14
    },
    {
        "text": "Senior Backend Engineer",
        "hostedUrl": "https://jobs.lever.co/stripe/def456",
        "categories": {"location": "Toronto, Canada"},
        "descriptionPlain": "Senior role.",
        "createdAt": 1742000000000,
    },
    {
        "text": "SWE Intern",
        "hostedUrl": "https://jobs.lever.co/stripe/ghi789",
        "categories": {"location": "Austin, Texas"},
        "descriptionPlain": "Texas office internship.",
        "createdAt": 1742000000000,
    },
]


def _mock_urlopen(data):
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_returns_intern_jobs():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Stripe", "stripe")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Software Engineer Intern"


def test_excludes_senior():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Stripe", "stripe")
    assert all("senior" not in j["title"].lower() for j in jobs)


def test_excludes_wrong_location():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Stripe", "stripe")
    assert all("austin" not in j["location"].lower() for j in jobs)


def test_source_is_lever():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Stripe", "stripe")
    assert all(j["source"] == "Lever" for j in jobs)


def test_date_parsed():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(FIXTURE_RESPONSE)):
        jobs = _scrape_company("Stripe", "stripe")
    assert jobs[0]["date_posted"]  # non-empty
