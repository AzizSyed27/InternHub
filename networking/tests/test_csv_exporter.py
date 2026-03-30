# networking/tests/test_csv_exporter.py

import csv
from datetime import date
from pathlib import Path

from networking.csv_exporter import export_csv, _COLUMNS
from networking.profile_parser import Profile


def _make_profile(**overrides) -> Profile:
    base: Profile = {
        "name": "Jane Smith",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "current_company": "Google",
        "current_role": "Software Engineer",
        "college": "Centennial College",
        "university": "University of Toronto",
        "connection_degree": "2nd",
        "connection_note_draft": "Hi Jane!",
        "followup_message_draft": "Hi Jane, I wanted to follow up...",
        "contacted": "",
        "replied": "",
        "notes": "",
    }
    base.update(overrides)
    return base


def test_export_creates_file(tmp_path):
    profiles = [_make_profile(), _make_profile(name="Bob Jones", linkedin_url="https://linkedin.com/in/bobjones")]
    output_path = export_csv(profiles, tmp_path)
    assert Path(output_path).exists()


def test_export_filename_contains_today(tmp_path):
    profiles = [_make_profile()]
    output_path = export_csv(profiles, tmp_path)
    assert date.today().isoformat() in Path(output_path).name


def test_export_correct_columns(tmp_path):
    profiles = [_make_profile()]
    output_path = export_csv(profiles, tmp_path)
    with open(output_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert list(reader.fieldnames) == _COLUMNS


def test_export_correct_row_count(tmp_path):
    profiles = [_make_profile(), _make_profile(name="Bob Jones")]
    output_path = export_csv(profiles, tmp_path)
    with open(output_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2


def test_export_blank_manual_columns(tmp_path):
    profiles = [_make_profile()]
    output_path = export_csv(profiles, tmp_path)
    with open(output_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["contacted"] == ""
    assert rows[0]["replied"] == ""
    assert rows[0]["notes"] == ""


def test_export_empty_profiles_creates_header_only_file(tmp_path):
    output_path = export_csv([], tmp_path)
    assert Path(output_path).exists()
    with open(output_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 0


def test_export_handles_special_chars_in_fields(tmp_path):
    # Fields with commas and quotes must be properly escaped in CSV
    profile = _make_profile(
        name='O\'Brien, "Jane"',
        notes="Applied on 2026-03-30, waiting",
    )
    output_path = export_csv([profile], tmp_path)
    with open(output_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["name"] == 'O\'Brien, "Jane"'
    assert rows[0]["notes"] == "Applied on 2026-03-30, waiting"
