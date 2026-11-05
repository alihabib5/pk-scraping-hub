# Plan: PPRA Punjab Scraper

**Status: built and verified on the branch `feature/punjab-scraper`. Not committed or merged yet.**

This was the working plan. The phases ran in order, and each passed its gate. The results are in section 9.

| Document | Answers |
|---|---|
| **plan.md** (this file) | What do we do, in what order, and how do we know it worked? |
| [architecture.md](architecture.md) | Where does each piece live, and how does it stay separate from PPRA? |
| [system-design.md](system-design.md) | How does the site behave, and exactly how does the scraper work? |
| [security.md](security.md) | What can go wrong from a security view, and what must we build? |

When the work is finished, the lasting parts of these documents move into the main [README.md](../README.md) (Phase 8).

---

## 1. Goal

Add a second portal to PK-Hub that collects live tenders from <https://eproc.punjab.gov.pk/Admin_Tender_Search.aspx>, excludes auctions, and gives the same console, history and Excel experience as PPRA.

### In scope
- Live tenders with their two PDF links, stored per run
- Filters: Type, Category, Title, Department, closing date range
- Auction exclusion and the closing-date guard
- Start, Pause, Resume, Stop, Refresh, Live Preview, History, Download

### Out of scope
- Downloading or reading the PDFs
- Closing time and city, which the site's table doesn't provide
- Linking a Corrigendum to its original tender, which the site doesn't provide
- Fixing existing PPRA security gaps (listed in [security.md](security.md#6-existing-gaps-in-shared-code), for a separate decision)

---

## 2. The one rule: PPRA must keep working

Every phase follows these rules. The reasons are in [architecture.md](architecture.md#5-how-ppra-stays-safe).

1. Don't edit anything in `server/app/scrapers/ppra/`.
2. Don't change any `ppra_*` table.
3. Change shared files only where this plan lists them, and only by adding a branch for Punjab. PPRA's path stays as it is.
4. Run the PPRA regression gate (section 6) after every phase that touches shared code.

---

## 3. Decisions

These weren't changed before building, so **the defaults below are what was built**. Each one is a small change if you want a different answer.

| # | Question | Default used | Needed by |
|---|---|---|---|
| 1 | Auctions: always removed, or a checkbox? | Checkbox, ticked by default | Phase 2 |
| 2 | Also remove the 4 auctions filed in other categories, using the word check? | No, changed on your instruction: only the Procurement Title `Sales/Auction/Disposal` is excluded | Phase 1 |
| 3 | Keep `Violated Tender` rows? | Keep and show the status | Phase 1 |
| 4 | Keep Corrigendum and Addendum rows? (44 rows) | Keep, with the Title filter available | Phase 1 |
| 5 | Closing guard default? It removed 360 of 909 tenders | 7 days, adjustable | Phase 6 |
| 6 | Portal key and label? | `punjab`, "PPRA Punjab" | Phase 2 |

---

## 4. Readiness on 5 November 2026

| Item | State | Action |
|---|---|---|
| PostgreSQL 18 | Running, connection confirmed | None |
| `pg_hba.conf` | All entries use `scram-sha-256`, so no `trust` left over | None |
| Postgres password | Reset, stored only in `server\.env` | Keep it to letters and digits, or URL-encode it |
| `server\.env` | Created | None |
| `pk-hub` database | Created, with PPRA and Punjab tables | None |
| `server\.venv` | Installed on Python 3.15.2 | None |
| PPRA test baseline | 19 passed | None |
| `client\node_modules` | Present, build passes | None |

PK-Hub ran correctly on Python 3.15.2 throughout this work. FastAPI prints a deprecation warning that says it will need updating for Python 3.16.

---

## 5. Phases

### Phase 0: Prepare and record the baseline

Nothing is built here. This phase records how PPRA behaves today so we can prove later that it didn't change.

- [x] Install `requirements.txt` in `server\.venv`
- [x] Create `server\.env` with the real `DATABASE_URL`
- [x] Confirm the `pk-hub` database exists, and create it if not
- [x] Start the server and confirm `Database tables ready`
- [x] Run `pytest` and record the result in section 9
- [x] Run `npm run build` in `client\` and record the result
- [x] Run one small PPRA scrape, download the workbook, and keep it as the reference
- [x] Create the branch `feature/punjab-scraper`

**Gate:** the tests and the build have a recorded result, and a PPRA workbook downloads. If a test already fails, note it so it isn't blamed on this work later.

### Phase 1: Parser and test pages

Pure functions with no browser or database, so this is the safest place to start.

- [x] Save real pages to `server/tests/fixtures/punjab/`: normal page, last page, one-page result, empty result. Remove the hidden form state to keep them small
- [x] Write `parsers.py`: `parse_listing`, `parse_pager`, `parse_options`, `tender_id_from_links`, `is_auction`, `to_iso_date`, `safe_pdf_url`, `check_columns`
- [x] Write `tests/test_punjab_parsers.py`

**Gate:** tests cover every auction example and false match in [system-design.md](system-design.md#6-excluding-auctions), one-page and empty results, the date format, and rejected links.

### Phase 2: Data layer

- [x] `models.py`: `punjab_runs`, `punjab_bids`, `punjab_filter_options`
- [x] `schemas.py`: `PunjabFilters`, `PunjabOptions`, `PunjabScrapeRequest`, with the validation from [security.md](security.md#4-controls-to-build)
- [x] `repository.py`
- [x] `filters.py` and the seed file `filter_options.json`
- [x] Shared edits: [db.py](../server/app/db.py) and [config.py](../server/app/config.py)
- [x] Update `.env.example` with the new optional settings

**Gate:** the server starts, the three new tables exist, and the `ppra_*` tables are unchanged. Run the PPRA gate.

### Phase 3: Scraper

- [x] `scraper.py`: search, page loop, reload wait, page check, recovery, worker task
- [x] Run it live from a small test script, using PK-Hub's real Chrome settings

**Gate:** one live run reads every page, unique rows match the site's total, no auctions are saved, and Pause, Resume and Stop work. This phase also settles the first item in [system-design.md](system-design.md#12-not-yet-tested), which is whether PK-Hub's DNS-over-HTTPS setting works with this site.

### Phase 4: API

- [x] `router.py`, with the `/punjab` routes
- [x] Shared edit: [main.py](../server/app/main.py)
- [x] Add tests that a Refresh refuses a PPRA run id and that bad filters are rejected

**Gate:** all routes work from `/docs`. Run the PPRA gate.

### Phase 5: Excel

- [x] `export.py`: workbook, Run Summary and `excel_name`
- [x] Shared edit: [exports.py](../server/app/core/exports.py), the most sensitive change in this plan
- [x] Add `tests/test_punjab_export.py`, with the export dispatch tests there and in `tests/test_punjab_api.py`

**Gate:** Punjab and PPRA runs each produce their own workbook. Compare a PPRA download with the Phase 0 reference: same sheets, columns and filename pattern. Run the PPRA gate.

### Phase 6: Console

- [x] `api.ts`: `Portal` type, new option and count fields, Punjab calls
- [x] `portals.ts`: new entry, which also adds Punjab to the sidebar, the jobs bar and the routes
- [x] New `PunjabPanel.tsx` and `PunjabResults.tsx`
- [x] `PortalPanelHost.tsx` and `ConsoleShell.tsx`: show the panel for the current portal
- [x] `RunHistory.tsx`: show results by `run.scraper`
- [x] `RunStatus.tsx`: add the Punjab step label and the auction note
- [x] Footer text and a landing page card

**Gate:** `npm run build` passes, and both consoles work at `/console/ppra` and `/console/punjab`. Run the PPRA gate.

### Phase 7: Full verification

- [x] Run the checklist in section 7
- [x] Run both portals at the same time
- [x] Complete the release checklist in [security.md](security.md#7-release-checklist)

### Phase 8: Update the README and finish

- [x] Update the main [README.md](../README.md): overview, layout, settings, API, Excel, filters
- [ ] Open the pull request, once you approve it

---

## 6. PPRA regression gate

Run this after Phases 2, 4, 5 and 6, and again in Phase 7.

| Check | Pass means |
|---|---|
| `pytest` | Same result as the Phase 0 baseline, plus the new tests passing |
| `git diff main -- server/app/scrapers/ppra` | Empty |
| Filename | A PPRA run still gets a `PPRA_Tenders...xlsx` name |
| Workbook | Same two sheets and same columns as the reference |
| `npm run build` | Passes |
| Console (Phases 6 and 7) | PPRA can start, pause, resume, stop, refresh, open history and download |

If a check fails, stop and fix it before continuing.

---

## 7. Definition of done

- [x] Unique rows read equal the site's total, or the run shows a warning explaining the gap
- [x] No saved tender matches `is_auction()` when exclusion is on
- [x] Every saved closing date meets the closing guard
- [x] A closing date range includes tenders closing on its last day
- [x] One-page, empty and multi-page searches all finish correctly
- [x] Pause, Resume, Stop, Refresh, Live Preview, History and Download all work
- [x] A stopped run still gives a partial workbook
- [x] A Refresh run marks tenders new, changed or unchanged
- [x] Both PDF links in the Excel open the right documents
- [x] The PPRA regression gate passes

---

## 8. Rollback

The work sits on its own branch, so `main` is untouched until the pull request is merged.

After a merge, reverting that merge restores the old code. The three `punjab_*` tables would remain, but nothing would use them, and they don't affect PPRA. Dropping them is optional, and it deletes all Punjab results, so it needs your approval.

---

## 9. Progress log

| Date | Phase | Result | Notes |
|---|---|---|---|
| 5 Nov 2026 | Research | Done | Site tested, code read, these documents written |
| 5 Nov 2026 | Phase 0 | Passed | `pytest` 19 passed, `npm run build` passed, reference PPRA run of 84 tenders on 2 pages |
| 5 Nov 2026 | Phase 1 | Passed | 41 parser tests, using 4 real pages captured through PK-Hub's own Chrome settings |
| 5 Nov 2026 | Phases 2 to 5 | Passed | Live run: 944 on site = 559 kept + 25 auctions + 360 closing too soon. No duplicates, auctions or bad links saved |
| 5 Nov 2026 | Phase 6 | Passed | Build passed, and the console was driven in a real browser. The project has no ESLint config, so lint wasn't run |
| 5 Nov 2026 | Phase 7 | Passed | Both portals ran at once. Forced failure recovered on the live site. PPRA workbook matched the reference cell for cell. PPRA pause, resume, stop and refresh all work |
| 5 Nov 2026 | Final | 99 tests passed | 19 PPRA tests unchanged plus 80 new. Diff of `scrapers/ppra` and PPRA tests is empty |
| 5 Nov 2026 | Change | Word check removed | Exclusion now matches only the Procurement Title `Sales/Auction/Disposal`. The live counts above are from before this change |
