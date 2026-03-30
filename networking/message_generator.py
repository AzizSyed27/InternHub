# networking/message_generator.py
#
# Generates personalized LinkedIn outreach drafts using the Anthropic API.
# If ANTHROPIC_MODEL is empty in config.py, returns template-filled drafts
# without calling the API.
#
# Two drafts per profile:
#   1. Connection note (≤300 chars — LinkedIn hard limit)
#   2. Follow-up message (sent manually after the connection is accepted)

import json
import os
from pathlib import Path

from networking.config import (
    ANTHROPIC_MODEL,
    CONNECTION_NOTE_TEMPLATE,
    FOLLOWUP_TEMPLATE,
)
from networking.profile_parser import Profile

# Load company values at import time so we fail early if the file is missing
_VALUES_PATH = Path(__file__).parent / "company_values.json"
with _VALUES_PATH.open("r", encoding="utf-8") as _fh:
    _COMPANY_VALUES: dict[str, str] = json.load(_fh)

_CONNECTION_NOTE_MAX_CHARS = 300


def generate_drafts(profile: Profile) -> tuple[str, str]:
    """
    Return (connection_note, followup_message) for the given profile.

    If ANTHROPIC_MODEL is set, calls the Anthropic API to lightly personalize
    both drafts using the profile details and company values.
    Falls back to template substitution only if the API call fails or
    ANTHROPIC_MODEL is empty.
    """
    company_value = _COMPANY_VALUES.get(
        profile["current_company"],
        f"making an impact in tech",  # safe fallback
    )
    if not _COMPANY_VALUES.get(profile["current_company"]):
        print(
            f"[message_generator] WARNING: no company value for '{profile['current_company']}'"
            " — using generic fallback"
        )

    note = _fill_template(CONNECTION_NOTE_TEMPLATE, profile, company_value)
    followup = _fill_template(FOLLOWUP_TEMPLATE, profile, company_value)

    if ANTHROPIC_MODEL:
        try:
            note, followup = _personalize_with_ai(profile, note, followup, company_value)
        except Exception as exc:
            print(f"[message_generator] WARNING: Anthropic API call failed: {exc}. Using template.")

    # Enforce 300-char hard limit on connection note
    if len(note) > _CONNECTION_NOTE_MAX_CHARS:
        note = note[: _CONNECTION_NOTE_MAX_CHARS - 1] + "…"

    return note, followup


def _fill_template(template: str, profile: Profile, company_value: str) -> str:
    """Substitute all placeholders in the template string."""
    return (
        template
        .replace("[Name]", profile["name"].split()[0])  # first name only
        .replace("[Company]", profile["current_company"])
        .replace("[Role]", profile["current_role"])
        .replace("[College]", profile["college"])
        .replace("[University]", profile["university"])
        .replace("[COMPANY_VALUE]", company_value)
    )


def _personalize_with_ai(
    profile: Profile,
    note_draft: str,
    followup_draft: str,
    company_value: str,
) -> tuple[str, str]:
    """
    Send both drafts to the Anthropic API for light personalization.
    Returns (note, followup).
    """
    import anthropic  # imported here so networking tool doesn't hard-fail if not installed

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = f"""You are helping a CS student personalize LinkedIn outreach messages.

Profile:
- Name: {profile['name']}
- Current role: {profile['current_role']} at {profile['current_company']}
- Education path: {profile['college']} → {profile['university']}

Company value for {profile['current_company']}: {company_value}

Here are two draft messages. Lightly personalize them — keep the tone warm, genuine, and concise.
Make small improvements based on the profile details, but do not add information that isn't provided.
Do NOT change the overall structure or length significantly.

CONNECTION NOTE (must stay under 300 characters total, including spaces):
{note_draft}

FOLLOW-UP MESSAGE:
{followup_draft}

Return a JSON object with two keys: "note" and "followup". No explanation, just the JSON."""

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw)
    return parsed["note"], parsed["followup"]
