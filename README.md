# PK-Hub — Pakistan Procurement Intelligence & Active Tender Harvester

> **An automated discovery, live monitoring, and structured extraction engine for Pakistan's federal Public Procurement Regulatory Authority (PPRA) e-Procurement System ([EPMS](https://epms.ppra.gov.pk/public/tenders/active-tenders)).**

---

## 1. Overview & End-to-End Capabilities

**PK-Hub** is a procurement intelligence platform for businesses, contractors, and market analysts tracking public sector opportunities across Pakistan. Rather than manually paging through the PPRA portal, PK-Hub automates the whole run:

- **Every filter on the PPRA search form**: all 1,200+ organizations, all 29 sectors, category, tender type, method, nature, status, country, city, advertise and closing dates, keyword and tender number. The dropdown lists are read from the live site and kept up to date automatically (see [§7](#7-how-the-filters-work)).
- **Configurable closing-date guard**: skips tenders closing within N days (default 7, set per run, or turned off), so you don't chase tenders you can't bid on in time.
- **Live scraper console**: **Start**, **Pause**, **Resume**, **Stop** and **Refresh** for each run; runs keep going while you move between Console, History and Downloads.
- **Live preview**: screenshots from the headless browser, streamed into the console.
- **Live results table**: tenders appear page by page as they are saved.
- **Excel workbooks**: real date cells, closing time in Pakistan time (PKT), a live `Days Left` formula (`=MAX(0, J{row}-TODAY())`), clickable links, and a **Run Summary** sheet. Files are named after your filters, e.g. `PPRA_Tenders(13-10-2026 to 15-10-2026, Goods).xlsx` (see [§8](#8-excel-output)).
- **Stopped runs keep their rows**: stopping a run part-way still gives you a downloadable workbook of everything found so far.
- **History**: run state and every scraped tender persist in PostgreSQL, so past runs can be reopened or downloaded at any time.

> [!NOTE]
> **Pakistan Procurement Only**: This platform is tailored for Pakistani procurement (PPRA Pakistan / EPMS). All foreign or legacy US portal integrations (BidNet, MyFloridaMarketPlace, RideMetro, Texas SmartBuy, etc.) have been removed.

---

## 2. Technology Stack

### Frontend (`client/`)
- **Framework**: [Next.js 16](https://nextjs.org/) (App Router & Turbopack)
- **Language**: TypeScript 5 (Strict Mode)
- **Styling**: Tailwind CSS v4 (`@tailwindcss/postcss`) with custom editorial tokens (`paper`, `ink-900`, `gold-500`) defined in `globals.css`
- **Typography**: Newsreader (editorial serif headings) + Inter (interface body)
- **State**: a `useSyncExternalStore` session store, so a running scrape survives route changes and page reloads

### Backend (`server/`)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
- **ORM & Database**: [SQLAlchemy 2](https://www.sqlalchemy.org/) + [PostgreSQL 15+](https://www.postgresql.org/) with `psycopg2`
- **Scraping**: Selenium 4 headless Chrome (driver installed by `webdriver-manager`) with anti-detection settings
- **HTML Parsing**: BeautifulSoup4 (built-in `html.parser`)
- **Concurrency**: `ThreadPoolExecutor` worker pool; runs beyond the cap wait in a queue
- **Spreadsheets**: `openpyxl`

---

## 3. System Architecture

```mermaid
flowchart TD
    subgraph Target["Target Authority"]
        PPRA["epms.ppra.gov.pk<br/>(Active Tenders EPMS)"]
    end

    subgraph Server["FastAPI Backend (Port 8000)"]
        API["FastAPI routers<br/>(ppra/router.py, core/download_router.py)"]
        ScrapeWorker["PPRA scraper<br/>(BaseScraper + headless Chrome)"]
        LiveBus["Live screenshot registry<br/>(live.py)"]
        RunManager["Run manager<br/>(run_manager.py)"]
        ExcelEngine["Excel export<br/>(ppra/export.py)"]
    end

    subgraph Storage["Persistent Storage"]
        PG[("PostgreSQL<br/>ppra_runs · ppra_bids · ppra_filter_options · run_state")]
        DataDir[("Local data<br/>data/archives/&lt;run_id&gt;/*.xlsx<br/>data/ppra/&lt;run_id&gt;/tenders.jsonl")]
    end

    subgraph Client["Next.js 16 Client (Port 3000)"]
        UI["Console<br/>(PpraPanel / PpraResults)"]
        Engine["Session engine<br/>(SessionEngine / sessions.ts)"]
        LiveMonitor["Live preview modal"]
    end

    UI -->|"1. GET /ppra/filters (dropdown lists)"| API
    UI -->|"2. POST /ppra/scrape (filter ids)"| API
    API -->|"3. Queue on worker pool"| ScrapeWorker
    ScrapeWorker -->|"4. Open search URL, page through results"| PPRA
    ScrapeWorker -->|"5. Upsert tenders, refresh dropdown lists"| PG
    ScrapeWorker -->|"6. Save workbook"| ExcelEngine
    ExcelEngine --> DataDir
    LiveMonitor -->|"7. GET /runs/{id}/screenshot"| LiveBus
    Engine -->|"8. Poll /runs, status, logs"| API
    UI -->|"9. Poll /ppra/bids"| API
    RunManager --- API
```

### End-to-End Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Procurement Officer
    participant Console as Next.js Console (Port 3000)
    participant API as FastAPI Server (Port 8000)
    participant Worker as Scraper (thread pool)
    participant DB as PostgreSQL
    participant EPMS as PPRA EPMS Portal

    Console->>API: GET /ppra/filters
    API-->>Console: Dropdown lists (site ids + labels)
    User->>Console: Choose filters & click "Start PPRA Scrape"
    Console->>API: POST /ppra/scrape { filters: { sector: "14", … }, options }
    API->>DB: INSERT ppra_runs (status 'running')
    API-->>Console: 200 { run_id: "18ec1404149c" }

    activate Worker
    API->>Worker: Queue the run (waits if all slots are busy)
    Worker->>EPMS: GET active-tenders?sector=14&… (page 1)
    Worker->>DB: Refresh ppra_filter_options from the page's dropdowns

    loop Each results page
        Worker->>Worker: Parse rows, apply closing-date guard
        Worker->>DB: Upsert into ppra_bids
        Worker->>EPMS: GET next page
    end

    loop Every 2–3 seconds
        Console->>API: GET /ppra/scrape/status/{id} · /runs/{id}/logs · /ppra/bids?after_id=…
        API-->>Console: Status, log lines, new tenders
    end

    Worker->>DB: UPDATE ppra_runs SET status 'completed', finished_at
    Worker->>Worker: Build the Excel workbook into data/archives/{run_id}/
    deactivate Worker

    Console->>User: "Completed" badge & Download Excel button
```

---

## 4. Repository Layout

```
pk-hub/
├── client/                          # Next.js 16 frontend
│   ├── src/
│   │   ├── app/                     # Routes: landing page, /console/[portal], history, exports
│   │   │   ├── console/layout.tsx   # Console shell; keeps the panel and session engine alive
│   │   │   ├── layout.tsx           # Fonts (Newsreader + Inter)
│   │   │   ├── globals.css          # Theme tokens and animations
│   │   │   └── page.tsx             # Landing page
│   │   ├── components/
│   │   │   ├── PpraPanel.tsx        # Filter form & run controls
│   │   │   ├── PpraResults.tsx      # Live tenders table
│   │   │   ├── RunStatus.tsx        # Status card, closing-guard note, download
│   │   │   ├── RunHistory.tsx       # History tab
│   │   │   ├── ExportsPanel.tsx     # Downloads tab
│   │   │   ├── ActiveJobs.tsx       # Footer bar listing running jobs
│   │   │   ├── LiveMonitor.tsx      # Live preview modal
│   │   │   ├── SessionEngine.tsx    # The one poller for runs, status and logs
│   │   │   └── ui.tsx               # Buttons, fields, dropdowns, searchable picker, tables, badges
│   │   └── lib/
│   │       ├── api.ts               # Typed API client
│   │       ├── sessions.ts          # Session store (survives navigation and reload)
│   │       ├── usePortalSession.ts  # A panel's view of its session
│   │       ├── runs.ts              # Run formatting helpers
│   │       └── portals.ts           # Portal registry (PPRA)
│   ├── .env.example                 # Client environment template
│   └── package.json
│
├── server/                          # FastAPI backend
│   ├── app/
│   │   ├── config.py                # Settings from server/.env (see §6)
│   │   ├── db.py                    # Database engine, session, table creation
│   │   ├── main.py                  # FastAPI app, CORS, routers
│   │   ├── core/
│   │   │   ├── base_scraper.py      # Chrome setup, navigation retries, pause/stop
│   │   │   ├── run_manager.py       # Run state, mirrored to the run_state table
│   │   │   ├── jobs.py              # Worker pool and queue
│   │   │   ├── download_router.py   # /runs endpoints: list, logs, screenshot, stop, pause, resume, download
│   │   │   ├── exports.py           # Excel filename, download, archive
│   │   │   ├── excel_style.py       # Shared workbook styling
│   │   │   ├── closing_filter.py    # Closing-date parsing and the N-day rule
│   │   │   ├── live.py              # Live screenshot registry
│   │   │   ├── run_logs.py          # Per-run log tail
│   │   │   ├── filenames.py         # Filename sanitising
│   │   │   └── models.py            # run_state table
│   │   ├── scrapers/ppra/
│   │   │   ├── router.py            # /ppra endpoints
│   │   │   ├── scraper.py           # Page loop and the worker task
│   │   │   ├── parsers.py           # Results table, totals and dropdown parsing
│   │   │   ├── filters.py           # Dropdown cache, name↔id lookup, search URL
│   │   │   ├── filter_options.json  # Built-in copy of the site's dropdown lists
│   │   │   ├── export.py            # Two-sheet Excel workbook
│   │   │   ├── repository.py        # Database writes and the JSONL mirror
│   │   │   ├── models.py            # ppra_runs, ppra_bids, ppra_filter_options
│   │   │   └── schemas.py           # Request models
│   │   └── services/notifier.py     # Optional completion email (AWS SES)
│   ├── tests/                       # pytest suite (needs the database)
│   ├── main.py                      # Root uvicorn entrypoint (main:app)
│   ├── .env.example                 # Server environment template
│   └── requirements.txt             # Python dependencies
│
├── .github/workflows/aislop.yml     # CI: aislop code-quality gate
├── data/                            # Workbooks and JSONL mirror (gitignored)
├── run-client.bat                   # One-click client start (Windows)
└── run-server.bat                   # One-click server start (Windows)
```

---

## 5. One-Time Setup Guide

### Step 1: Prerequisites
- **Node.js**: v20.9 or newer (required by Next.js 16)
- **Python**: v3.12 or newer
- **PostgreSQL**: v15 or newer (on port `5432`)
- **Google Chrome** (the matching ChromeDriver is downloaded automatically)

---

### Step 2: Create the Database

```powershell
createdb -U postgres -p 5432 pk-hub
```

*(Enter your PostgreSQL superuser password if prompted.)* The tables are created automatically the first time the server starts.

---

### Step 3: Backend Setup (`server/`)

1. Open PowerShell in the `server` folder:
   ```powershell
   cd C:\Users\Aliha\Downloads\pk-hub\server
   ```

2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. Install the Python packages:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Create your `.env` file and set your PostgreSQL password:
   ```powershell
   cp .env.example .env
   ```
   ```ini
   DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/pk-hub
   DATA_DIR=../data
   ```
   Every other setting is optional — see [§6](#6-configuration).

5. Check that the server starts:
   ```powershell
   uvicorn main:app --reload --port 8000
   ```
   You should see:
   ```
   INFO: Database tables ready
   INFO: Uvicorn running on http://127.0.0.1:8000
   ```
   *(Press `Ctrl + C` to stop.)*

6. Optional: run the tests:
   ```powershell
   pytest
   ```

---

### Step 4: Frontend Setup (`client/`)

1. In a second terminal, open the `client` folder:
   ```powershell
   cd C:\Users\Aliha\Downloads\pk-hub\client
   ```

2. Install the Node packages:
   ```powershell
   npm install
   ```

3. Create the frontend `.env` file:
   ```powershell
   cp .env.example .env.local
   ```
   ```ini
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Check that the production build compiles:
   ```powershell
   npm run build
   ```

---

## 6. Configuration

All server settings are read from `server/.env` (names are case-insensitive). Only `DATABASE_URL` is required.

| Variable | Default | What it does |
|---|---|---|
| `DATABASE_URL` | placeholder | PostgreSQL connection, e.g. `postgresql+psycopg2://postgres:PASSWORD@localhost:5432/pk-hub` |
| `DATA_DIR` | `../data` | Where workbooks (`archives/<run_id>/`) and the JSONL mirror (`ppra/<run_id>/`) are written; relative to `server/` |
| `SCRAPE_CONCURRENCY` | `3` | How many scrapes run at once; more wait in a queue (each Chrome uses ~300–500 MB) |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Base of the download link in completion emails |
| `PPRA_DELAY_MIN_MS` / `PPRA_DELAY_MAX_MS` | `1000` / `2500` | Random pause between result pages, to be polite to the portal |
| `PPRA_LOCAL_MIRROR` | `true` | Also append every saved tender to `data/ppra/<run_id>/tenders.jsonl` |
| `PPRA_BASE_URL` / `PPRA_ACTIVE_TENDERS_PATH` | the EPMS site | Where the scraper points |
| `DNS_OVER_HTTPS` / `DNS_OVER_HTTPS_TEMPLATES` | `true` / Google + Cloudflare | Chrome resolves names over DNS-over-HTTPS, which avoids ISP resolver failures |
| `RECIPIENT_EMAILS` | empty | Comma-separated addresses to email each finished workbook to. Nothing is sent unless this and the three SES settings below are set |
| `AWS_REGION`, `AWS_SES_FROM_EMAIL`, `AWS_SES_USERNAME`, `AWS_SES_PASSWORD` | empty | AWS SES SMTP credentials for those emails |

The client reads one setting from `client/.env.local`: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

---

## 7. How the Filters Work

The PPRA search form's dropdowns (tender type, method, category, sector, nature, organization, country, status) only accept the **site's own numeric ids**. A name is either ignored (organization) or matches nothing (sector), so PK-Hub always sends ids:

- The server reads every dropdown from the PPRA page and caches it in the `ppra_filter_options` table. This happens on **every scrape** (the scraper is on that page anyway), and on demand from the **Refresh lists** button or `POST /ppra/filters/refresh`.
- Until the first refresh, the built-in copy in `server/app/scrapers/ppra/filter_options.json` is served, so the dropdowns are never empty.
- The console shows the lists by name. Organization (1,200+) and Country are searchable: click, type or use the arrow to open them.
- Filenames and the Excel summary turn ids back into names. Runs saved before ids were used (with names) are converted automatically.

---

## 8. Excel Output

Each run produces one workbook, downloaded from the console, the Downloads tab, or `GET /runs/{run_id}/download`. It is rebuilt from the database on every download, and a copy is kept in `data/archives/<run_id>/`.

**Filename**: the advertise date range, then every other filter applied, by name:

| Filters | Filename |
|---|---|
| 13–15 Oct + Goods | `PPRA_Tenders(13-10-2026 to 15-10-2026, Goods).xlsx` |
| Goods + Info and Comm Tech | `PPRA_Tenders(Goods, Info and Comm Tech).xlsx` |
| Only a start date | `PPRA_Tenders(from 13-10-2026).xlsx` |
| No filters | `PPRA_Tenders_2026-10-17_0650.xlsx` (run start, PKT) |

Country "Pakistan" is left out of the name, since every tender is in Pakistan.

**Sheets**:
1. **PPRA Tenders** — Tender No, Title, Ref No, Sector, Organization, Department / Office, City, Status, Advertised Date, Closing Date, Closing Time (PKT), Days Left (live formula), Link, Change (new / changed / unchanged on a refresh run), Scraped At.
2. **Run Summary** — run id, status, start / finish / duration (PKT), the filters by name, the exact search URL, the closing-date guard and what it skipped, and the tender counts.

---

## 9. Running the System

### Method A: Quick Launch Scripts (Windows)
Double-click, or run from any folder:
1. **Backend**: `run-server.bat` (FastAPI on `http://127.0.0.1:8000`, reloads on code changes)
2. **Frontend**: `run-client.bat` (Next.js on `http://localhost:3000`)

### Method B: Manual Startup

**Terminal 1 — Backend:**
```powershell
cd server
.\.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```
Keep `--reload`: without it, code changes are not picked up until you restart the server.

**Terminal 2 — Frontend:**
```powershell
cd client
npm run dev -- --port 3000
```

Then open:
```
http://localhost:3000/console/ppra
```

---

## 10. API Reference

Interactive docs are served at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/ppra/scrape` | Start a scrape with `{ filters, options, live_preview }`; dropdown filters take the site's ids |
| `POST` | `/ppra/scrape/refresh/{run_id}` | Re-run a previous scrape's filters and mark tenders new / changed / unchanged |
| `GET` | `/ppra/scrape/status/{run_id}` | Full status of one run |
| `GET` | `/ppra/scrape/runs` | Every PPRA run the server holds |
| `GET` | `/ppra/filters` | Every dropdown on the PPRA search form as the site's ids and labels |
| `POST` | `/ppra/filters/refresh` | Re-read those dropdowns from the live site now |
| `GET` | `/ppra/bids` | Tenders for a run (`after_id` cursor for live updates, `query` to search) |
| `GET` | `/runs` | Every run (`?active=true` for those still going) and pool capacity |
| `GET` | `/runs/{run_id}/logs` | Log lines newer than `after` |
| `POST` | `/runs/{run_id}/pause` | Pause a running scrape at its next page |
| `POST` | `/runs/{run_id}/resume` | Resume a paused scrape |
| `POST` | `/runs/{run_id}/stop` | Stop a run (a queued one is cancelled); rows saved so far are kept |
| `GET` | `/runs/{run_id}/screenshot` | Latest browser frame, or `null` |
| `GET` | `/runs/{run_id}/download` | The run's Excel workbook (completed runs, and stopped runs that kept rows) |

---

## 11. Continuous Integration

`.github/workflows/aislop.yml` runs the [aislop](https://github.com/scanaislop/aislop) code-quality gate (v0.18.1) on every pull request and every push to `main`. To set a minimum score, add `.aislop/config.yml` with `ci.failBelow: <score>`.

---

## 12. License

Internal and proprietary. Developed for Pakistan public procurement intelligence.
