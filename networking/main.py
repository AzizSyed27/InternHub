#!/usr/bin/env python3
# networking/main.py
#
# LinkedIn Networking Pipeline — entry point.
# Run manually from the terminal (never scheduled):
#
#   cd networking
#   python main.py
#
# What it does:
#   1. Logs into LinkedIn using LINKEDIN_EMAIL / LINKEDIN_PASSWORD from .env
#   2. Iterates alumni pages for configured schools × target companies
#   3. Visits matching profiles (up to MAX_PROFILES_PER_RUN)
#   4. Generates connection note + follow-up draft per matched profile
#   5. Exports a timestamped CSV ready for manual outreach

import os
import sys
from pathlib import Path

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from networking.config import (
    ANTHROPIC_MODEL,
    COLLEGES,
    TARGET_COMPANIES,
    UNIVERSITIES,
)
from networking.csv_exporter import export_csv
from networking.linkedin_scraper import run_scraper
from networking.message_generator import generate_drafts


def _validate_env() -> None:
    """Exit early with a clear message if required environment variables are missing."""
    required = ["LINKEDIN_EMAIL", "LINKEDIN_PASSWORD"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[main] ERROR: Missing required environment variables: {', '.join(missing)}")
        print("       Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY") and ANTHROPIC_MODEL:
        print("[main] ERROR: ANTHROPIC_MODEL is set but ANTHROPIC_API_KEY is missing in .env")
        sys.exit(1)

    if not ANTHROPIC_MODEL:
        print(
            "[main] NOTE: ANTHROPIC_MODEL is empty in networking/config.py. "
            "Messages will use templates only (no AI personalization). "
            "Set ANTHROPIC_MODEL to enable AI drafts."
        )


def main() -> None:
    _validate_env()

    email = os.environ["LINKEDIN_EMAIL"]
    password = os.environ["LINKEDIN_PASSWORD"]

    print(f"[main] Starting LinkedIn scrape.")
    print(f"       Schools:   {len(COLLEGES)} colleges + {len(UNIVERSITIES)} universities")
    print(f"       Companies: {len(TARGET_COMPANIES)}")
    print(f"       Max profiles per run: from config")

    # Combine colleges and universities into one school list
    all_schools = COLLEGES + UNIVERSITIES

    # Run the scraper — this opens a browser, logs in, and visits profiles
    profiles = run_scraper(email, password, all_schools, TARGET_COMPANIES)

    if not profiles:
        print("[main] No matching profiles found this run.")
        sys.exit(0)

    # Generate outreach drafts for each matched profile
    print(f"[main] Generating outreach drafts for {len(profiles)} profiles...")
    for profile in profiles:
        try:
            note, followup = generate_drafts(profile)
            profile["connection_note_draft"] = note
            profile["followup_message_draft"] = followup
        except Exception as exc:
            print(f"[main] WARNING: could not generate drafts for {profile['name']}: {exc}")

    # Export to CSV
    output_path = export_csv(profiles)
    print(f"\n[main] Done. {len(profiles)} profiles exported to:")
    print(f"       {output_path}")
    print()
    print("Next steps:")
    print("  1. Open the CSV in Excel or Google Sheets")
    print("  2. Review and edit the connection note drafts (300 char limit)")
    print("  3. Send connection requests manually on LinkedIn")
    print("  4. After acceptance, send the follow-up message manually")
    print("  5. Update 'contacted' and 'replied' columns as you go")


if __name__ == "__main__":
    main()
