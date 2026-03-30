# tracker/tests/test_db.py

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import tracker.db as db_module


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH to a temp file for every test."""
    fake_path = tmp_path / "seen_jobs.json"
    monkeypatch.setattr(db_module, "DB_PATH", fake_path)
    yield fake_path


# ---------------------------------------------------------------------------
# load_db / save_db
# ---------------------------------------------------------------------------

def test_load_db_creates_file_if_missing(tmp_db):
    assert not tmp_db.exists()
    result = db_module.load_db()
    assert tmp_db.exists()
    assert result == {"seen_ids": [], "last_run": {}}


def test_save_and_load_roundtrip(tmp_db):
    data = {"seen_ids": ["abc"], "last_run": {"greenhouse": "2026-01-01T00:00:00+00:00"}}
    db_module.save_db(data)
    assert db_module.load_db() == data


# ---------------------------------------------------------------------------
# is_new / mark_seen
# ---------------------------------------------------------------------------

def test_is_new_returns_true_for_unseen_id(tmp_db):
    assert db_module.is_new("abc123") is True


def test_is_new_returns_false_after_mark_seen(tmp_db):
    db_module.mark_seen("abc123")
    assert db_module.is_new("abc123") is False


def test_mark_seen_idempotent(tmp_db):
    db_module.mark_seen("abc123")
    db_module.mark_seen("abc123")
    db = db_module.load_db()
    assert db["seen_ids"].count("abc123") == 1


# ---------------------------------------------------------------------------
# get_last_run / set_last_run
# ---------------------------------------------------------------------------

def test_get_last_run_returns_none_for_unknown_scraper(tmp_db):
    assert db_module.get_last_run("greenhouse") is None


def test_set_and_get_last_run(tmp_db):
    db_module.set_last_run("greenhouse")
    ts = db_module.get_last_run("greenhouse")
    assert ts is not None
    assert isinstance(ts, datetime)
    # Should be very recent
    delta = datetime.now(timezone.utc) - ts
    assert delta.total_seconds() < 5


# ---------------------------------------------------------------------------
# is_seeded
# ---------------------------------------------------------------------------

def test_is_seeded_false_when_empty(tmp_db):
    assert db_module.is_seeded() is False


def test_is_seeded_true_after_mark_seen(tmp_db):
    db_module.mark_seen("some-id")
    assert db_module.is_seeded() is True
