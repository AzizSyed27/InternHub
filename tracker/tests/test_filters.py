# tracker/tests/test_filters.py

import pytest

from tracker.filters import make_job_id, passes_filters
from tracker.scrapers import Job


def _job(**overrides) -> Job:
    base: Job = {
        "id": "dummy",
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
# make_job_id
# ---------------------------------------------------------------------------

def test_make_job_id_deterministic():
    id1 = make_job_id("gh", "Shopify", "Software Intern", "https://example.com")
    id2 = make_job_id("gh", "Shopify", "Software Intern", "https://example.com")
    assert id1 == id2


def test_make_job_id_different_inputs_differ():
    id1 = make_job_id("gh", "Shopify", "Software Intern", "https://example.com")
    id2 = make_job_id("gh", "Shopify", "Data Intern", "https://example.com")
    assert id1 != id2


def test_make_job_id_case_insensitive():
    id1 = make_job_id("GH", "Shopify", "Software Intern", "https://example.com")
    id2 = make_job_id("gh", "shopify", "software intern", "https://example.com")
    assert id1 == id2


# ---------------------------------------------------------------------------
# passes_filters — keyword include
# ---------------------------------------------------------------------------

def test_intern_title_passes():
    assert passes_filters(_job(title="Software Engineering Intern"), "tier1") is True


def test_coop_title_passes():
    assert passes_filters(_job(title="Backend Co-op Developer"), "tier1") is True


def test_no_keyword_fails():
    assert passes_filters(_job(title="Accountant", description="Finance role"), "tier1") is False


# ---------------------------------------------------------------------------
# passes_filters — keyword exclude
# ---------------------------------------------------------------------------

def test_senior_title_excluded():
    assert passes_filters(_job(title="Senior Software Engineer"), "tier1") is False


def test_staff_excluded():
    assert passes_filters(_job(title="Staff Software Engineer Intern"), "tier1") is False


def test_product_manager_excluded():
    assert passes_filters(_job(title="Product Manager Intern"), "tier1") is False


# ---------------------------------------------------------------------------
# passes_filters — location (tier1)
# ---------------------------------------------------------------------------

def test_toronto_location_passes():
    assert passes_filters(_job(location="Toronto, Ontario"), "tier1") is True


def test_remote_passes():
    assert passes_filters(_job(location="Remote"), "tier1") is True


def test_new_york_excluded():
    assert passes_filters(_job(location="New York, NY"), "tier1") is False


def test_waterloo_passes():
    assert passes_filters(_job(location="Waterloo, ON, Canada"), "tier1") is True


# ---------------------------------------------------------------------------
# passes_filters — big_tech tier skips location check
# ---------------------------------------------------------------------------

def test_big_tech_tier_skips_location():
    # New York would normally fail, but big_tech skips location filtering
    assert passes_filters(_job(location="New York, NY"), "big_tech") is True


def test_big_tech_tier_still_applies_keyword_filter():
    assert passes_filters(_job(title="Senior Engineer", location="New York, NY"), "big_tech") is False


# ---------------------------------------------------------------------------
# passes_filters — applied company
# ---------------------------------------------------------------------------

def test_applied_company_skipped(monkeypatch):
    import tracker.filters as f
    monkeypatch.setattr(f, "APPLIED_COMPANIES", ["Acme Corp"])
    assert passes_filters(_job(company="Acme Corp"), "tier1") is False


def test_non_applied_company_passes(monkeypatch):
    import tracker.filters as f
    monkeypatch.setattr(f, "APPLIED_COMPANIES", ["Other Corp"])
    assert passes_filters(_job(company="Acme Corp"), "tier1") is True
