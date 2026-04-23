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
| Amazon | `https://www.amazon.jobs/en/search.json?base_query={query}&result_limit=100` | ✅ Working — queries `["software intern", "software internship"]` (no stemming); `loc_query` ignored by API |
| Google | `https://careers.google.com/api/jobs/jobs-v1/search/?q=software+intern&location={location}` | ❌ Deprecated as of 2026-04 — no public replacement without auth |
| Microsoft | `https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query={query}&start={offset}&num_jobs=100` | ✅ Working — Eightfold PCSX API; old jobs.careers.microsoft.com had SSL mismatch (fixed 2026-04) |
| Apple | `https://jobs.apple.com/api/role/search` (POST) | ❌ Endpoint does not exist — moved to Playwright (`playwright_jobs.py`) |
| Uber | `jobs.uber.com` | ❌ Cloudflare-blocked — moved to Playwright (`playwright_jobs.py`) |

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
| Meta | `playwright_jobs.py` | ✅ Rewrote 2026-04: now intercepts GraphQL response at `/graphql` (old CSS selector broke on SPA redesign) |
| Google | `playwright_jobs.py` | ✅ Added 2026-04: DOM scraper on `google.com/about/careers/applications/jobs/results?employment_type=INTERN&q=software`; job cards are `li.lLd3Je`, title `h3.QJPWVe`, link is relative href → prefixed with `/about/careers/applications/`, location from `.wVoYLb` text after `place\n` marker |
| Apple | `playwright_jobs.py` | ✅ Added 2026-04: DOM scraper on `jobs.apple.com/en-ca/search?location=canada-CANC+united-states-USA&key=Software&team=internships-STDNT-INTRN`; job links `ul#search-job-list a[href*='/details/']`, dedup by `.job-posted-date` sibling presence; pagination via `[aria-label="Next Page"]` |
| Uber | `playwright_jobs.py` | ✅ Added 2026-04: response interceptor on `www.uber.com/ca/en/careers/list/?query=Intern&department=University`; `jobs.uber.com` is Cloudflare-blocked but `www.uber.com` is accessible; heuristic JSON traversal finds job array in XHR responses; job URL: `uber.com/global/en/careers/list/{jobId}/` |
| Tesla | `playwright_jobs.py` | ❌ Disabled 2026-04 — Cloudflare blocks headless Chromium (Access Denied). No public API found. |
| Ontario Public Service | `ontario_public.py` | ❌ Disabled 2026-04 — old URL 404; new portal (gojobs.gov.on.ca) uses Radware CAPTCHA |
| OPG | `opg.py` | ✅ Navigates directly to `/search?q={term}` — home page search input is CSS-hidden |
| City of Toronto | `city_toronto.py` | ✅ Updated URL 2026-04: old `toronto.ca/...` was 404; now `jobs.toronto.ca/jobsatcity/search/?q=intern` |
| Govt Canada | `govt_canada.py` | ✅ Updated selector 2026-04: `table.resultTable tr` matched nothing; now `a[href*='page1800']` |
| YC Work at a Startup | `yc.py` | ✅ Authenticated DOM scraper on `workatastartup.com/internships` — logs in via `account.ycombinator.com` (YC_EMAIL/YC_PASSWORD in .env) to unlock full listing (~44 raw jobs); falls back to 15 without credentials; location filter bypassed (tier="github"); old `/jobs.json` was HTTP 500 as of 2026-04 |
| intern-list.com | `playwright_jobs.py` | ✅ Added 2026-04: DOM scraper on Jobright embed pages — US: `jobright.ai/minisites-jobs/intern/us/swe?embed=true`, Canada: `jobright.ai/minisites-jobs/intern/ca/swe?embed=true`; rows: `tr[data-index]`, title: `td[1]`, location: `td[5]`, company: `td[6]`, apply link: `a[href*='/jobs/info/']`; virtual scroll via nearest `overflow-y:auto` ancestor; returns ~900 jobs (US + Canada); location filter bypassed (tier="github", aggregate board like SimplifyJobs); "Multi Locations: X; Y" prefix stripped to first location |
| Google for Jobs | `playwright_jobs.py` | ✅ Added 2026-04: DOM scraper on `google.com/search?q={q}&ibp=htl;jobs` (the aggregator vertical — NOT careers.google.com). Loops 3 SWE-intern queries. Semantic selectors only: `div[role="main"] [role="list"]` → `[role="listitem"]` → `[role="heading"][aria-level="3"]`. Reads company/location from card inner text (line after title; location = first `·`-separated segment). Clicks card → harvests `a[href^="http"]` with "apply" in aria-label or text → picks by priority (company-domain match → non-aggregator host → first). Bails on `/sorry/`, `consent.google.com`, recaptcha iframe, or "unusual traffic" text. Fragility tripwire: >30% empty-company → WARN + return []. `tier="github"` bypasses location filter. 4-hour SCRAPER_INTERVAL to minimize bot-detection exposure. |

**Community Sources (stdlib only)**

| Source | Scraper | Notes |
|---|---|---|
| SimplifyJobs GitHub repos | `github_repos.py` | Uses `dev` branch, falls back to `main`; HTML `<table>` parser (switched from markdown pipe tables 2026-04); `New-Grad-Positions` currently disabled |
| negarprh/Canadian-Tech-Internships-2026 | `github_repos.py` | Markdown pipe table format; `main` branch only (no dev); 5 columns: Company \| Role \| Location \| Apply \| Date Posted |
| Hacker News Who's Hiring | `hackernews.py` | |

### config.py (current state as of 2026-04)

```python
GITHUB_REPOS = [
    "SimplifyJobs/Summer2026-Internships",
    "negarprh/Canadian-Tech-Internships-2026",  # markdown pipe table format
    # "SimplifyJobs/New-Grad-Positions",  # disabled — intern-only mode
]

GREENHOUSE_COMPANIES = {
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
    # --- 0 jobs / empty board as of 2026-04 ---
    # "HubSpot":      "hubspot",
    # --- 404 as of 2026-04 — left Greenhouse, ATS unknown ---
    # "Shopify", "OpenAI", "Cohere", "Wealthsimple", "Ada", "ApplyBoard",
    # "Notion", "Datadog", "Benchling", "Rippling", "Airtable", "Ramp"
}

LEVER_COMPANIES = {
    "Plaid":    "plaid",     # confirmed 2026-04 — 94 total jobs, 0 intern currently
    "Palantir": "palantir",  # confirmed 2026-04 — 20 intern/co-op jobs
    # --- 404 as of 2026-04 — moved to Greenhouse or another ATS ---
    # "Stripe", "OpenAI", "Anthropic", "Databricks", "Scale AI" → all on Greenhouse now
    # "Benchling", "Asana", "Brex" → Greenhouse; "Rippling" → unknown
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
    "microsoft": True,   # Eightfold PCSX API — apply.careers.microsoft.com/api/pcsx/search — confirmed 2026-04
    "apple":     False,  # No public JSON API — needs Playwright
    "uber":      False,  # Cloudflare-blocked on jobs.uber.com — moved to PLAYWRIGHT_JOBS_ENABLED
}

PLAYWRIGHT_JOBS_ENABLED = {
    "meta":        True,
    "tesla":       False,  # Cloudflare blocks headless Chromium as of 2026-04
    "yc":          True,
    "google":      True,   # DOM scraper — old careers.google.com API deprecated 2026-04
    "apple":       True,   # DOM scraper — /api/role/search is 404; /api/v1/search requires CSRF auth headless can't fulfill
    "uber":        True,   # Response interceptor — jobs.uber.com Cloudflare-blocked; www.uber.com accessible
    "intern_list": True,   # DOM scraper on jobright.ai embed pages — US + Canada SWE intern tabs; added 2026-04
    "google_jobs": True,   # Google for Jobs aggregator — google.com/search?...&ibp=htl;jobs; added 2026-04; 4-hour interval
}

BIG_TECH_LOCATIONS = ["canada", "united states", "usa", "us", "remote"]
# NOTE: BIG_TECH_LOCATIONS and BIG_TECH_SEARCH_QUERY are no longer used by Amazon.
# Amazon's loc_query parameter is silently ignored (any value returns the same results).
# Amazon also requires two separate queries — see _AMAZON_QUERIES in big_tech.py.
# BIG_TECH_SEARCH_QUERY is still used by the Google/Microsoft/Apple scrapers.
BIG_TECH_SEARCH_QUERY = "software intern"

PUBLIC_SECTOR_ENABLED = {
    "govt_canada":    True,
    "ontario_public": False,  # Broken 2026-04 — gojobs.gov.on.ca uses Radware CAPTCHA
    "opg":            True,
    "city_toronto":   True,
}

GOVT_CANADA_KEYWORDS = [
    "student",     # GC Jobs uses "student" not "intern" for co-op/summer programs
    "co-op",
    "intern",
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
# "student" added for Government of Canada positions (GC uses "Student Software Developer" etc.)
KEYWORDS_INCLUDE = [
    "intern",
    "internship",
    "co-op",
    "coop",
    "co op",
    "student",      # Government of Canada uses "student" for co-op/summer programs
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
    "google":         30,
    "apple":          30,
    "uber":           30,
    "intern_list":    30,
    "google_jobs":    240,  # 4 hours — minimize Google bot-detection exposure
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

| Scraper | File | Status | Risk | Last verified |
|---|---|---|---|---|
| SimplifyJobs repos | `github_repos.py` | ✅ | Switched markdown→HTML tables 2026-04 (fixed). Could change again. | 2026-04 |
| Canadian Tech Internships 2026 | `github_repos.py` | ✅ | Markdown pipe table; added 2026-04. Selectors: column index 0–3 (Company/Role/Location/Apply). If 0 jobs, check repo still uses pipe table format. | 2026-04 |
| Hacker News Who's Hiring | `hackernews.py` | ✅ | Parses HN comment HTML. HN rarely changes layout, but format shift = silent 0 results. | — |
| YC Work at a Startup | `yc.py` | ✅ | Authenticated DOM scraper on `workatastartup.com/internships`. Login via `#ycid-input` + `#password-input` on `account.ycombinator.com/authenticate`. Two DOM layouts: logged-in uses `img[alt]` for company name; logged-out uses `span.font-bold`. Location from first `<span>` in metadata div. If 0 jobs, check selectors or verify credentials. | 2026-04 |
| Meta careers | `playwright_jobs.py` | ✅ | Rewrote 2026-04 to intercept GraphQL response instead of CSS selector (SPA redesign broke old approach). Response key `job_search_with_featured_jobs.all_jobs` could change. | 2026-04 |
| Google careers | `playwright_jobs.py` | ✅ | Added 2026-04: DOM scraper. Selectors `li.lLd3Je` (cards), `h3.QJPWVe` (title), `.wVoYLb` (location). High risk — obfuscated CSS class names could change on any deploy. | 2026-04 |
| Apple careers | `playwright_jobs.py` | ✅ | Added 2026-04: DOM scraper. `ul#search-job-list a[href*='/details/']`; deduped via `.job-posted-date` sibling; `wait_until="load"` + `wait_for_selector` (networkidle never resolves — persistent analytics connections). Pagination via `[aria-label="Next Page"]`. | 2026-04 |
| Tesla careers | `playwright_jobs.py` | ❌ DISABLED | Cloudflare blocks headless Chromium as of 2026-04. No public API found. | 2026-04 |
| Uber careers | `playwright_jobs.py` | ✅ | Added 2026-04: response interceptor on `www.uber.com`. Heuristic JSON traversal finds job array. If 0 jobs returned, inspect XHR on `www.uber.com/ca/en/careers/list/?query=Intern&department=University` and update `_on_response` key path. | 2026-04 |
| Govt Canada | `govt_canada.py` | ✅ | Selector updated 2026-04: `table.resultTable tr` was wrong; now `a[href*='page1800']`. GC jobs uses "student" not "intern" in titles. | 2026-04 |
| Ontario Public Service | `ontario_public.py` | ❌ DISABLED | gojobs.gov.on.ca (new OPS portal) uses Radware CAPTCHA — blocks headless Chromium. | 2026-04 |
| OPG | `opg.py` | ✅ | Playwright, navigates directly to `/search?q=` (home search is CSS-hidden). | 2026-04 |
| City of Toronto | `city_toronto.py` | ✅ | URL updated 2026-04: old `toronto.ca/city-government/...` is 404; now `jobs.toronto.ca/jobsatcity/search/?q=intern`. | 2026-04 |
| intern-list.com | `playwright_jobs.py` | ✅ | Added 2026-04: DOM scraper on `jobright.ai/minisites-jobs/intern/{us\|ca}/swe?embed=true`. Rows: `tr[data-index]`, apply: `a[href*='/jobs/info/']`. Virtual scroll via nearest `overflow-y:auto` ancestor. CSS module class names (`index_bodyViewport`, `index_tableRow`) may change — `tr[data-index]` and `/jobs/info/` href are stable. If 0 jobs, check if `tr[data-index]` still exists on the embed page. | 2026-04 |
| Google for Jobs | `playwright_jobs.py` | ✅ | Added 2026-04: DOM scraper on the aggregator vertical `google.com/search?...&ibp=htl;jobs`. **High risk** — Google actively fights scrapers, recaptcha can fire, DOM obfuscated. Uses only semantic selectors (`role=list`, `role=listitem`, `role=heading`, `aria-level`). Cookie-consent interstitial is auto-dismissed by `_dismiss_consent_if_needed()` (clicks "Reject all" / "Accept all" / "I agree"). If 0 jobs: (1) open URL in DevTools and confirm cards still wrap in `[role="listitem"]`; (2) if consent-dismiss WARN fires, the consent page button labels may have changed — re-verify the button selectors; (3) if `/sorry/` challenge fires, disable temporarily via `PLAYWRIGHT_JOBS_ENABLED["google_jobs"] = False`. Tripwire: >30% empty-company → self-aborts with WARN. **If this repeatedly breaks, disable permanently — aggregator overlaps 80%+ with existing ATS scrapers.** | 2026-04 |

**How to spot a broken scraper:** `main.py` now logs `[scraper_name] N jobs returned, M new` for every run. A scraper returning 0 that used to return results is a signal to investigate.

**JSON API scrapers (lower risk):** Greenhouse, Lever, Workday — these return structured JSON. A breaking change usually produces an HTTP error or schema mismatch, not silent 0 results. Amazon's `jobs` list field was silently renamed from `hits` in 2026-04 (fixed).

---

## Next Steps

- **Find more Canada-focused internship GitHub repos** — `negarprh/Canadian-Tech-Internships-2026` added 2026-04 (markdown pipe table). Look for additional Canadian co-op boards; `github_repos.py` handles both HTML `<table>` and markdown pipe table formats automatically.
- **Uber pagination** — current Playwright response interceptor captures whatever the SPA loads on first render. If there are more than one page of intern results, check whether the page has a "Load more" or pagination control and extend `_scrape_uber()` accordingly.
- **Find ATS for 404 Greenhouse companies** — the following were on Greenhouse but are now 404; find where they moved and add them back: Shopify, OpenAI, Cohere, Ada, Notion, Datadog, Benchling, Rippling, Airtable, Ramp. Check Ashby (`jobs.ashbyhq.com/{slug}`), Workday, or their own careers page.
- **Check Ashby ATS** — several companies that left Greenhouse/Lever have moved to Ashby (e.g., Ramp, Airtable, Linear, Retool). Ashby has a public API at `jobs.ashbyhq.com/api/non-user-graphql` — worth implementing a new `ashby.py` Tier 1 scraper if enough target companies use it.
- **YC scraper** — Fixed and authenticated 2026-04. Now scrapes `workatastartup.com/internships` with YC login. If returning 0, check credentials in `.env` (`YC_EMAIL`/`YC_PASSWORD`) and verify `#ycid-input` / `#password-input` selectors on `account.ycombinator.com/authenticate` still exist.
- **Toronto/GTA company Workday check** — Thomson Reuters, PointClickCare (Mississauga), BlackBerry (Waterloo), OpenText (Waterloo) likely use Workday; find their tenant slugs via DevTools on their careers pages and add to `WORKDAY_COMPANIES`.

### Toronto / Scarborough / GTA Company Research (2026-04)

Checked ~50 Toronto-area companies across Greenhouse, Lever, and Ashby. Results:

**Added to `GREENHOUSE_COMPANIES`:**
| Company | Slug | Notes |
|---|---|---|
| Ritual | `ritual` | Toronto food-tech; Software Engineer Intern + Research Intern (Remote) — confirmed 2026-04 |
| Lightspeed | `lightspeedhq` | Montreal POS/commerce; board active (182 jobs); intern jobs currently Amsterdam only — worth monitoring |
| Geotab | `geotab` | Oakville (GTA) fleet tech; board active (80 jobs); intern jobs currently Germany/UK only — worth monitoring |

**Greenhouse boards exist but 0 intern jobs (monitor, don't add yet):**
- `ecobee` — Toronto smart home (Ecobee); board exists, 0 total jobs
- `benevity` — Calgary/Toronto CSR platform; 20 total jobs, 0 intern
- `touchbistro` — Toronto restaurant tech; 5 total jobs, 0 intern

**Lever boards exist but 0 relevant intern jobs:**
- `wealthsimple` — 0 total jobs (empty board)
- `achievers` — Toronto HR platform; 18 jobs, 0 intern
- `wattpad` — Toronto storytelling; 14 jobs, 2 "intern" titles but they're WEBTOON marketing (Los Angeles)
- `magnetforensics` — Ottawa digital forensics; 40 jobs, 0 intern

**Ashby boards confirmed (all 0 jobs as of 2026-04):**
Wealthsimple, FreshBooks, Koho, Loopio, D2L, Hootsuite, Clearco, League, PointClickCare, Achievers, Neo Financial, Financeit, TouchBistro, Kira Systems, ApplyBoard, Vena Solutions, Top Hat, Clio, Lightspeed — boards verified but no postings. Re-check seasonally.

**No ATS found — investigate custom portals or Workday:**
- **Clio** (Burnaby BC) — not on GH/Lever/Ashby; check `clio.com/careers`
- **FreshBooks** (Toronto) — Ashby board (0 jobs); check `freshbooks.com/careers`
- **Koho** (Toronto fintech) — Ashby board (0 jobs)
- **D2L** (Kitchener LMS) — Ashby board (0 jobs); check `d2l.com/careers`
- **Hootsuite** (Vancouver) — Ashby board (0 jobs); Lever timed out
- **Miovision** (Waterloo traffic AI) — not found on any ATS; check `miovision.com/careers`
- **Vidyard** (Kitchener video) — not found on GH/Lever/Ashby; check `vidyard.com/careers`
- **Thomson Reuters** (Toronto) — likely Workday; check `careers.thomsonreuters.com`
- **PointClickCare** (Mississauga) — likely Workday; check `pointclickcare.com/careers`
- **BlackBerry** (Waterloo) — likely Workday; check `blackberry.com/en/us/company/careers`
- **OpenText** (Waterloo) — likely Workday; check `opentext.com/careers`

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

# YC Work at a Startup — optional, unlocks full listing (~44 raw jobs vs 15 without login)
YC_EMAIL=your.yc@email.com
YC_PASSWORD=your_yc_password

# Tool 2
LINKEDIN_EMAIL=your.linkedin@email.com
LINKEDIN_PASSWORD=your_linkedin_password
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Key Decisions

- **One email per posting** — not a digest. Subject: `🚀 Company — Title (Location)`
- **launchd fires every 5 min** — each scraper self-regulates via `SCRAPER_INTERVALS`
- **Tier 1, 2, 3 all bypass `LOCATIONS_INCLUDE`** — Greenhouse/Lever pass `tier="big_tech"` (same as Tier 2/3); all are curated company lists where you want all intern postings regardless of location. Location filter only applies to community (HN) and public sector tiers.
- **`BIG_TECH_ENABLED` = Tier 2 JSON API scrapers only** (Amazon, Google, Microsoft, Apple, Uber) — Apple and Google are `False`; both moved to Playwright
- **`PLAYWRIGHT_JOBS_ENABLED` = Meta, YC, Google (careers.google.com), Apple, Uber, intern_list, google_jobs (aggregator)** (Tesla disabled 2026-04 — Cloudflare blocking)
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
- **Govt Canada** — RSS feed (page2710) removed 2026-04; scraper uses Playwright on page2440; selector is `a[href*='page1800']` (job detail links); GC Jobs uses "student" not "intern" in titles — added "student" to `KEYWORDS_INCLUDE` and `GOVT_CANADA_KEYWORDS`; uses `urllib.parse.quote` (NOT `urllib.request.quote`)
- **YC Work at a Startup** — `/jobs.json` HTTP 500 as of 2026-04; converted to authenticated Playwright DOM scraper on `workatastartup.com/internships`. No XHR API — data is server-rendered. Login flow: `account.ycombinator.com/authenticate` → `#ycid-input` (email) + `#password-input` → submit → `wait_for_load_state("load")` → navigate to `/internships` (session cookie carries over; redirect doesn't auto-follow). Two DOM layouts depending on auth state: logged-in company name is in `a[href*='/companies/'] img[alt]` (text node is empty — only the img alt has the name); logged-out uses `span.font-bold`. Location from first `<span>` in metadata div after job title, with •-bullet fallback. `wait_until="load"` + 3s delay (networkidle never resolves on SPA). `/companies?jobType=intern` URL investigated but shows all jobs at intern-hiring companies (not intern-only) — `/internships` is the correct dedicated page. Location filter bypassed via `tier="github"` (same as SimplifyJobs). Credentials optional — falls back to 15 unauthenticated jobs if `YC_EMAIL`/`YC_PASSWORD` absent. Gated by `PLAYWRIGHT_JOBS_ENABLED["yc"]`
- **`github_repos.py` supports both HTML and markdown pipe tables** — SimplifyJobs uses HTML `<table>` (switched 2026-04); `negarprh/Canadian-Tech-Internships-2026` uses markdown pipe tables. Auto-detected: if `<table` in content → `_TableParser`; else → `_parse_markdown_table()`. Uses `re` (stdlib) for markdown link extraction. No new dependencies.
- **`"github"` tier bypasses location filter** — same mechanism as `"big_tech"` tier; SimplifyJobs is a curated global list so location filtering would drop valid US/remote postings
- **SimplifyJobs company names may have emoji prefixes** — FAANG-tier companies are tagged `🔥, Cloudflare` in the HTML; `APPLIED_COMPANIES` entries must match the exact parsed string; workaround is to rely on Greenhouse/Lever/Workday scrapers for those companies instead
- **New-Grad-Positions disabled** — `SimplifyJobs/New-Grad-Positions` commented out of `GITHUB_REPOS` as of 2026-04; re-enable to include new-grad roles
- **Microsoft careers moved to Eightfold AI (2026-04)** — old `jobs.careers.microsoft.com/global/en/search` had SSL hostname mismatch and is effectively deprecated. New portal is `apply.careers.microsoft.com`, powered by Eightfold AI. The public PCSX search API (`/api/pcsx/search?domain=microsoft.com&query=...&start=N&num_jobs=100`) requires no authentication. Response shape: `data.data.positions[].{id, name, locations[], postedTs, positionUrl}`. Job URL: `https://apply.careers.microsoft.com` + `positionUrl`. Supports pagination via `start` offset.
- **Amazon schema changed 2026-04** — `data["hits"]` is now an integer count; job list is now `data["jobs"]` with flat fields (not nested under `fields`). Fixed in `big_tech.py`.
- **Amazon uses two distinct search terms (2026-04)** — `base_query=software+intern` and `base_query=software+internship` return different job sets (no stemming). `_scrape_amazon()` queries both via `_AMAZON_QUERIES`. The `loc_query` parameter is silently ignored by Amazon's API (any value including nonexistent strings returns the same count) — location loop removed; one request per query with `result_limit=100`.
- **Meta careers redesigned 2026-04** — CSS selector approach broke; `playwright_jobs.py` now intercepts the GraphQL response at `/graphql` and parses `data.job_search_with_featured_jobs.all_jobs`. Job URLs: `metacareers.com/jobs/{id}/`.
- **Google careers Playwright scraper added 2026-04** — old `careers.google.com/api/jobs/jobs-v1/search/` deprecated (301 → 404 at new path). No interceptable JSON API — job data is rendered directly into the DOM. Scraper parses `li.lLd3Je` cards at `google.com/about/careers/applications/jobs/results?employment_type=INTERN&q=software`. Title: `h3.QJPWVe`; location: `.wVoYLb` text after `place\n` marker; URL: relative href prefixed with base. Returns ~18 results (one page). CSS class names are obfuscated and may change on Google deploys — high fragility risk.
- **Apple careers Playwright scraper added 2026-04** — `jobs.apple.com/api/role/search` (old big_tech.py stub) returns 301 → `apple.com/pagenotfound`. The internal `/api/v1/search` endpoint requires a CSRF token fetched by the page's own JS — headless Playwright can't replicate that auth flow (returns `{"res": {"searchResults": [], "totalRecords": 0}}`). Job data IS rendered into the DOM. Scraper navigates `jobs.apple.com/en-ca/search?location=canada-CANC+united-states-USA&key=Software&team=internships-STDNT-INTRN` and parses `ul#search-job-list`. Each card has two `<a>` tags with the same href — title link (has `.job-posted-date` sibling) and "See full role description" (no date sibling); skip the second by checking the date sibling in `page.evaluate()`. Uses `wait_until="load"` + `wait_for_selector` because `networkidle` never resolves (persistent analytics connections). Pagination via `[aria-label="Next Page"]`. `BIG_TECH_ENABLED["apple"]` stays `False`; `PLAYWRIGHT_JOBS_ENABLED["apple"] = True`.
- **Tesla blocked 2026-04** — Cloudflare returns "Access Denied" to headless Chromium. No public API. Disabled in `PLAYWRIGHT_JOBS_ENABLED`.
- **Uber Playwright scraper added 2026-04** — `jobs.uber.com` is Cloudflare-blocked (403). `www.uber.com/ca/en/careers/list/` is an SPA accessible to headless Chromium. No public JSON API endpoint found in JS bundles (abstracted behind Redux `loadSearchJobsResults`). Playwright response interceptor captures XHR responses from `uber.com` and heuristically walks top-level and one level of nesting to find a list of objects with a `title` field. URL: `https://www.uber.com/ca/en/careers/list/?query=Intern&department=University`. Job URL: `uber.com/global/en/careers/list/{jobId}/`. Moved to `PLAYWRIGHT_JOBS_ENABLED`; `BIG_TECH_ENABLED["uber"]` stays `False`.
- **Ontario Public Service broken 2026-04** — old ontario.ca URL is 404; new portal (gojobs.gov.on.ca) uses Radware CAPTCHA. Disabled in `PUBLIC_SECTOR_ENABLED`.
- **City of Toronto URL changed 2026-04** — old `toronto.ca/city-government/...` is 404; scraper now uses `jobs.toronto.ca/jobsatcity/search/?q=intern` with `a[href*='/job/']` selector.
- **main.py per-scraper logging** — each scraper now prints `[name] N jobs returned, M new` every run for diagnostics.
- **intern-list.com added 2026-04** — DOM scraper on Jobright embed pages. The `?k=swe` landing page embeds jobright.ai iframes (not Airtable); the Canada tab also loads via `jobright.ai/minisites-jobs/intern/ca/swe?embed=true`. Navigates directly to the iframe URLs to avoid tab interactions. Table uses virtual scroll — only ~22 rows visible at a time; scrolling the nearest `overflow-y:auto` ancestor loads more. Row selector `tr[data-index]` is stable (data attribute); CSS module class names on cells are obfuscated and may change. Job URLs: `jobright.ai/jobs/info/{id}` (UTM params stripped). Returns ~900 jobs (US + Canada combined). `tier="github"` — aggregate curated board, same as SimplifyJobs; location filter bypassed.
- **Google for Jobs aggregator added 2026-04** — separate from `careers.google.com` (`PLAYWRIGHT_JOBS_ENABLED["google"]`). This scrapes the Google Search vertical at `google.com/search?q=...&ibp=htl;jobs`, which indexes `JobPosting` schema.org markup across the web. Three SWE-intern query variants looped: `software engineering intern`, `software internship`, `software developer intern`. No explicit location param — Google geo-biases off the request IP; adding `&location=` narrows unpredictably. **Selectors are semantic only** (`role=list` / `role=listitem` / `[role="heading"][aria-level="3"]`) because Google's CSS classnames are obfuscated and change on deploys. Cards carry title + company + location in their inner text; clicking a card renders the right-hand detail pane containing "Apply on {source}" links. Apply-URL priority: (1) hostname matches company name → (2) non-aggregator host → (3) first link. Aggregator hosts demoted: `linkedin.com`, `indeed.com`, `glassdoor.com`, `ziprecruiter.com`, `simplyhired.com`. **Cookie-consent handling**: fresh Playwright contexts have no `CONSENT` cookie, so Google serves the "Before you continue to Google Search" interstitial on first load. `_dismiss_consent_if_needed()` clicks "Reject all" (privacy-friendly; falls back to "Accept all" / "I agree" / aria-label variants) and waits for navigation. Only bails when: `/sorry/` challenge URL, recaptcha iframe, "unusual traffic" body text, OR consent page shown but no dismiss button could be clicked. Fragility tripwire: if >30% of harvested cards have empty company, selectors drifted → WARN + return []. `tier="github"` bypasses `LOCATIONS_INCLUDE` (aggregator like SimplifyJobs). **4-hour `SCRAPER_INTERVALS` entry** — longer than other Playwright scrapers to minimize Google bot-detection exposure of the residential IP. Expected heavy overlap with existing ATS scrapers; same MD5 dedup key includes source+company+title+url, so the same posting can trigger two emails via different URLs (e.g., company career page + Google Jobs apply link) — acceptable cost. If recaptcha ever fires repeatedly, flip to `False` and rely on existing scrapers.

---

## Open Source Notes

- Comment every non-obvious config option with what it does and how to find the value
- README must work for someone who has never used Python
- Message templates in `networking/config.py` written generically with personalization instructions
