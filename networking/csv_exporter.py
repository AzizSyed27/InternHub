# networking/csv_exporter.py
#
# Exports a list of matched LinkedIn profiles to a timestamped CSV file.
# The last three columns (contacted, replied, notes) are left blank for
# the user to fill in manually as they work through outreach.

import csv
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from networking.profile_parser import Profile

_COLUMNS = [
    "name",
    "linkedin_url",
    "current_company",
    "current_role",
    "college",
    "university",
    "connection_degree",
    "connection_note_draft",
    "followup_message_draft",
    "contacted",
    "replied",
    "notes",
]


def export_csv(profiles: "list[Profile]", output_dir: Path | None = None) -> str:
    """
    Write profiles to a CSV file named networking_results_YYYY-MM-DD.csv.
    output_dir defaults to the current working directory.
    Returns the absolute path to the written file.
    """
    if output_dir is None:
        output_dir = Path.cwd()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"networking_results_{date.today().isoformat()}.csv"
    output_path = output_dir / filename

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for profile in profiles:
            writer.writerow(profile)

    return str(output_path.resolve())
