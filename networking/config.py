# networking/config.py
#
# All user-facing configuration for the LinkedIn Networking Pipeline.
# To adapt for your own search: update COLLEGES, UNIVERSITIES, TARGET_COMPANIES,
# and the message templates below.

# ---------------------------------------------------------------------------
# Target schools — the scraper searches alumni pages for each school
# ---------------------------------------------------------------------------

# Ontario colleges (diploma programs)
COLLEGES = [
    "Centennial College",
    "Sheridan College",
    "Humber College",
    "George Brown College",
    "Seneca College",
    "Durham College",
    "Mohawk College",
    "Fanshawe College",
]

# Canadian universities (degree programs)
UNIVERSITIES = [
    "Ontario Tech University",
    "University of Toronto",
    "University of Waterloo",
    "McMaster University",
    "Western University",
    "Queen's University",
    "Toronto Metropolitan University",
    "York University",
    "University of Ottawa",
    "Carleton University",
]

# ---------------------------------------------------------------------------
# Target companies — profiles must be working at one of these
# ---------------------------------------------------------------------------

TARGET_COMPANIES = [
    # Core Big Tech
    "Google", "Meta", "Apple", "Amazon", "Microsoft",
    "Netflix", "Nvidia", "Uber", "Airbnb", "Salesforce",
    "Adobe", "PayPal", "LinkedIn", "Spotify",
    # AI / High-Growth
    "OpenAI", "Anthropic", "Cohere", "Databricks", "Snowflake",
    "Scale AI", "Stripe", "Figma", "Notion", "Cloudflare",
    "Datadog", "Palantir",
    # Canadian Big Tech
    "Shopify", "Wealthsimple", "Thomson Reuters", "Lightspeed",
    "Ada", "Faire", "D2L", "ApplyBoard",
    # Gaming
    "Ubisoft", "Electronic Arts", "Riot Games", "Epic Games",
]

# ---------------------------------------------------------------------------
# Rate limiting — be respectful and avoid detection
# ---------------------------------------------------------------------------

# Maximum number of profile pages to visit in a single run
MAX_PROFILES_PER_RUN = 50

# Random delay range (seconds) between navigating to new pages
PAGE_LOAD_DELAY = (3, 7)

# Random delay range (seconds) between visiting individual profile pages
PROFILE_VISIT_DELAY = (8, 15)

# ---------------------------------------------------------------------------
# Anthropic model for message generation
# Set this before running networking/main.py.
#
# Available models (as of 2026):
#   "claude-haiku-4-5-20251001"  — fast and cheap, good for templated messages
#   "claude-sonnet-4-6"          — higher quality, costs more
#
# Leave empty to run without AI personalization (templates only).
# ---------------------------------------------------------------------------
ANTHROPIC_MODEL = ""

# ---------------------------------------------------------------------------
# Message templates
# These are the base templates sent to the Anthropic API for personalization.
# Placeholders: [Name], [Company], [Role], [College], [University]
# ---------------------------------------------------------------------------

# LinkedIn connection request note — strict 300 character limit
CONNECTION_NOTE_TEMPLATE = (
    "Hi [Name] — I'm a CS student at Ontario Tech, graduated Centennial. "
    "I noticed you took a similar path and landed at [Company]. "
    "I'd love to hear your story — would you be open to connecting?"
)

# Follow-up message sent manually after connection is accepted
FOLLOWUP_TEMPLATE = (
    "Hi [Name], my name is Aziz Syed. I'm completing my CS degree at Ontario Tech "
    "after graduating from Centennial College. I noticed you went from [College] to "
    "[University] and are now a [Role] at [Company] — almost exactly the path I'm "
    "hoping to take. After my second year at Centennial, I realized I didn't want to "
    "work just anywhere — I want to be at [Company] because of [COMPANY_VALUE]. "
    "Given you've been in my position, what steps would you advise me to take to make "
    "that a reality? Even one piece of advice would mean a lot."
)
