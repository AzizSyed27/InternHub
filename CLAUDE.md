# InternHub — CLAUDE.md

## What This Project Is

InternHub is a two-tool Python automation suite that runs on a Mac:

- **Tool 1 — Internship Tracker:** Monitors job sources across 4 tiers on a self-regulating schedule, deduplicates postings, and sends one email per new posting found
- **Tool 2 — LinkedIn Networking Pipeline:** Scrapes LinkedIn alumni pages, finds professionals who went college → university → big tech, and exports a CSV with profile data and AI-generated outreach message drafts

Both tools are independent — separate folders, separate schedules, separate dependencies. Full spec is in `PRD.md`.

---

## Project Structure

```
internhub/
│
├── tracker/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── filters.py
│   ├── emailer.py
│   ├── seen_jobs.json
│   ├── requirements.txt
│   └── scrapers/
│       ├── __init__.py
│       ├── github_repos.py
│       ├── greenhouse.py
│       ├── lever.py
│       ├── big_tech.py
│       ├── workday.py
│       ├── hackernews.py
│       ├── yc.py
│       ├── playwright_jobs.py
│       ├── govt_canada.py
│       ├── ontario_public.py
│       ├── opg.py
│       └── city_toronto.py
│
├── networking/
│   ├── main.py
│   ├── config.py
│   ├── linkedin_scraper.py
│   ├── profile_parser.py
│   ├── message_generator.py
│   ├── csv_exporter.py
│   ├── company_values.json
│   └── requirements.txt
│
├── .env.example
├── .gitignore
├── CLAUDE.md
├── README.md
└── PRD.md
```

---

## Tool 1 — Internship Tracker

### Four Scraper Tiers

**Tier 1 — ATS JSON APIs (stdlib only)**

| Source | API |
|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` |
| Lever | `api.lever.co/v0/postings/{slug}?mode=json&limit=250` |

**Tier 2 — Big Tech Career Page APIs (stdlib only)**

Loop over `BIG_TECH_LOCATIONS`, make one request per location, merge and deduplicate results.

| Company | Endpoint | Status |
|---|---|---|
| Amazon | `https://www.amazon.jobs/en/search.json?base_query=software+intern&loc_query={location}` | ✅ Working |
| Google | `https://careers.google.com/api/jobs/jobs-v1/search/?q=software+intern&location={location}` | ❌ Deprecated as of 2026-04 — no public replacement without auth |
| Microsoft | `https://jobs.careers.microsoft.com/global/en/search?q=intern&lc={location}` | ❌ SSL hostname mismatch — re-test on different network |
| Apple | `https://jobs.apple.com/api/role/search` (POST) | ❌ Endpoint does not exist — needs Playwright |
| Uber | `jobs.uber.com` | ❌ Stub — validate endpoint via DevTools first |

**Tier 3 — Workday ATS JSON API (stdlib only)**

```
POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
Headers: Referer: https://{tenant}.{wd}.myworkdayjobs.com/{site}  (required — 422 without it)
Body: {"searchText": "software intern", "limit": 20, "offset": 0, "appliedFacets": {}}
```

Job URL format: `https://{tenant}.{wd}.myworkdayjobs.com/en-US/{site}{externalPath}`

To add a new company: open their Workday careers page in DevTools → Network tab → find the XHR POST to `/wday/cxs/.../jobs` → extract tenant, site name, and wd cluster (wd1/wd3/wd5).

**Tier 4 — Playwright (optional dependency, fail gracefully)**

| Source | Scraper | Notes |
|---|---|---|
| Meta | `playwright_jobs.py` | ✅ |
| Tesla | `playwright_jobs.py` | ✅ |
| Ontario Public Service | `ontario_public.py` | ✅ |
| OPG | `opg.py` | Navigates directly to `/search?q={term}` — home page search input is CSS-hidden |
| City of Toronto | `city_toronto.py` | ✅ |
| Govt Canada | `govt_canada.py` | Playwright only — RSS feed (page2710) removed as of 2026-04; uses page2440 |
| YC Work at a Startup | `yc.py` | Playwright only — `/jobs.json` endpoint returned HTTP 500 as of 2026-04; navigates `workatastartup.com/jobs?q=intern` |

**Community Sources (stdlib only)**

| Source | Scraper | Notes |
|---|---|---|
| SimplifyJobs GitHub repos | `github_repos.py` | Uses `dev` branch, falls back to `main`; HTML `<table>` parser (switched from markdown pipe tables 2026-04); `New-Grad-Positions` currently disabled |
| Hacker News Who's Hiring | `hackernews.py` | |

### config.py (current state as of 2026-04)

```python
GITHUB_REPOS = [
    "SimplifyJobs/Summer2026-Internships",
    # "SimplifyJobs/New-Grad-Positions",  # disabled — intern-only mode
]

GREENHOUSE_COMPANIES = {
    # Confirmed working as of 2026-04
    "Faire":        "faire",
    "HubSpot":      "hubspot",
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
    # 404 as of 2026-04 — companies left Greenhouse or changed slugs:
    # "Shopify", "Cohere", "Wealthsimple", "Ada", "ApplyBoard",
    # "Notion", "Datadog", "OpenAI", "Databricks"
}

LEVER_COMPANIES = {
    # Confirmed working as of 2026-04
    "Plaid": "plaid",
    # 404 as of 2026-04 — moved to Greenhouse or other ATS:
    # "Stripe" → Greenhouse, "OpenAI" → check, "Anthropic" → Greenhouse,
    # "Databricks", "Scale AI", "Benchling", "Asana", "Brex", "Rippling"
}

WORKDAY_COMPANIES = {
    # Format: (tenant_slug, site_name, wd_cluster)
    # Find via DevTools: POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
    "Netflix": ("netflix", "Netflix",                "wd1"),  # confirmed 2026-04
    "Nvidia":  ("nvidia",  "NVIDIAExternalCareerSite", "wd5"),  # confirmed 2026-04
}

BIG_TECH_ENABLED = {
    "amazon":    True,
    "google":    False,  # Public API deprecated — no replacement without auth
    "microsoft": False,  # SSL hostname mismatch — re-test on different network
    "apple":     False,  # No public JSON API — needs Playwright
    "uber":      False,  # Stub — validate endpoint via DevTools on jobs.uber.com first
}

PLAYWRIGHT_JOBS_ENABLED = {
    "meta":  True,
    "tesla": True,
    "yc":    True,
}

BIG_TECH_LOCATIONS = ["canada", "united states", "usa", "us", "remote"]
BIG_TECH_SEARCH_QUERY = "software intern"

PUBLIC_SECTOR_ENABLED = {
    "govt_canada":    True,
    "ontario_public": True,
    "opg":            True,
    "city_toronto":   True,
}

GOVT_CANADA_KEYWORDS = [
    "software", "developer", "engineer", "programmer",
    "data", "technology", "IT", "information technology",
]

LOCATIONS_INCLUDE = [
    "canada", "toronto", "ontario", "gta", "scarborough",
    "vancouver", "montreal", "ottawa", "waterloo", "remote",
]

# Role-level + season indicators ONLY.
# Do NOT add tech stack keywords (backend, frontend, etc.) — they match senior full-time titles.
# Season keywords use "20" suffix to match "Summer 2026" but not standalone "summer".
KEYWORDS_INCLUDE = [
    "intern",
    "internship",
    "co-op",
    "coop",
    "co op",
    # "new grad",     # disabled — intern-only mode
    # "entry level",  # disabled — intern-only mode
    # "junior",       # disabled — intern-only mode
    "summer 20",
    "fall 20",
    "winter 20",
    "spring 20",
]

KEYWORDS_EXCLUDE = [
    "senior", "staff", "principal", "lead", "manager",
    "director", "vp ", "vice president", "qa ", "quality assurance",
    "test engineer", "product manager", "pm ", "project manager",
    "sales", "marketing", "recruiter", "hr ", "finance", "accounting", "legal",
]

APPLIED_COMPANIES = []
APPLIED_PUBLIC_ORGS = []

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

EMAIL_SUBJECT_PREFIX = "🚀"
```

### filters.py behaviour

- `passes_filters(job, tier)` checks: applied-company, applied-public-org (public_sector tier), keyword include (title only), keyword exclude (title only), location (skipped for big_tech and github tiers).
- `title_lower` is used for both include and exclude checks — description is NOT checked. This avoids false positives like "intern" matching "internal" in a senior job's description body.
- Tier 2 + Tier 3 pass `tier="big_tech"` → location check skipped; API query params handle geography.
- GitHub scraper passes `tier="github"` → location check also skipped; SimplifyJobs is a curated global list and filtering by city would drop valid remote/US postings.
- Public sector scrapers pass `tier="public_sector"` → `APPLIED_PUBLIC_ORGS` checked in addition to `APPLIED_COMPANIES`.

### Location Filter Rule

Tier 2 (`big_tech.py`) and Tier 3 (`workday.py`) bypass `LOCATIONS_INCLUDE`. Location filtering is handled by API query parameters using `BIG_TECH_LOCATIONS`. Only keyword and applied-company filters apply to their results.

### Email

- One email per new posting — not a digest
- Subject: `🚀 [Company] — [Job Title] ([Location])`
- HTML dark-mode card: company, role, source badge, location, date, 300-char description excerpt, Apply Now button
- Gmail SMTP + App Password, no OAuth

### Deduplication

- ID: `md5(source_prefix + company + title + url)`
- `seen_jobs.json` stores seen IDs + last run timestamp per scraper

```json
{
  "seen_ids": ["abc123"],
  "last_run": {
    "github_repos": "2026-03-23T14:00:00",
    "greenhouse":   "2026-03-23T14:00:00"
  }
}
```

### Scheduling

`launchd.plist` fires `main.py` every 5 minutes using absolute paths. Each scraper checks its last run time against `SCRAPER_INTERVALS` and skips if not due.

**Seeding behaviour:** On first run (empty `seen_jobs.json`), all current postings are indexed without sending emails. `last_run` timestamps are NOT set during seeding — this ensures all scrapers are immediately due on the very next run, so emails fire right away.

---

## Scraper Health Watchlist

These scrapers parse HTML or DOM structure directly and are most likely to break silently if the source site changes its layout. Check these first if a scraper suddenly returns 0 results.

| Scraper | File | Risk | Last verified |
|---|---|---|---|
| SimplifyJobs repos | `github_repos.py` | Switched markdown→HTML tables 2026-04 (fixed). Could change again. | 2026-04 |
| Hacker News Who's Hiring | `hackernews.py` | Parses HN comment HTML. HN rarely changes layout, but format shift = silent 0 results. | — |
| YC Work at a Startup | `yc.py` | Already broke once (HTTP 500 on `/jobs.json` 2026-04). Now Playwright on `workatastartup.com/jobs`. CSS selectors could break on redesign. | 2026-04 |
| Meta careers | `playwright_jobs.py` | Playwright CSS selectors. Meta redesigns career pages. | — |
| Tesla careers | `playwright_jobs.py` | Playwright CSS selectors. Tesla career pages change frequently. | — |
| Govt Canada | `govt_canada.py` | Already broke once (RSS page2710 removed 2026-04). Now Playwright on page2440. | 2026-04 |
| Ontario Public Service | `ontario_public.py` | Playwright CSS selectors on OPS careers portal. | — |
| OPG | `opg.py` | Playwright, navigates directly to `/search?q=` (home search is CSS-hidden). | — |
| City of Toronto | `city_toronto.py` | Playwright CSS selectors on city portal. | — |

**How to spot a broken scraper:** It runs without error but returns 0 results — or far fewer than usual. Add a `print(f"[scraper_name] {len(jobs)} jobs found")` and run the scraper manually to check.

**JSON API scrapers (lower risk):** Greenhouse, Lever, Workday — these return structured JSON. A breaking change usually produces an HTTP error or schema mismatch, not silent 0 results.

---

## Next Steps

- **Google Jobs scraping** — scrape `jobs.google.com` for internship listings. The old `careers.google.com` API is deprecated. Need to identify the current internal API endpoint via DevTools on `jobs.google.com` (search for "intern", capture the XHR/fetch request). Likely a Playwright scraper or a new JSON API endpoint. Add to `big_tech.py` or a new `google_jobs.py`.

---

## Tool 2 — LinkedIn Networking Pipeline

### How It Works

1. Log into LinkedIn via Playwright using `.env` credentials
2. Navigate alumni pages for each target school
3. Filter alumni by each target company
4. Visit matching profiles and extract data
5. Call Anthropic API to generate personalized outreach drafts per profile
6. Export to timestamped CSV

### Target Schools

**Colleges:** Centennial, Sheridan, Humber, George Brown, Seneca, Durham, Mohawk, Fanshawe

**Universities:** Ontario Tech, UofT, Waterloo, McMaster, Western, Queens, Toronto Metropolitan, York, Ottawa, Carleton

### Target Companies (35)

**Core Big Tech:** Google, Meta, Apple, Amazon, Microsoft, Netflix, Nvidia, Uber, Airbnb, Salesforce, Adobe, PayPal, LinkedIn, Spotify

**AI / High-Growth:** OpenAI, Anthropic, Cohere, Databricks, Snowflake, Scale AI, Stripe, Figma, Notion, Cloudflare, Datadog, Palantir

**Canadian Big Tech:** Shopify, Wealthsimple, Thomson Reuters, Lightspeed, Ada, Faire, D2L, ApplyBoard

**Gaming:** Ubisoft Montreal, EA, Riot Games, Epic Games

### Profile Match Criteria

Must have ALL THREE:
1. College diploma from any Ontario college
2. University degree from any Canadian university
3. Current technical role at one of the 35 target companies

### Message Templates

**Connection note (≤300 chars):**
> Hi [Name] — I'm a CS student at Ontario Tech, graduated Centennial. I noticed you took a similar path and landed at [Company]. I'd love to hear your story — would you be open to connecting?

**Follow-up (after acceptance):**
> Hi [Name], my name is Aziz Syed. I'm completing my CS degree at Ontario Tech after graduating from Centennial College. I noticed you went from [College] to [University] and are now a [Role] at [Company] — almost exactly the path I'm hoping to take. After my second year at Centennial, I realized I didn't want to work just anywhere — I want to be at [Company] because of [company-specific value]. Given you've been in my position, what steps would you advise me to take to make that a reality? Even one piece of advice would mean a lot.

Company values come from `company_values.json` — never hallucinate.

### CSV Output

`networking_results_YYYY-MM-DD.csv`

Columns: `name`, `linkedin_url`, `current_company`, `current_role`, `college`, `university`, `connection_degree`, `connection_note_draft`, `followup_message_draft`, `contacted`, `replied`, `notes`

### Rate Limiting

- Max 50 profile visits per run
- 3–7 second random delay between page loads
- 8–15 second random delay between profile visits
- On-demand only — never scheduled
- No automated messages or connection requests

---

## Environment Variables

```bash
# .env — never commit

# Tool 1
EMAIL_SENDER=your.gmail@gmail.com
EMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
EMAIL_RECIPIENT=your.email@gmail.com

# Tool 2
LINKEDIN_EMAIL=your.linkedin@email.com
LINKEDIN_PASSWORD=your_linkedin_password
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Key Decisions

- **One email per posting** — not a digest. Subject: `🚀 Company — Title (Location)`
- **launchd fires every 5 min** — each scraper self-regulates via `SCRAPER_INTERVALS`
- **Tier 2 + Tier 3 bypass `LOCATIONS_INCLUDE`** — use `BIG_TECH_LOCATIONS` via API query params
- **`BIG_TECH_ENABLED` = Tier 2 JSON API scrapers only** (Amazon, Google, Microsoft, Apple, Uber)
- **`PLAYWRIGHT_JOBS_ENABLED` = Meta, Tesla, YC** — separate from BIG_TECH_ENABLED
- **Tier 1–3 are stdlib only** — zero pip installs (except certifi for macOS SSL); YC moved from Tier 3 to Tier 4 (Playwright) in 2026-04 when `/jobs.json` was deprecated
- **Playwright is optional** — Tier 4 scrapers skip gracefully if not installed
- **No LinkedIn automated messaging** — find and log only, all outreach manual
- **MD5 deduplication** — hash of source+company+title+url
- **No database** — JSON for tracker state, CSV for networking output
- **No GitHub Actions** — runs locally on Mac via launchd
- **No web UI** — CLI only for v1
- **seen_jobs.json excluded from git**
- **Open source** — no personal details in logic files, everything in config.py or .env
- **KEYWORDS_INCLUDE = role-level only** — no tech stack terms (backend, frontend, etc.) to avoid matching senior full-time job titles
- **Keyword include checks title only** — not description, to prevent "intern" matching "internal" in a senior job's description
- **Seed run does not set last_run timestamps** — ensures all scrapers are immediately due on the first real run after seeding
- **macOS SSL** — `certifi` added to requirements; `main.py` patches `ssl._create_default_https_context` on startup
- **SimplifyJobs repos use `dev` branch** — `github_repos.py` tries `dev` first, falls back to `main`
- **Workday URL format** — job links require `/en-US/{site}` prefix before `externalPath`; Referer header and `appliedFacets: {}` in POST body are required
- **OPG search** — home page search input is CSS-hidden; scraper navigates directly to `/search?q={term}`
- **Govt Canada** — RSS feed (page2710) removed as of 2026-04; scraper uses Playwright on page2440; uses `urllib.parse.quote` (NOT `urllib.request.quote` — that module has no `quote` function)
- **YC Work at a Startup** — `/jobs.json` endpoint returned HTTP 500 as of 2026-04; converted to Playwright scraper navigating `workatastartup.com/jobs?q=intern`; gated by `PLAYWRIGHT_JOBS_ENABLED["yc"]`
- **`github_repos.py` uses `html.parser`** — SimplifyJobs switched README format from markdown pipe tables to HTML `<table>` in 2026-04; parser rewritten using stdlib `html.parser`; no new dependencies
- **`"github"` tier bypasses location filter** — same mechanism as `"big_tech"` tier; SimplifyJobs is a curated global list so location filtering would drop valid US/remote postings
- **SimplifyJobs company names may have emoji prefixes** — FAANG-tier companies are tagged `🔥, Cloudflare` in the HTML; `APPLIED_COMPANIES` entries must match the exact parsed string; workaround is to rely on Greenhouse/Lever/Workday scrapers for those companies instead
- **New-Grad-Positions disabled** — `SimplifyJobs/New-Grad-Positions` commented out of `GITHUB_REPOS` as of 2026-04; re-enable to include new-grad roles

---

## Open Source Notes

- Comment every non-obvious config option with what it does and how to find the value
- README must work for someone who has never used Python
- Message templates in `networking/config.py` written generically with personalization instructions
