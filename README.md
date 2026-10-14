# PK-Hub — Pakistan Procurement Intelligence & Active Tender Harvester

> **An automated discovery, live monitoring, and structured extraction engine for Pakistan's federal Public Procurement Regulatory Authority (PPRA) e-Procurement System ([EPMS](https://epms.ppra.gov.pk/public/tenders/active-tenders)).**

---

## 1. Overview & End-to-End Capabilities

**PK-Hub** is a dedicated procurement intelligence platform engineered for businesses, contractors, and market analysts tracking public sector opportunities across Pakistan. Rather than manually navigating paginated, dynamic government portals, PK-Hub automates the entire ingestion lifecycle:

- **Filterable Discovery**: Search active tenders by organization, sector, category, tender type, procedure, or keyword.
- **7-Day Closing Runway Guard**: Automatically flags or prioritizes tenders closing at least 7 days out, preventing wasted bids on expiring opportunities.
- **Live Scraper Console**: Full operational control over active scrapes with **Start**, **Pause**, **Resume**, **Stop**, and **Refresh**.
- **Live Visual Monitor**: Broadcasts real-time screenshots from the headless browser session directly into the dashboard.
- **Live-Streaming Results Grid**: Tenders appear in the interactive data table in real-time as they are extracted page-by-page.
- **Styled Excel Workbooks**: Automatically compiles structured `.xlsx` workbooks with color-coded status highlights, formatted dates, and deep links to tender dossiers.
- **Historical Audit & Resumable Runs**: Run checkpoints and metadata persist to PostgreSQL so past jobs can be re-inspected or downloaded at any time.

---

## 2. Technology Stack

### Frontend (`client/`)
- **Framework**: [Next.js 16](https://nextjs.org/) (App Router & Turbopack)
- **Language**: TypeScript 5 (Strict Mode)
- **Styling**: Tailwind CSS v4 (`@tailwindcss/postcss`) with custom editorial tokens (`paper`, `ink-900`, `gold-500`)
- **Typography**: Newsreader (editorial serif headings) + Inter (clean interface body)
- **State Architecture**: `useSyncExternalStore` persistent session engine (runs survive client route changes)

### Backend (`server/`)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
- **ORM & Database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [PostgreSQL 15+](https://www.postgresql.org/) with `psycopg2`
- **Automation / Scraping**: Playwright / Selenium 4 headless automation with anti-detection headers
- **HTML Parsing**: BeautifulSoup4 + `lxml`
- **Concurrency & Pooling**: `ThreadPoolExecutor` scrape worker pool with concurrency caps
- **Data Packaging**: `openpyxl` with custom styling engines for publication-grade spreadsheets

---

## 3. System Architecture

```mermaid
flowchart TD
    subgraph Target["Target Authority"]
        PPRA["epms.ppra.gov.pk<br/>(Active Tenders EPMS)"]
    end

    subgraph Server["FastAPI Backend (Port 8000)"]
        API["FastAPI App Router<br/>(main.py / app/main.py)"]
        ScrapeWorker["BaseScraper Engine<br/>(Headless Browser Session)"]
        LiveBus["Live Screenshot Bus<br/>(live.py)"]
        Checkpointer["Checkpoint & Run Manager<br/>(run_manager.py)"]
        ExcelEngine["Excel Packaging Engine<br/>(excel_style.py)"]
    end

    subgraph Storage["Persistent Storage"]
        PG[("PostgreSQL 15+<br/>(pk-hub DB on Port 5432)")]
        DataDir[("Local Data Mirror<br/>(data/documents/*.xlsx)")]
    end

    subgraph Client["Next.js 16 Client (Port 3000)"]
        UI["Editorial Console Shell<br/>(PpraPanel / PpraResults)"]
        SessionStore["External Session Store<br/>(sessions.ts / useSession)"]
        LiveMonitor["Live Monitor Component<br/>(Screencast Poller)"]
    end

    UI -->|"1. POST /ppra/scrape (filters)"| API
    API -->|"2. Dispatch thread"| ScrapeWorker
    ScrapeWorker -->|"3. Navigate & Extract"| PPRA
    ScrapeWorker -->|"4. Stream frame"| LiveBus
    ScrapeWorker -->|"5. Upsert tenders"| PG
    LiveBus -->|"6. GET /runs/{id}/screenshot"| LiveMonitor
    ScrapeWorker -->|"7. Build XLSX"| ExcelEngine
    ExcelEngine -->|"8. Save workbook"| DataDir
    SessionStore -->|"9. Poll /ppra/bids & /runs"| API
    API -->|"10. Hydrate state"| UI
```

### End-to-End Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Procurement Officer
    participant Console as Next.js Console (Port 3000)
    participant API as FastAPI Server (Port 8000)
    participant Worker as Scraper Engine
    participant DB as PostgreSQL (Port 5432)
    participant EPMS as PPRA EPMS Portal

    User->>Console: Configure filters & click "Start PPRA Scrape"
    Console->>API: POST /ppra/scrape { date_from, date_to, sector, org }
    API->>DB: INSERT into ppra_runs (status='running')
    API-->>Console: 202 Accepted { run_id: "ppra_20261015_abc" }
    
    activate Worker
    API->>Worker: Launch scraper thread
    Worker->>EPMS: Load active-tenders & apply form filters
    Worker->>Console: Stream live screenshot frame
    Worker->>EPMS: Extract table rows (Tender No, Org, Title, Close Date)
    Worker->>DB: Bulk upsert into ppra_bids
    
    loop Every 2 Seconds
        Console->>API: GET /ppra/bids?run_id=ppra_20261015_abc
        API->>DB: Query newest bids
        API-->>Console: Return new bids array
        Console->>User: Update live results table & counter
    end

    Worker->>Worker: Generate styled Excel (.xlsx)
    Worker->>DB: UPDATE ppra_runs SET status='completed'
    deactivate Worker
    
    Console->>User: Display "Completed" status badge & Download Excel button
```

---

## 4. Repository Layout

```
pk-hub/
├── client/                     # Next.js 16 frontend application
│   ├── src/
│   │   ├── app/                # App router (landing, console, history, exports)
│   │   │   ├── console/
│   │   │   │   ├── [portal]/   # Dynamic portal console (/console/ppra)
│   │   │   │   └── layout.tsx  # Persistent layout with ActiveJobs runner
│   │   │   ├── layout.tsx      # Font and theme setup (Newsreader + Inter)
│   │   │   └── page.tsx        # Editorial landing page
│   │   ├── components/         # Production UI components
│   │   │   ├── PpraPanel.tsx   # Filter form & run controls (Start/Pause/Stop)
│   │   │   ├── PpraResults.tsx # Real-time bids data table
│   │   │   ├── LiveMonitor.tsx # Screencast window for headless browser
│   │   │   └── ui.tsx          # Editorial UI primitives (Button, DataTable, Badge)
│   │   ├── lib/
│   │   │   ├── api.ts          # Strongly-typed API client
│   │   │   ├── portals.ts      # Pakistan portal registry
│   │   │   ├── sessions.ts     # External store session manager
│   │   │   └── runs.ts         # Run formatting and state helpers
│   │   ├── .env.example        # Client environment template
│   │   └── package.json
│   │
├── server/                     # FastAPI backend application
│   ├── app/
│   │   ├── config.py           # Pydantic v2 application settings
│   │   ├── db.py               # Database engine & session maker
│   │   ├── main.py             # FastAPI app with CORS & routers
│   │   ├── core/               # Scraper engine infrastructure
│   │   │   ├── base_scraper.py # Headless browser controller
│   │   │   ├── run_manager.py  # Thread state, cancel flags & status
│   │   │   ├── live.py         # Screenshot broadcaster
│   │   │   ├── checkpoints.py  # Pause & resume state persistence
│   │   │   └── exports.py      # Styled Excel generation
│   │   ├── scrapers/ppra/      # PPRA Pakistan Scraper
│   │   │   ├── scraper.py      # Scraper loop & page traverser
│   │   │   ├── parsers.py      # Table & tender card parser
│   │   │   ├── models.py       # SQLAlchemy ORM definitions
│   │   │   ├── schemas.py      # Pydantic request/response schemas
│   │   │   └── router.py       # Scrape & bid query endpoints
│   │   └── services/           # Background email / notification services
│   ├── main.py                 # Root uvicorn entrypoint (main:app)
│   ├── .env.example            # Server environment template
│   └── requirements.txt        # Server Python dependencies
│
├── data/                       # Scraped exports and attachments (.xlsx, .zip)
├── run-client.bat              # 1-click client startup script (Windows)
├── run-server.bat              # 1-click server startup script (Windows)
└── .gitignore                  # Git cache, dependency, and secret exclusions
```

---

## 5. One-Time Setup Guide

### Step 1: Prerequisites
Ensure the following tools are installed on your machine:
- **Node.js**: v18.18.0 or newer (v20+ recommended)
- **Python**: v3.12 or newer
- **PostgreSQL**: v15 or newer (running on port `5432`)
- **Google Chrome** or **Chromium** (for headless automation)

---

### Step 2: PostgreSQL Database Initialization
Open PowerShell or your command prompt and create the `pk-hub` database:

```powershell
# Connect to PostgreSQL and create the database
createdb -U postgres -p 5432 pk-hub
```

*(If prompted, enter your PostgreSQL superuser password).*

---

### Step 3: Backend Setup (`server/`)

1. Open PowerShell and navigate to the `server` directory:
   ```powershell
   cd C:\Users\Aliha\Downloads\pk-hub\server
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. Install required Python packages:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Create your local `.env` file:
   ```powershell
   cp .env.example .env
   ```
   *Edit `.env` to verify your PostgreSQL credentials:*
   ```ini
   DOWNLOAD_DIR=../data/documents
   DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/pk-hub
   ```

5. Verify that the server can start and initialize tables:
   ```powershell
   uvicorn main:app --reload --port 8000
   ```
   *You should see:*
   ```
   INFO: Database tables ready
   INFO: Uvicorn running on http://127.0.0.1:8000
   ```
   *(Press `Ctrl + C` to stop).*

---

### Step 4: Frontend Setup (`client/`)

1. In a separate terminal, navigate to the `client` directory:
   ```powershell
   cd C:\Users\Aliha\Downloads\pk-hub\client
   ```

2. Install Node dependencies:
   ```powershell
   npm install
   ```

3. Create the local frontend `.env` file:
   ```powershell
   cp .env.example .env.local
   ```
   *Confirm the API URL points to your FastAPI backend:*
   ```ini
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Verify the production build compiles cleanly:
   ```powershell
   npm run build
   ```

---

## 6. Running the System

You can run both servers simultaneously using the provided Windows one-click batch scripts or directly from terminal windows.

### Method A: Quick Launch Scripts (Windows)
Double-click or run from the project root:
1. **Start Backend**: Run `run-server.bat` (starts FastAPI on `http://127.0.0.1:8000`)
2. **Start Frontend**: Run `run-client.bat` (starts Next.js on `http://localhost:3000`)

---

### Method B: Manual Startup

**Terminal 1 — Backend:**
```powershell
cd server
.\.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd client
npm run dev -- --port 3000
```

Open your browser and navigate to:
```
http://localhost:3000/console/ppra
```

---

## 7. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service health status and registered scrapers |
| `POST` | `/ppra/scrape` | Trigger an active tender scrape job with optional filters |
| `GET` | `/ppra/bids` | Fetch extracted tenders for a specific run with pagination |
| `GET` | `/ppra/export` | Download a freshly compiled Excel workbook of all stored tenders |
| `GET` | `/runs` | List all active or historical scraper jobs |
| `POST` | `/runs/{run_id}/pause` | Pause an active scraping run at the nearest checkpoint |
| `POST` | `/runs/{run_id}/resume` | Resume a parked scrape job |
| `POST` | `/runs/{run_id}/stop` | Gracefully terminate a run and preserve partial results |
| `GET` | `/runs/{run_id}/screenshot` | Retrieve latest visual frame from the headless browser |
| `GET` | `/runs/{run_id}/download` | Download completed or partial run archive / spreadsheet |

---

## 8. License

Internal and proprietary. Developed for Pakistan public procurement intelligence.
