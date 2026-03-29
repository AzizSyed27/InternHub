# Product Requirements Document
## InternHub — Internship Tracker & LinkedIn Networking Pipeline

**Author:** Aziz Syed
**Version:** 2.0
**Status:** Planning
**Last Updated:** March 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Goals & Success Metrics](#3-goals--success-metrics)
4. [Target Users](#4-target-users)
5. [Tool 1 — Internship Tracker](#5-tool-1--internship-tracker)
6. [Tool 2 — LinkedIn Networking Pipeline](#6-tool-2--linkedin-networking-pipeline)
7. [Technical Architecture](#7-technical-architecture)
8. [Data Model](#8-data-model)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Out of Scope](#10-out-of-scope)
11. [Future Roadmap](#11-future-roadmap)
12. [Open Questions](#12-open-questions)

---

## 1. Overview

InternHub is a two-tool automation suite that runs locally on a Mac mini, targeting software engineering students pursuing internships at top technology companies. It eliminates two of the biggest friction points in the internship search: **discovering new job postings the moment they go live**, and **finding the right people to network with** based on a shared non-traditional academic path.

- **Tool 1 — Internship Tracker:** A multi-source job aggregator that monitors 4 tiers of job sources on a self-regulating schedule, deduplicates postings, filters by role and location, and sends one individual email per new posting found.
- **Tool 2 — LinkedIn Networking Pipeline:** A browser automation tool that searches LinkedIn alumni pages to find professionals who went college → university → big tech, and exports a CSV with their profile details and AI-generated personalized outreach message drafts.

Both tools run independently on the same Mac mini. Tool 1 runs continuously via launchd. Tool 2 runs on-demand from the Terminal.

---

## 2. Problem Statement

**Challenge 1 — Speed of application**
Top internship postings at companies like Google, Amazon, and Shopify routinely close within 24–72 hours of going live. Students who check job boards manually — even daily — frequently miss the window. There is no centralized alert system that monitors multiple sources simultaneously and notifies applicants in real time.

**Challenge 2 — Lack of accessible mentorship**
Students from non-traditional academic paths (college diploma programs, transfer students, smaller universities) lack access to the alumni networks and career services that students at Waterloo or UofT take for granted. Identifying professionals who took a similar path and are now at target companies requires hours of manual LinkedIn searching with no guarantee of finding the right people.

---

## 3. Goals & Success Metrics

### Primary Goals
- Receive email notifications for new relevant internship postings within 5–10 minutes of going live
- Build a qualified list of 100+ LinkedIn contacts matching the target profile
- Reduce time spent on job board monitoring to zero
- Reduce time spent on LinkedIn prospecting from hours to minutes per session

### Success Metrics

| Metric | Target |
|---|---|
| New posting notification latency | ≤ 10 minutes |
| False positive rate (irrelevant postings) | < 10% |
| Duplicate posting rate | 0% |
| LinkedIn profiles logged per run | 20–50 |
| Profile match accuracy | > 85% |
| Outreach draft quality (usable without major edits) | > 90% |

---

## 4. Target Users

### Primary User
A CS student at Ontario Tech University (incoming), graduating from Centennial College with an Advanced Diploma in Software Engineering Technology. Targeting SWE internships at big tech companies in the GTA and remotely. Comfortable with Python and Terminal.

### Secondary Users — Open Source Community
Any CS/SE student pursuing tech internships. All user-specific configuration is centralized in `config.py` and `.env` to make the tool easy to adapt.

---

## 5. Tool 1 — Internship Tracker

### 5.1 Description

A Python script that fires every 5 minutes via launchd. Each scraper self-regulates via its own configured interval — lightweight API scrapers run every 5 minutes, Playwright scrapers run every 30 minutes to 6 hours. When new postings are found, one email is sent per posting immediately.

### 5.2 Job Sources — Four Tiers

**Tier 1 — ATS JSON APIs (no Playwright, stdlib only)**

| Source | API Endpoint | Scraper |
|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | `greenhouse.py` |
| Lever | `api.lever.co/v0/postings/{slug}?mode=json&limit=250` | `lever.py` |

**Tier 2 — Big Tech Career Page APIs (no Playwright, stdlib only)**

Each company exposes an internal JSON API used by their own frontend. The scraper loops over `BIG_TECH_LOCATIONS` and makes one request per location, then merges and deduplicates.

| Company | Endpoint |
|---|---|
| Amazon | `https://www.amazon.jobs/en/search.json?base_query=software+intern&loc_query={location}` |
| Google | `https://careers.google.com/api/jobs/jobs-v1/search/?q=software+intern&location={location}` |
| Microsoft | `https://jobs.careers.microsoft.com/global/en/search?q=intern&lc={location}&l=en_us&pg=1&pgSz=20` |
| Apple | `https://jobs.apple.com/api/role/search` — POST body with location filter per location |
| Uber | `jobs.uber.com` — validate exact endpoint via DevTools during build |

**Tier 3 — Workday ATS JSON API (no Playwright, stdlib only)**

```
POST https://{company}.wd5.myworkdayjobs.com/wday/cxs/{company}/{site}/jobs
Body: {"searchText": "software intern", "limit": 20, "offset": 0}
```

One scraper handles all Workday companies via different slugs.

**Tier 4 — Playwright Scrapers (optional dependency)**

| Source | URL | Scraper |
|---|---|---|
| Meta | metacareers.com | `playwright_jobs.py` |
| Tesla | tesla.com/careers | `playwright_jobs.py` |
| Ontario Public Service | ontario.ca/careers | `ontario_public.py` |
| OPG | opg.com/careers | `opg.py` |
| City of Toronto | toronto.ca/jobs | `city_toronto.py` |
| Govt Canada | jobs.gc.ca | `govt_canada.py` |

All Tier 4 scrapers must fail gracefully — never crash the full run.

**Community Sources (stdlib only)**

| Source | Method | Scraper |
|---|---|---|
| SimplifyJobs GitHub repos | GitHub raw API, parse markdown tables | `github_repos.py` |
| Hacker News Who's Hiring | Algolia HN API | `hackernews.py` |
| YC Work at a Startup | `workatastartup.com/jobs.json` | `yc.py` |

### 5.3 Target Companies

**Core Big Tech:** Google, Meta, Apple, Amazon, Microsoft, Netflix, Nvidia, Uber, Airbnb, Salesforce, Adobe, PayPal, LinkedIn, Spotify

**AI / High-Growth:** OpenAI, Anthropic, Cohere, Databricks, Snowflake, Scale AI, Stripe, Figma, Notion, Cloudflare, Datadog, Palantir

**Canadian Big Tech:** Shopify, Wealthsimple, Thomson Reuters, Lightspeed, Ada, Faire, D2L, ApplyBoard

**Gaming / Other:** Ubisoft Montreal, EA, Riot Games, Epic Games

### 5.4 Target Public Sector Organizations

**Federal:** Government of Canada (FSWEP), NRC, Statistics Canada, CRA, Bank of Canada

**Ontario Provincial:** OPS, OPG, Hydro One, Metrolinx, Ontario Health

**Municipal:** City of Toronto, TTC, York Region, Peel Region

### 5.5 Filtering Logic

**INCLUDE keywords (must match at least one — title + description):**
`intern, internship, co-op, coop, co op, new grad, entry level, junior, software engineer, software developer, swe, full stack, fullstack, backend, front end, frontend, mobile, ios, android, data engineer, ml engineer`

**EXCLUDE keywords (drop if matched):**
`senior, staff, principal, lead, manager, director, vp , vice president, qa , quality assurance, test engineer, product manager, pm , project manager, sales, marketing, recruiter, hr , finance, accounting, legal`

**Standard location filter (used by Tier 1, community, and public sector scrapers):**
`canada, toronto, ontario, gta, scarborough, vancouver, montreal, ottawa, waterloo, remote`

**Big tech location filter (used by Tier 2 + Tier 3 ONLY — bypasses standard filter):**
`canada, united states, usa, us, remote`

> Tier 2 and Tier 3 scrapers bypass `LOCATIONS_INCLUDE`. Location is handled by API query params using `BIG_TECH_LOCATIONS`. Only keyword and applied-company filters apply to their results.

### 5.6 Deduplication

- ID: `md5(source_prefix + company + title + url)`
- `seen_jobs.json` stores seen IDs + last run timestamp per scraper
- Only unseen jobs trigger an email

```json
{
  "seen_ids": ["abc123", "def456"],
  "last_run": {
    "github_repos": "2026-03-23T14:00:00",
    "greenhouse":   "2026-03-23T14:00:00"
  }
}
```

### 5.7 Email — Per-Posting

- One email sent per new job posting — not a digest
- Subject: `🚀 [Company] — [Job Title] ([Location])`
- HTML dark-mode card: company, role, source badge, location, date, 300-char description, Apply Now button
- Gmail SMTP + App Password — no OAuth
- Zero emails sent if no new postings

### 5.8 Scheduling

launchd fires `main.py` every 5 minutes. Each scraper self-regulates:

```python
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
```

---

## 6. Tool 2 — LinkedIn Networking Pipeline

### 6.1 Description

A Python + Playwright tool that logs into LinkedIn, navigates alumni pages, finds professionals matching the target profile, and exports a CSV with profile data and AI-generated outreach drafts. Does not send any messages — all outreach is manual.

### 6.2 Target Schools

**Colleges:** Centennial, Sheridan, Humber, George Brown, Seneca, Durham, Mohawk, Fanshawe

**Universities:** Ontario Tech, UofT, Waterloo, McMaster, Western, Queens, Toronto Metropolitan, York, Ottawa, Carleton

### 6.3 Profile Match Criteria

Must have ALL THREE:
1. College diploma from any Ontario college
2. University degree from any Canadian university
3. Current technical role at one of the 35 target companies

### 6.4 Data Extracted Per Profile

`name`, `linkedin_url`, `current_company`, `current_role`, `college`, `university`, `graduation_years`, `connection_degree`

### 6.5 Message Templates

**Connection request note (≤300 chars strict limit):**
> Hi [Name] — I'm a CS student at Ontario Tech, graduated Centennial. I noticed you took a similar path and landed at [Company]. I'd love to hear your story — would you be open to connecting?

**Follow-up message (sent manually after acceptance):**
> Hi [Name], my name is Aziz Syed. I'm completing my CS degree at Ontario Tech after graduating from Centennial College. I noticed you went from [College] to [University] and are now a [Role] at [Company] — almost exactly the path I'm hoping to take. After my second year at Centennial, I realized I didn't want to work just anywhere — I want to be at [Company] because of [company-specific value]. Given you've been in my position, what steps would you advise me to take to make that a reality? Even one piece of advice would mean a lot.

Company-specific values drawn from `company_values.json` — never hallucinate.

### 6.6 CSV Output

Filename: `networking_results_YYYY-MM-DD.csv`

Columns: `name`, `linkedin_url`, `current_company`, `current_role`, `college`, `university`, `connection_degree`, `connection_note_draft`, `followup_message_draft`, `contacted`, `replied`, `notes`

Last 3 columns left blank for user to fill in manually.

### 6.7 Rate Limiting

- Max 50 profile visits per run
- 3–7 second random delay between page loads
- 8–15 second random delay between profile visits
- On-demand only — never scheduled
- No automated messages or connection requests ever

---

## 7. Technical Architecture

### 7.1 Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Browser automation | Playwright |
| HTTP requests | `urllib` (stdlib) |
| AI message generation | Anthropic API |
| Email | Gmail SMTP (stdlib) |
| Persistence | JSON + CSV |
| Scheduling | launchd (macOS) |
| Secrets | `.env` via `python-dotenv` |

### 7.2 Project Structure

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

## 8. Data Model

### 8.1 Job Posting

```python
{
  "id":          str,   # md5(source_prefix + company + title + url)
  "title":       str,
  "company":     str,
  "location":    str,
  "url":         str,
  "date_posted": str,   # YYYY-MM-DD
  "description": str,   # first 500 chars
  "source":      str,   # "GitHub" | "Greenhouse" | "Lever" | "BigTech" | "Workday" | "HackerNews" | "YC" | "Meta" | "Tesla" | "GovtCanada" | "OPS" | "OPG" | "CityToronto"
}
```

### 8.2 LinkedIn Profile

```python
{
  "name":                   str,
  "linkedin_url":           str,
  "current_company":        str,
  "current_role":           str,
  "college":                str,
  "university":             str,
  "connection_degree":      str,
  "connection_note_draft":  str,
  "followup_message_draft": str,
  "contacted":              bool,
  "replied":                bool,
  "notes":                  str,
}
```

---

## 9. Non-Functional Requirements

**Performance**
- Full run across all sources completes in under 5 minutes
- Playwright scrapers each complete in under 60 seconds

**Reliability**
- Each scraper is independently wrapped in try/except — one failure never crashes the run

**Privacy & Security**
- All credentials in `.env`, excluded from git
- No credentials logged to stdout

**Portability**
- Tier 1–3 scrapers: zero third-party dependencies (stdlib only)
- Playwright is optional — if not installed, Tier 4 scrapers skip gracefully with a warning
- Both tools work on macOS, Linux, Windows (minor scheduler differences)

**Maintainability**
- All user config in `config.py` per tool
- Adding a new Greenhouse/Lever/Workday company = one line in config
- Adding a new scraper = one new file in `scrapers/`

---

## 10. Out of Scope

- Automated LinkedIn messaging or connection requests
- LinkedIn Premium / InMail
- Web UI or dashboard
- Database backend
- Multi-user support
- Mobile push notifications
- Resume tracking or ATS integration
- Automatic job application submission

---

## 11. Future Roadmap

| Version | Feature |
|---|---|
| v1.1 | Ashby ATS scraper (growing ATS used by AI startups) |
| v1.1 | Additional public sector scrapers (Metrolinx, Hydro One, TTC) |
| v1.2 | Simple Flask dashboard to browse postings and mark applied |
| v1.2 | Slack or iMessage notification option |
| v1.3 | LinkedIn scraper flags 2nd-degree connections and mutual contacts |
| v2.0 | Application status tracker (applied, phone screen, rejected, offer) |
| v2.0 | Weekly digest report with source breakdown and response rate |

---

## 12. Open Questions

| # | Question | Status |
|---|---|---|
| 1 | Does jobs.gc.ca expose a stable REST or RSS API or require Playwright? | Validate via DevTools during build |
| 2 | What is Uber's exact internal JSON API endpoint? | Validate via DevTools during build |
| 3 | What is Apple's exact POST body structure for location filtering? | Validate via DevTools during build |
| 4 | Will Playwright reliably handle LinkedIn's current SPA structure? | Validate during build |

---

*InternHub is an open source project. Contributions welcome.*