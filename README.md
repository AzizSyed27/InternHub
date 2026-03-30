# InternHub

A two-tool Python automation suite for software engineering students pursuing internships.

- **Tool 1 — Internship Tracker:** Monitors 30+ job sources across 4 tiers every 5 minutes, deduplicates postings, and sends one email per new posting found.
- **Tool 2 — LinkedIn Networking Pipeline:** Finds professionals who went college → university → big tech and exports a CSV with AI-generated outreach drafts.

Both tools run independently on a Mac mini (or any macOS/Linux machine). Tool 1 runs continuously via launchd. Tool 2 runs on-demand from the Terminal.

---

## Requirements

- macOS (for launchd scheduling) or Linux/Windows for manual use
- Python 3.11 or newer
- A Gmail account with [App Password enabled](https://myaccount.google.com/apppasswords) (Tool 1)
- An [Anthropic API key](https://console.anthropic.com/) (Tool 2, optional)
- LinkedIn account (Tool 2)

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/internhub.git
cd internhub
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your values:

```
EMAIL_SENDER=your.gmail@gmail.com
EMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password, not your account password
EMAIL_RECIPIENT=your.email@gmail.com

LINKEDIN_EMAIL=your.linkedin@email.com
LINKEDIN_PASSWORD=your_linkedin_password
ANTHROPIC_API_KEY=sk-ant-...             # optional, for AI message drafts
```

**How to create a Gmail App Password:**
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and your device
3. Copy the 16-character password into `EMAIL_APP_PASSWORD`

### 3. Install dependencies

**Tool 1 (Tracker):**

```bash
cd tracker
pip install -r requirements.txt
playwright install chromium    # only needed for Tier 4 scrapers (Meta, Tesla, public sector)
```

**Tool 2 (Networking):**

```bash
cd networking
pip install -r requirements.txt
playwright install chromium
```

---

## Tool 1 — Internship Tracker

### What it monitors

| Tier | Sources | Method |
|------|---------|--------|
| 1 | Greenhouse ATS (18 companies) | JSON API |
| 1 | Lever ATS (10 companies) | JSON API |
| 2 | Amazon, Google, Microsoft, Apple, Uber | Internal career page APIs |
| 3 | Netflix, Nvidia (Workday) | Workday POST API |
| 4 | Meta, Tesla, OPS, OPG, City of Toronto, Govt Canada | Playwright |
| Community | SimplifyJobs GitHub, Hacker News Who's Hiring, YC | Various |

### First run (important!)

On the very first run, the tracker does a **seed pass** — it indexes all currently-live postings without sending emails. This prevents a flood of notifications when you first set it up.

Run it manually to verify it works:

```bash
cd internhub
python tracker/main.py
# Output: "First run detected — seeding database (no emails will be sent)."
# Output: "Seed complete. N postings indexed. Run again to start receiving emails."

python tracker/main.py   # second run — now you'll get emails for new postings
```

### Set up continuous monitoring (Mac mini)

1. Open `tracker/launchd.plist` and replace the placeholder values:
   - `YOUR_PYTHON_PATH` → output of `which python3` (e.g. `/usr/local/bin/python3`)
   - `YOUR_REPO_PATH` → absolute path to this repo (e.g. `/Users/yourname/internhub`)

2. Copy the plist to launchd's agents directory:

```bash
cp tracker/launchd.plist ~/Library/LaunchAgents/com.internhub.tracker.plist
```

3. Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.internhub.tracker.plist
```

4. Verify it's running:

```bash
launchctl list | grep internhub
```

5. To stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.internhub.tracker.plist
```

Logs are written to `tracker/tracker.log` and `tracker/tracker_error.log`.

### Customizing for your job search

All configuration lives in `tracker/config.py`:

- **Add companies:** add a line to `GREENHOUSE_COMPANIES`, `LEVER_COMPANIES`, or `WORKDAY_COMPANIES`
- **Change locations:** update `LOCATIONS_INCLUDE`
- **Change role keywords:** update `KEYWORDS_INCLUDE` / `KEYWORDS_EXCLUDE`
- **Mark as applied:** add company names to `APPLIED_COMPANIES` to stop seeing their postings
- **Disable a scraper:** set it to `False` in `BIG_TECH_ENABLED`, `PLAYWRIGHT_JOBS_ENABLED`, or `PUBLIC_SECTOR_ENABLED`

---

## Tool 2 — LinkedIn Networking Pipeline

### What it does

1. Logs into LinkedIn using your credentials
2. Searches alumni pages for each target school × target company combination
3. Visits matching profiles (up to 50 per run)
4. Generates personalized connection note + follow-up message drafts
5. Exports a CSV file for manual outreach

### Profile match criteria

The tool only exports profiles where the person has **all three**:
1. A diploma from an Ontario college
2. A degree from a Canadian university
3. A current technical role at one of the 35 target companies

### AI message drafts (optional)

To enable AI-personalized outreach drafts:
1. Add your `ANTHROPIC_API_KEY` to `.env`
2. Set `ANTHROPIC_MODEL` in `networking/config.py` (e.g. `"claude-haiku-4-5-20251001"`)

If `ANTHROPIC_MODEL` is empty, the tool still runs and fills in template-based drafts.

### Run it

```bash
cd internhub
python networking/main.py
```

The tool prints progress as it visits profiles, then writes a CSV to the current directory:

```
networking_results_2026-03-30.csv
```

### Outreach workflow

1. Open the CSV in Excel or Google Sheets
2. Review and edit the `connection_note_draft` column (300 char limit on LinkedIn)
3. Send connection requests manually on LinkedIn
4. After acceptance, send the `followup_message_draft` manually
5. Update `contacted`, `replied`, and `notes` columns as you go

**This tool never sends any messages automatically.**

### Rate limits

- Max 50 profile visits per run
- 3–7 second delay between page loads
- 8–15 second delay between profile visits

These are intentional — be respectful of LinkedIn's systems.

---

## Customizing for your own use

InternHub is designed to be easy to adapt:

1. **Change the target schools:** edit `COLLEGES` and `UNIVERSITIES` in `networking/config.py`
2. **Change the target companies:** edit `TARGET_COMPANIES` in `networking/config.py`
3. **Change the message templates:** edit `CONNECTION_NOTE_TEMPLATE` and `FOLLOWUP_TEMPLATE` in `networking/config.py`
4. **Add company values:** edit `networking/company_values.json`
5. **Change the outreach persona:** update the templates to use your name and school

---

## Project structure

```
internhub/
├── tracker/                  # Tool 1
│   ├── main.py               # Orchestrator (run by launchd)
│   ├── config.py             # All tracker configuration
│   ├── filters.py            # Keyword + location filtering
│   ├── db.py                 # seen_jobs.json persistence
│   ├── emailer.py            # Gmail SMTP
│   ├── launchd.plist         # macOS scheduling config
│   └── scrapers/             # One file per scraper
├── networking/               # Tool 2
│   ├── main.py               # Entry point (run manually)
│   ├── config.py             # Schools, companies, rate limits
│   ├── linkedin_scraper.py   # Playwright login + navigation
│   ├── profile_parser.py     # Extract data from profile pages
│   ├── message_generator.py  # Anthropic API drafts
│   ├── csv_exporter.py       # CSV output
│   └── company_values.json   # Values per target company
├── .env.example              # Credential template
└── README.md
```

---

## Contributing

Pull requests are welcome. Please keep all user-specific configuration in `config.py` and `.env` — no personal details in logic files.

Issues: [github.com/YOUR_USERNAME/internhub/issues](https://github.com/azizsyed27/internhub/issues)
