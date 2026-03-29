# InternHub — CLAUDE.md

## What This Project Is

InternHub is a two-tool Python automation suite that runs on a Mac mini:

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

| Company | Endpoint |
|---|---|
| Amazon | `https://www.amazon.jobs/en/search.json?base_query=software+intern&loc_query={location}` |
| Google | `https://careers.google.com/api/jobs/jobs-v1/search/?q=software+intern&location={location}` |
| Microsoft | `https://jobs.careers.microsoft.com/global/en/search?q=intern&lc={location}&l=en_us&pg=1&pgSz=20` |
| Apple | `https://jobs.apple.com/api/role/search` — POST body with location, one POST per location |
| Uber | `jobs.uber.com` — validate exact endpoint via DevTools during build |

**Tier 3 — Workday ATS JSON API (stdlib only)**

```
POST https://{company}.wd5.myworkdayjobs.com/wday/cxs/{company}/{site}/jobs
Body: {"searchText": "software intern", "limit": 20, "offset": 0}
```

**Tier 4 — Playwright (optional dependency, fail gracefully)**

| Source | Scraper |
|---|---|
| Meta | `playwright_jobs.py` |
| Tesla | `playwright_jobs.py` |
| Ontario Public Service | `ontario_public.py` |
| OPG | `opg.py` |
| City of Toronto | `city_toronto.py` |
| Govt Canada | `govt_canada.py` (try REST/RSS first, Playwright fallback) |

**Community Sources (stdlib only)**

| Source | Scraper |
|---|---|
| SimplifyJobs GitHub repos | `github_repos.py` |
| Hacker News Who's Hiring | `hackernews.py` |
| YC Work at a Startup | `yc.py` |

### config.py

```python
GITHUB_REPOS = [
    "SimplifyJobs/Summer2026-Internships",
    "SimplifyJobs/New-Grad-Positions",
]

GREENHOUSE_COMPANIES = {
    "Shopify": "shopify", "Cohere": "cohere44", "Wealthsimple": "wealthsimple",
    "Ada": "ada", "Faire": "faire", "ApplyBoard": "applyboard",
    "HubSpot": "hubspot", "Figma": "figma", "Notion": "notion",
    "Vercel": "vercel", "Cloudflare": "cloudflare", "Reddit": "reddit",
    "Twitch": "twitch", "Lyft": "lyft", "Airbnb": "airbnb",
    "Coinbase": "coinbase", "MongoDB": "mongodb", "Datadog": "datadoghq",
}

LEVER_COMPANIES = {
    "Stripe": "stripe", "OpenAI": "openai", "Anthropic": "anthropic",
    "Databricks": "databricks", "Scale AI": "scaleai", "Benchling": "benchling",
    "Plaid": "plaid", "Asana": "asana", "Brex": "brex", "Rippling": "rippling",
}

WORKDAY_COMPANIES = {
    "Netflix": ("netflix", "Netflix_External_Site"),
    "Nvidia":  ("nvidia",  "NVIDIAExternalCareerSite"),
}

# Tier 2 JSON API scrapers only (no Playwright)
BIG_TECH_ENABLED = {
    "amazon":    True,
    "google":    True,
    "microsoft": True,
    "apple":     True,
    "uber":      True,
}

# Tier 4 Playwright scrapers for heavy SPAs
PLAYWRIGHT_JOBS_ENABLED = {
    "meta":  True,
    "tesla": True,
}

# Tier 2 + Tier 3 use this — bypasses LOCATIONS_INCLUDE
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

# Standard filter — used by Tier 1, community, public sector
# Tier 2 + Tier 3 bypass this and use BIG_TECH_LOCATIONS instead
LOCATIONS_INCLUDE = [
    "canada", "toronto", "ontario", "gta", "scarborough",
    "vancouver", "montreal", "ottawa", "waterloo", "remote",
]

KEYWORDS_INCLUDE = [
    "intern", "internship", "co-op", "coop", "co op",
    "new grad", "entry level", "junior",
    "software engineer", "software developer", "swe",
    "full stack", "fullstack", "backend", "front end", "frontend",
    "mobile", "ios", "android", "data engineer", "ml engineer",
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

## Build Order

### Phase 1 — Scaffolding
1. `.gitignore`
2. `.env.example`
3. `README.md` (stub)
4. `tracker/requirements.txt`
5. `networking/requirements.txt`

### Phase 2 — Internship Tracker
6. `tracker/config.py`
7. `tracker/filters.py`
8. `tracker/db.py`
9. `tracker/scrapers/__init__.py`
10. `tracker/scrapers/github_repos.py`
11. `tracker/scrapers/greenhouse.py`
12. `tracker/scrapers/lever.py`
13. `tracker/scrapers/big_tech.py` — Amazon, Google, Microsoft, Apple, Uber
14. `tracker/scrapers/workday.py` — Netflix, Nvidia
15. `tracker/scrapers/hackernews.py`
16. `tracker/scrapers/yc.py`
17. `tracker/scrapers/playwright_jobs.py` — Meta, Tesla
18. `tracker/scrapers/govt_canada.py`
19. `tracker/scrapers/ontario_public.py`
20. `tracker/scrapers/opg.py`
21. `tracker/scrapers/city_toronto.py`
22. `tracker/emailer.py`
23. `tracker/main.py`
24. `tracker/launchd.plist`

### Phase 3 — LinkedIn Networking Pipeline
25. `networking/config.py`
26. `networking/company_values.json`
27. `networking/profile_parser.py`
28. `networking/message_generator.py`
29. `networking/csv_exporter.py`
30. `networking/linkedin_scraper.py`
31. `networking/main.py`

### Phase 4 — Polish
32. `README.md` — full setup, usage guide, screenshots section
33. Final review pass

---

## Key Decisions

- **One email per posting** — not a digest. Subject: `🚀 Company — Title (Location)`
- **launchd fires every 5 min** — each scraper self-regulates via `SCRAPER_INTERVALS`
- **Tier 2 + Tier 3 bypass `LOCATIONS_INCLUDE`** — use `BIG_TECH_LOCATIONS` via API query params
- **`BIG_TECH_ENABLED` = Tier 2 JSON API scrapers only** (Amazon, Google, Microsoft, Apple, Uber)
- **`PLAYWRIGHT_JOBS_ENABLED` = Meta + Tesla only** — separate from BIG_TECH_ENABLED
- **Tier 1–3 are stdlib only** — zero pip installs
- **Playwright is optional** — Tier 4 scrapers skip gracefully if not installed
- **No LinkedIn automated messaging** — find and log only, all outreach manual
- **MD5 deduplication** — hash of source+company+title+url
- **No database** — JSON for tracker state, CSV for networking output
- **No GitHub Actions** — runs locally on Mac mini via launchd
- **No web UI** — CLI only for v1
- **seen_jobs.json excluded from git**
- **Open source** — no personal details in logic files, everything in config.py or .env

---

## Open Source Notes

- Comment every non-obvious config option with what it does and how to find the value
- README must work for someone who has never used Python
- Message templates in `networking/config.py` written generically with personalization instructions