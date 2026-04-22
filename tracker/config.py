# tracker/config.py
#
# All user-facing configuration lives here.
# To adapt InternHub for your own job search:
#   - Add/remove companies from GREENHOUSE_COMPANIES, LEVER_COMPANIES, etc.
#   - Update LOCATIONS_INCLUDE with your target cities/regions
#   - Update KEYWORDS_INCLUDE / KEYWORDS_EXCLUDE for your target roles
#   - Set APPLIED_COMPANIES to skip roles you've already applied to

# ---------------------------------------------------------------------------
# Community source GitHub repos to parse for job listings.
# These are maintained markdown tables of internship/new-grad postings.
# Format: "owner/repo" — the scraper fetches the raw README.md.
# ---------------------------------------------------------------------------
GITHUB_REPOS = [
    "SimplifyJobs/Summer2026-Internships",
    "negarprh/Canadian-Tech-Internships-2026",  # markdown pipe table format
    # "SimplifyJobs/New-Grad-Positions",  # disabled — intern-only mode
]

# ---------------------------------------------------------------------------
# Greenhouse ATS companies.
# Key = display name, Value = Greenhouse board slug.
# Find a company's slug at: boards.greenhouse.io/{slug}
# ---------------------------------------------------------------------------
GREENHOUSE_COMPANIES = {
    # Verify slugs at: boards.greenhouse.io/{slug}
    # Remove or update any that return 404 — companies switch ATS over time.
    "Faire":        "faire",
    "Figma":        "figma",
    "Vercel":       "vercel",
    "Cloudflare":   "cloudflare",
    "Reddit":       "reddit",
    "Twitch":       "twitch",
    "Lyft":         "lyft",
    "Airbnb":       "airbnb",
    "Coinbase":     "coinbase",
    "MongoDB":      "mongodb",
    "Anthropic":    "anthropic",
    "Stripe":       "stripe",
    "Databricks":   "databricks",  # confirmed 2026-04 — 14 intern jobs
    "Asana":        "asana",       # confirmed 2026-04 — 7 intern jobs
    "Carta":        "carta",       # confirmed 2026-04 — 7 intern jobs
    "Robinhood":    "robinhood",   # confirmed 2026-04 — 7 intern jobs
    "Twilio":       "twilio",      # confirmed 2026-04 — 5 intern jobs
    "Scale AI":     "scaleai",     # confirmed 2026-04 — 4 intern jobs
    "Brex":         "brex",        # confirmed 2026-04 — 2 intern jobs
    "Duolingo":     "duolingo",    # confirmed 2026-04 — 2 intern jobs
    "Mercury":      "mercury",     # confirmed 2026-04 — 2 intern jobs
    "Dropbox":      "dropbox",     # confirmed 2026-04 — 1 intern job
    # --- Toronto / Canadian companies (confirmed Greenhouse boards, 2026-04) ---
    "Ritual":       "ritual",      # confirmed 2026-04 — Software Engineer Intern + Research Intern (Remote)
    "Lightspeed":   "lightspeedhq", # confirmed 2026-04 — board active; intern jobs currently international only (Amsterdam); worth monitoring for Canadian postings
    "Geotab":       "geotab",      # confirmed 2026-04 — Oakville (GTA) company; intern jobs currently international (Germany/UK); worth monitoring
    # --- 0 jobs / empty board as of 2026-04 ---
    # "HubSpot":      "hubspot",       # board exists but 0 total jobs
    # "Ecobee":       "ecobee",        # Toronto IoT; board exists but 0 total jobs as of 2026-04
    # "Benevity":     "benevity",      # Calgary/Toronto; board active, 20 jobs, 0 intern as of 2026-04
    # "TouchBistro":  "touchbistro",   # Toronto; board active, 5 jobs, 0 intern as of 2026-04
    # --- 404 as of 2026-04 — left Greenhouse, ATS unknown ---
    # "Shopify":      "shopify",
    # "OpenAI":       "openai",
    # "Cohere":       "cohere44",
    # "Wealthsimple": "wealthsimple",  # now on Lever (wealthsimple) and Ashby — both 0 jobs
    # "Ada":          "ada",
    # "ApplyBoard":   "applyboard",    # confirmed 404 on GH and Ashby as of 2026-04
    # "Notion":       "notion",
    # "Datadog":      "datadoghq",
    # "Benchling":    "benchling",
    # "Rippling":     "rippling",
    # "Airtable":     "airtable",      # 404 on Greenhouse; try Ashby
    # "Ramp":         "ramp",          # 404 on Greenhouse; try Ashby
    # "Retool":       "retool",        # 404 on Greenhouse
    # "Gusto":        "gusto",         # board exists but 0 intern jobs
    # "Intercom":     "intercom",      # board exists but 0 intern jobs
    # --- Toronto companies: no Greenhouse/Lever/Ashby board found — check custom portals ---
    # "Clio":         "?",             # BC legaltech; not on GH/Lever/Ashby — check jobs.clio.com
    # "Wattpad":      "?",             # Toronto; Lever board (wattpad) exists but 0 tech intern (WEBTOON/LA only)
    # "D2L":          "?",             # Kitchener; Ashby board (d2l) exists but 0 jobs
    # "Koho":         "?",             # Toronto fintech; not on GH/Lever — Ashby board (koho) exists, 0 jobs
    # "FreshBooks":   "?",             # Toronto; Ashby board (freshbooks) exists, 0 jobs — check freshbooks.com/careers
    # "Loopio":       "?",             # Toronto; Ashby board (loopio) exists, 0 jobs
    # "Hootsuite":    "?",             # Vancouver; not on GH/Lever — Ashby board (hootsuite) 0 jobs, Lever timed out
    # "PointClickCare":"?",            # Mississauga; not found on GH/Lever/Ashby — check Workday
    # "Miovision":    "?",             # Waterloo; not found on GH/Lever — check their careers page
    # "Magnet Forensics":"?",          # Ottawa; Lever board (magnetforensics) — 40 jobs, 0 intern
    # "Achievers":    "?",             # Toronto; Lever board (achievers) — 18 jobs, 0 intern
    # "Thomson Reuters":"?",           # Toronto; likely Workday — check careers.thomsonreuters.com
    # "BlackBerry":   "?",             # Waterloo; likely Workday — check blackberry.com/careers
    # "OpenText":     "?",             # Waterloo; not on GH — check Workday
    # "Vidyard":      "?",             # Kitchener; not on GH/Lever/Ashby — check vidyard.com/careers
}

# ---------------------------------------------------------------------------
# Lever ATS companies.
# Key = display name, Value = Lever posting slug.
# Find a company's slug at: jobs.lever.co/{slug}
# ---------------------------------------------------------------------------
LEVER_COMPANIES = {
    # Verify slugs at: jobs.lever.co/{slug}
    # Remove or update any that return 404 — companies switch ATS over time.
    "Plaid":      "plaid",       # confirmed 2026-04 — 94 total jobs, 0 intern currently
    "Palantir":   "palantir",   # confirmed 2026-04 — 20 intern/co-op jobs
    # --- 404 as of 2026-04 — moved to Greenhouse or another ATS ---
    # "Stripe":     "stripe",      # moved to Greenhouse
    # "OpenAI":     "openai",      # moved to Greenhouse or other
    # "Anthropic":  "anthropic",   # moved to Greenhouse
    # "Databricks": "databricks",  # moved to Greenhouse
    # "Scale AI":   "scaleai",     # moved to Greenhouse
    # "Benchling":  "benchling",   # 404 on Lever
    # "Asana":      "asana",       # moved to Greenhouse
    # "Brex":       "brex",        # moved to Greenhouse
    # "Rippling":   "rippling",    # 404 on Lever
}

# ---------------------------------------------------------------------------
# Workday ATS companies.
# Key = display name, Value = (tenant_slug, site_name).
# Find slugs by inspecting the XHR on a Workday jobs page:
#   POST https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
# ---------------------------------------------------------------------------
WORKDAY_COMPANIES = {
    # Format: (tenant_slug, site_name, wd_cluster)
    # Find via DevTools: POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
    "Netflix": ("netflix", "Netflix",                "wd1"),  # confirmed 2026-04
    "Nvidia":  ("nvidia",  "NVIDIAExternalCareerSite", "wd5"),  # confirmed 2026-04
}

# ---------------------------------------------------------------------------
# Tier 2 — Big Tech internal JSON API scrapers (no Playwright required).
# Set a company to False to disable it without removing the code.
# ---------------------------------------------------------------------------
BIG_TECH_ENABLED = {
    "amazon":    True,
    "google":    False,  # Public API deprecated as of 2026-04 — no replacement without authentication
    "microsoft": True,   # Eightfold API — microsoftai.eightfold.ai/api/apply/v2/jobs — confirmed 2026-04
    "apple":     False,  # No public JSON API — jobs.apple.com/api/role/search does not exist; use Playwright instead
    "uber":      False,  # Stub — validate endpoint via DevTools on jobs.uber.com first
}

# ---------------------------------------------------------------------------
# Tier 4 — Playwright scrapers for SPAs that have no public JSON API.
# Requires: pip install playwright && playwright install chromium
# Set to False to skip a scraper without uninstalling Playwright.
# ---------------------------------------------------------------------------
PLAYWRIGHT_JOBS_ENABLED = {
    "meta":   True,
    "tesla":  False,  # Blocked by Cloudflare as of 2026-04 — returns Access Denied to headless Chromium
    "yc":     True,
    "google": True,   # Playwright response interceptor — old careers.google.com API deprecated 2026-04
    "apple":  True,   # Playwright DOM scraper — /api/role/search (big_tech.py) is 404; /api/v1/search requires CSRF auth headless can't fulfill
    "uber":   True,   # Playwright response interceptor — jobs.uber.com blocked by Cloudflare; www.uber.com accessible
}

# ---------------------------------------------------------------------------
# Public sector scrapers (all Tier 4 — Playwright or REST fallback).
# ---------------------------------------------------------------------------
PUBLIC_SECTOR_ENABLED = {
    "govt_canada":    True,
    "ontario_public": False,  # Broken as of 2026-04 — gojobs.gov.on.ca uses Radware CAPTCHA; blocks headless Chromium
    "opg":            True,
    "city_toronto":   True,
}

# ---------------------------------------------------------------------------
# Keywords used by govt_canada.py when searching jobs.gc.ca.
# These are sent as search terms, not used for client-side filtering.
# ---------------------------------------------------------------------------
GOVT_CANADA_KEYWORDS = [
    # Search terms sent to emploisfp-psjobs.cfp-psc.gc.ca.
    # GC Jobs uses "student" not "intern" for co-op/summer programs.
    "student",     # catches "Student Software Developer", "IT Student (Co-op)", etc.
    "co-op",       # catches co-op positions specifically
    "intern",      # included for completeness; GC Jobs currently returns 0 for this
    "software",
    "developer",
    "engineer",
    "programmer",
    "data",
    "technology",
    "IT",
    "information technology",
]

# ---------------------------------------------------------------------------
# Location strings passed to Tier 2 + Tier 3 API query parameters.
# These replace the standard LOCATIONS_INCLUDE for big-tech scrapers —
# the API handles filtering, so we cast a wider net.
# ---------------------------------------------------------------------------
BIG_TECH_LOCATIONS = ["canada", "united states", "usa", "us", "remote"]

# Search query sent to Tier 2 + Tier 3 APIs.
BIG_TECH_SEARCH_QUERY = "software intern"

# ---------------------------------------------------------------------------
# Standard location filter — used by Tier 1, community, and public sector
# scrapers. A posting passes if its location field contains ANY of these
# strings (case-insensitive substring match).
# Add/remove cities and regions to match your target geography.
# ---------------------------------------------------------------------------
LOCATIONS_INCLUDE = [
    "canada",
    "toronto",
    "ontario",
    "gta",
    "scarborough",
    "vancouver",
    "montreal",
    "ottawa",
    "waterloo",
    "remote",
]

# ---------------------------------------------------------------------------
# Keyword include list — a posting passes if its title OR description
# contains AT LEAST ONE of these strings (case-insensitive).
# ---------------------------------------------------------------------------
KEYWORDS_INCLUDE = [
    "intern",
    "internship",
    "co-op",
    "coop",
    "co op",
    "student",     # Government of Canada uses "student" for co-op/summer programs
                   # e.g. "Student Software Developer", "IT Student (Co-op)"
    #"new grad",
    # "entry level",
    #"junior",
    "summer 20",   # matches "Summer 2026/2027" but not standalone "summer"
    "fall 20",     # matches "Fall 2026/2027" but not "fallback" or "shortfall"
    "winter 20",   # matches "Winter 2026/2027"
    "spring 20",   # matches "Spring 2026/2027" but not "offspring" or "springboard"
]

# ---------------------------------------------------------------------------
# Keyword exclude list — a posting is dropped if its title OR description
# contains ANY of these strings (case-insensitive).
# Note the trailing spaces on short tokens (e.g. "vp ", "pm ") to avoid
# false positives on words like "company" or "important".
# ---------------------------------------------------------------------------
KEYWORDS_EXCLUDE = [
    "senior",
    "staff",
    "principal",
    "lead",    # title-only check — avoids false positives on "leadership" in descriptions
    "manager",
    "director",
    "vp ",
    "vice president",
    "qa ",
    "quality assurance",
    "test engineer",
    "product manager",
    "pm ",
    "project manager",
    "sales",
    "marketing",
    "recruiter",
    "hr ",
    "finance",
    "accounting",
    "legal",
]

# ---------------------------------------------------------------------------
# Companies you've already applied to — their postings are silently skipped.
# Add company display names exactly as they appear in job results.
# Example: APPLIED_COMPANIES = ["Shopify", "Google"]
# ---------------------------------------------------------------------------
APPLIED_COMPANIES = []

# ---------------------------------------------------------------------------
# Public sector organizations you've already applied to.
# Example: APPLIED_PUBLIC_ORGS = ["Government of Canada", "OPG"]
# ---------------------------------------------------------------------------
APPLIED_PUBLIC_ORGS = []

# ---------------------------------------------------------------------------
# How often each scraper runs (in minutes).
# launchd fires main.py every 5 minutes; each scraper checks its own
# last_run time and skips if it hasn't been long enough.
# Fast API scrapers run every 5 min; Playwright scrapers run less often
# to avoid rate limits and unnecessary browser overhead.
# ---------------------------------------------------------------------------
SCRAPER_INTERVALS = {
    "github_repos":   5,
    "greenhouse":     5,
    "lever":          5,
    "big_tech":       5,
    "workday":        5,
    "hackernews":     60,
    "yc":             60,
    "meta":           30,
    "tesla":          60,
    "google":         30,
    "apple":          30,
    "uber":           30,
    "govt_canada":    240,
    "ontario_public": 240,
    "opg":            360,
    "city_toronto":   360,
}

# ---------------------------------------------------------------------------
# Email subject prefix. Used in: "{PREFIX} Company — Title (Location)"
# ---------------------------------------------------------------------------
EMAIL_SUBJECT_PREFIX = "🚀"
