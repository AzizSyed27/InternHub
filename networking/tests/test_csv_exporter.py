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
