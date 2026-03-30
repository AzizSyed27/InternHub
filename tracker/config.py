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
    "SimplifyJobs/New-Grad-Positions",
]

# ---------------------------------------------------------------------------
# Greenhouse ATS companies.
# Key = display name, Value = Greenhouse board slug.
# Find a company's slug at: boards.greenhouse.io/{slug}
# ---------------------------------------------------------------------------
GREENHOUSE_COMPANIES = {
    "Shopify":      "shopify",
    "Cohere":       "cohere44",
    "Wealthsimple": "wealthsimple",
    "Ada":          "ada",
    "Faire":        "faire",
    "ApplyBoard":   "applyboard",
    "HubSpot":      "hubspot",
    "Figma":        "figma",
    "Notion":       "notion",
    "Vercel":       "vercel",
    "Cloudflare":   "cloudflare",
    "Reddit":       "reddit",
    "Twitch":       "twitch",
    "Lyft":         "lyft",
    "Airbnb":       "airbnb",
    "Coinbase":     "coinbase",
    "MongoDB":      "mongodb",
    "Datadog":      "datadoghq",
}

# ---------------------------------------------------------------------------
# Lever ATS companies.
# Key = display name, Value = Lever posting slug.
# Find a company's slug at: jobs.lever.co/{slug}
# ---------------------------------------------------------------------------
LEVER_COMPANIES = {
    "Stripe":     "stripe",
    "OpenAI":     "openai",
    "Anthropic":  "anthropic",
    "Databricks": "databricks",
    "Scale AI":   "scaleai",
    "Benchling":  "benchling",
    "Plaid":      "plaid",
    "Asana":      "asana",
    "Brex":       "brex",
    "Rippling":   "rippling",
}

# ---------------------------------------------------------------------------
# Workday ATS companies.
# Key = display name, Value = (tenant_slug, site_name).
# Find slugs by inspecting the XHR on a Workday jobs page:
#   POST https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
# ---------------------------------------------------------------------------
WORKDAY_COMPANIES = {
    "Netflix": ("netflix", "Netflix_External_Site"),
    "Nvidia":  ("nvidia",  "NVIDIAExternalCareerSite"),
}

# ---------------------------------------------------------------------------
# Tier 2 — Big Tech internal JSON API scrapers (no Playwright required).
# Set a company to False to disable it without removing the code.
# ---------------------------------------------------------------------------
BIG_TECH_ENABLED = {
    "amazon":    True,
    "google":    True,
    "microsoft": True,
    "apple":     True,
    "uber":      True,   # NOTE: Uber is stubbed — validate endpoint via DevTools first
}

# ---------------------------------------------------------------------------
# Tier 4 — Playwright scrapers for SPAs that have no public JSON API.
# Requires: pip install playwright && playwright install chromium
# Set to False to skip a scraper without uninstalling Playwright.
# ---------------------------------------------------------------------------
PLAYWRIGHT_JOBS_ENABLED = {
    "meta":  True,
    "tesla": True,
}

# ---------------------------------------------------------------------------
# Public sector scrapers (all Tier 4 — Playwright or REST fallback).
# ---------------------------------------------------------------------------
PUBLIC_SECTOR_ENABLED = {
    "govt_canada":    True,
    "ontario_public": True,
    "opg":            True,
    "city_toronto":   True,
}

# ---------------------------------------------------------------------------
# Keywords used by govt_canada.py when searching jobs.gc.ca.
# These are sent as search terms, not used for client-side filtering.
# ---------------------------------------------------------------------------
GOVT_CANADA_KEYWORDS = [
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
    "new grad",
    "entry level",
    "junior",
    "software engineer",
    "software developer",
    "swe",
    "full stack",
    "fullstack",
    "backend",
    "front end",
    "frontend",
    "mobile",
    "ios",
    "android",
    "data engineer",
    "ml engineer",
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
    "lead",
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
    "govt_canada":    240,
    "ontario_public": 240,
    "opg":            360,
    "city_toronto":   360,
}

# ---------------------------------------------------------------------------
# Email subject prefix. Used in: "{PREFIX} Company — Title (Location)"
# ---------------------------------------------------------------------------
EMAIL_SUBJECT_PREFIX = "🚀"
