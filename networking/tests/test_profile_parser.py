# networking/tests/test_profile_parser.py
#
# Tests for profile_parser helpers using mock Playwright page objects.

from unittest.mock import MagicMock, patch

import pytest

from networking.profile_parser import (
    _extract_connection_degree,
    _extract_current_position,
    _extract_education,
    _extract_name,
    _matches_target_company,
    parse_profile,
)


def _make_page(
    name="Jane Smith",
    role="Software Engineer",
    company="Google",
    edu_text="centennial college\nuniversity of toronto",
    badge="2nd",
):
    """Build a minimal mock Playwright page."""
    page = MagicMock()

    # h1 → name
    page.locator.return_value.first.inner_text.return_value = name

    # We need locator to return different things for different selectors.
    # The simplest approach: use side_effect to differentiate.
    def locator_side_effect(selector):
        mock = MagicMock()
        if "h1" in selector:
            mock.first.inner_text.return_value = name
        elif "experience" in selector or "pvs-list" in selector:
            mock.first.inner_text.return_value = f"{role}\n{company}\nFull-time"
        elif "education" in selector:
            mock.first.inner_text.return_value = edu_text
        elif "dist-value" in selector or "degree" in selector:
            mock.first.inner_text.return_value = badge
        else:
            mock.first.inner_text.return_value = ""
        return mock

    page.locator.side_effect = locator_side_effect
    return page


# ---------------------------------------------------------------------------
# _matches_target_company
# ---------------------------------------------------------------------------

def test_matches_google():
    assert _matches_target_company("Google") is True


def test_matches_partial_company_name():
    assert _matches_target_company("Google LLC") is True


def test_no_match_unknown_company():
    assert _matches_target_company("Random Startup Inc") is False


# ---------------------------------------------------------------------------
# parse_profile — integration
# ---------------------------------------------------------------------------

def test_parse_profile_returns_profile_on_match():
    page = _make_page()
    profile = parse_profile(page, "https://linkedin.com/in/janesmith")
    assert profile is not None
    assert profile["name"] == "Jane Smith"
    assert profile["current_company"] == "Google"
    assert profile["college"] == "Centennial College"
    assert profile["university"] == "University of Toronto"


def test_parse_profile_returns_none_if_no_college():
    page = _make_page(edu_text="university of toronto")
    assert parse_profile(page, "https://linkedin.com/in/test") is None


def test_parse_profile_returns_none_if_no_university():
    page = _make_page(edu_text="centennial college")
    assert parse_profile(page, "https://linkedin.com/in/test") is None


def test_parse_profile_returns_none_if_not_target_company():
    page = _make_page(company="Random Startup")
    assert parse_profile(page, "https://linkedin.com/in/test") is None


def test_parse_profile_blank_outreach_fields():
    page = _make_page()
    profile = parse_profile(page, "https://linkedin.com/in/janesmith")
    assert profile["connection_note_draft"] == ""
    assert profile["followup_message_draft"] == ""
    assert profile["contacted"] == ""
    assert profile["replied"] == ""
    assert profile["notes"] == ""
