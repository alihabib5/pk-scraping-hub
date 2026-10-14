# PK-Hub — Project Plan

> **Mission**: A standalone, self-contained procurement intelligence platform exclusively for Pakistani government portals — no coupling to scraping-hub, no US portal code, no shared deployment.

---

## 1. What We Are Building

**PK-Hub** is an internal tool for discovering, tracking, and exporting active procurement tenders published by Pakistani government bodies. It begins with PPRA (federal) and is designed from day one to scale into every province and authority that exposes structured bid data.

It is **not** a branch of scraping-hub. It is a clean, separate repository with its own:
- Next.js 16 frontend (TypeScript, Tailwind, App Router)
- FastAPI backend (Python 3.12+, SQLAlchemy, PostgreSQL)
- Selenium scraping engine (ChromeDriver, headless Chrome)
- PostgreSQL database (own schema, own migrations, running locally or on managed Postgres)
- Direct bare-metal / local execution (Standard Python venv + Node.js, zero Docker)

---

## 2. Pakistani Portals — Phase Roadmap

### Phase 1 — MVP (Current Sprint)
| Portal | Authority | URL | Status |
|--------|-----------|-----|--------|
| **PPRA Federal** | Public Procurement Regulatory Authority | `epms.ppra.gov.pk` | ✅ Scraper built in scraping-hub → migrate here |

### Phase 2 — Provincial Authorities
| Portal | Authority | URL | Status |
|--------|-----------|-----|--------|
| **KPRA / KP-PPRA** | KP Province Procurement | `kppra.gov.pk` | 🔲 Planned |
| **PPRA Punjab** | Punjab Procurement Regulatory Authority | `ppra.punjab.gov.pk` | 🔲 Planned |
| **PPRA Sindh** | Sindh Procurement Regulatory Authority | `sppra.gos.pk` | 🔲 Planned |
| **PPRA Balochistan** | Balochistan Procurement | `bppra.gob.pk` | 🔲 Planned |

### Phase 3 — Specialized Bodies
| Portal | Authority | URL | Status |
|--------|-----------|-----|--------|
| **OGDCL / PSO** | Energy sector SOEs | `ogdcl.com/tenders` | 🔲 Planned |
| **WAPDA** | Water & Power Development Authority | `wapda.gov.pk` | 🔲 Planned |
| **PNSC** | Pakistan National Shipping | `pnsc.com.pk` | 🔲 Planned |
| **NHA** | National Highway Authority | `nha.gov.pk` | 🔲 Planned |
| **PTA** | Pakistan Telecom Authority | `pta.gov.pk` | 🔲 Planned |

---

## 3. Development Milestones

### M1 — Repo Bootstrap (Week 1)
- [ ] Create `pk-hub/` repository (separate from `scraping-hub`)
- [ ] Scaffold Next.js 16 client (`client/`) with TypeScript strict, Tailwind CSS, ESLint
- [ ] Scaffold FastAPI server (`server/`) with SQLAlchemy, Alembic, Pydantic v2
- [ ] PostgreSQL schema baseline (runs, bids, filter_options tables)
- [ ] `.env.example`, native setup script for local dev (venv + npm)
- [ ] CI skeleton (GitHub Actions: lint, type-check, build)

### M2 — PPRA Portal (Week 2)
- [ ] Migrate PPRA scraper from scraping-hub (parsers, repository, scraper, schemas)
- [ ] FastAPI router: `POST /api/ppra/runs`, `GET /api/ppra/runs/{id}`, `GET /api/ppra/runs/{id}/bids`, `GET /api/ppra/filter-options`
- [ ] Frontend portal panel: filter form, run controls (Start / Stop / Pause)
- [ ] Real-time progress polling (run status, bids_processed, current_page)
- [ ] Excel export (`GET /api/ppra/runs/{id}/download`)
- [ ] Run history page

### M3 — Core Platform Shell (Week 3)
- [ ] Portal registry (`portals.ts`) — PK-only, no region switching needed
- [ ] Console shell: sidebar listing all PK portals, header with portal name + operator
- [ ] Home / landing page: portal cards with counts, live status badges
- [ ] Shared run list + history table component
- [ ] Exports page per portal

### M4 — Quality & Hardening (Week 4)
- [ ] Parser unit tests (fixtures for PPRA responsive table HTML)
- [ ] Date sanitizer tests (`_safe_date`, `_safe_datetime`)
- [ ] Closing filter tests (7-day guard)
- [ ] API integration tests (pytest, TestClient, SQLite for speed)
- [ ] Full `npm run build` clean pass
- [ ] Playwright E2E smoke: launch run → see progress → download

### M5 — Second Portal: KP-PPRA (Week 5–6)
- [ ] Scraper for `kppra.gov.pk` (login-free listing or auth if required)
- [ ] DB tables: `kppra_runs`, `kppra_bids`
- [ ] API router + frontend panel

---

## 4. Non-Goals (explicit)
- ❌ No US portals of any kind
- ❌ No shared codebase or imports from `scraping-hub`
- ❌ No NAICS codes, SAM.gov, or US-specific reference data
- ❌ No multi-region switcher in the UI (all portals are PK)
- ❌ No AI evaluation pipeline in Phase 1 (SAM-style bid scoring is Phase 3+)

---

## 5. Team Conventions
- Branch naming: `feat/<portal>-<feature>` e.g. `feat/ppra-closing-filter`
- Every portal gets its own branch for the initial scraper build
- No direct pushes to `main`; always PR with at least one review
- Run `npm run build` and `python -m compileall server` before every merge
- Migrations named `YYYY-MM-DD_<description>.sql`; never edit a shipped migration
