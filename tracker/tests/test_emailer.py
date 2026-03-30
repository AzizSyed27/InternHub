# tracker/tests/test_emailer.py
#
# Tests for the HTML email builder. Does not make real SMTP connections.

from tracker.emailer import _build_html
from tracker.scrapers import Job


def _job(**overrides) -> Job:
    base: Job = {
        "id": "abc123",
        "title": "Software Engineering Intern",
        "company": "Acme Corp",
        "location": "Toronto, ON",
        "url": "https://example.com/job/1",
        "date_posted": "2026-03-30",
        "description": "Join our team as a software intern working on backend systems.",
        "source": "Greenhouse",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# HTML escaping
# ---------------------------------------------------------------------------

def test_ampersand_escaped():
    html = _build_html(_job(company="A & B Corp"))
    assert "A &amp; B Corp" in html
    assert "A & B Corp" not in html


def test_less_than_escaped():
    html = _build_html(_job(title="Software <Intern>"))
    assert "&lt;Intern&gt;" in html
    assert "<Intern>" not in html


def test_double_quote_escaped():
    html = _build_html(_job(title='Software "Intern"'))
    assert "&quot;Intern&quot;" in html


def test_single_quote_escaped():
    html = _build_html(_job(title="O'Brien's Internship"))
    assert "&#39;" in html
    assert "O'Brien" not in html


def test_url_in_apply_button():
    html = _build_html(_job(url="https://example.com/job/1"))
    assert 'href="https://example.com/job/1"' in html


# ---------------------------------------------------------------------------
# Description truncation
# ---------------------------------------------------------------------------

def test_description_truncated_at_300_chars():
    long_desc = "x" * 400
    html = _build_html(_job(description=long_desc))
    assert "x" * 301 not in html   # truncated
    assert "…" in html


def test_short_description_not_truncated():
    html = _build_html(_job(description="Short desc"))
    assert "Short desc" in html
    assert "…" not in html


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_html_contains_apply_button():
    html = _build_html(_job())
    assert "Apply Now" in html


def test_html_contains_company_name():
    html = _build_html(_job(company="Shopify"))
    assert "Shopify" in html


def test_html_contains_source_badge():
    html = _build_html(_job(source="Greenhouse"))
    assert "Greenhouse" in html


def test_unknown_source_gets_default_badge_color():
    # Should not raise — unknown source gets a fallback color
    html = _build_html(_job(source="UnknownATS"))
    assert "UnknownATS" in html
