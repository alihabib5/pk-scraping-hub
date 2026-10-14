# PK-Hub — Database Design

## 1. Engine & Version

- **PostgreSQL 15** (minimum; 16 preferred)
- **Extensions**: none required beyond the built-in `uuid` and `jsonb` support
- **Time zone**: all timestamps stored as `timestamptz` (UTC-aware); application converts to `Asia/Karachi` (PKT, UTC+5) for display only
- **Migrations**: plain `.sql` files in `server/migrations/`, run in lexicographic (date-prefixed) order by `apply_migrations.py`

---

## 2. Naming Conventions

| Object | Convention | Example |
|--------|-----------|---------|
| Table | `{portal}_runs`, `{portal}_bids` | `ppra_runs`, `kppra_bids` |
| Primary key | `id bigserial` or `run_id text` | `ppra_bids.id`, `ppra_runs.run_id` |
| Foreign key column | `{referenced_table_singular}_id` | `run_id` → `ppra_runs.run_id` |
| Index | `ix_{table}_{column(s)}` | `ix_ppra_bids_closing` |
| Unique constraint | `uq_{table}_{column(s)}` | `uq_ppra_run_tender` |
| JSONB columns | snake_case, suffix `_data` or use semantic name | `raw_data`, `filters`, `checkpoint` |
| Boolean | no prefix; plain name | `live_preview`, `is_partial` |

---

## 3. Shared Infrastructure Tables

### `pk_runs` — cross-portal run registry (optional, for dashboard totals)
```sql
CREATE TABLE IF NOT EXISTS pk_runs (
  run_id      text PRIMARY KEY,          -- matches ppra_runs.run_id etc.
  portal      text NOT NULL,             -- 'ppra' | 'kppra' | 'ppra_sindh' ...
  status      text NOT NULL,             -- 'pending'|'running'|'completed'|'stopped'|'failed'
  started_at  timestamptz,
  finished_at timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_pk_runs_portal_created ON pk_runs (portal, created_at DESC);
```

---

## 4. PPRA Federal Schema

### `ppra_runs`
```sql
CREATE TABLE IF NOT EXISTS ppra_runs (
  -- identity
  run_id          text PRIMARY KEY,
  parent_run_id   text REFERENCES ppra_runs(run_id) ON DELETE SET NULL,

  -- lifecycle
  status          text NOT NULL,          -- see scraper lifecycle in architecture.md
  step            text,                   -- human-readable sub-step label
  error           text,                   -- first failure message if status='failed'
  is_partial      boolean NOT NULL DEFAULT false,

  -- input
  filters         jsonb NOT NULL,         -- PpraFilters as stored JSON
  filters_hash    text NOT NULL,          -- sha256(canonical JSON) for dedup
  options         jsonb NOT NULL DEFAULT '{}',
  live_preview    boolean NOT NULL DEFAULT false,

  -- progress counters
  total_expected  integer,
  total_pages     integer,
  current_page    integer NOT NULL DEFAULT 0,
  rows_scraped    integer NOT NULL DEFAULT 0,
  rows_new        integer NOT NULL DEFAULT 0,
  rows_changed    integer NOT NULL DEFAULT 0,
  skipped_closing integer NOT NULL DEFAULT 0,
  kept_unverified integer NOT NULL DEFAULT 0,

  -- resume support
  checkpoint      jsonb NOT NULL DEFAULT '{}',

  -- timestamps
  started_at      timestamptz,
  finished_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_ppra_runs_created    ON ppra_runs (created_at DESC);
CREATE INDEX ix_ppra_runs_hash       ON ppra_runs (filters_hash);
CREATE INDEX ix_ppra_runs_status     ON ppra_runs (status) WHERE status IN ('running','pending');
```

### `ppra_bids`
```sql
CREATE TABLE IF NOT EXISTS ppra_bids (
  id              bigserial PRIMARY KEY,

  -- run reference
  run_id          text NOT NULL REFERENCES ppra_runs(run_id) ON DELETE CASCADE,
  page_no         integer NOT NULL,
  position        integer NOT NULL,

  -- core tender fields
  tender_no       text NOT NULL,
  title           text NOT NULL,
  description     text,
  sector          text,
  tender_ref_no   text,
  tender_type     text,                   -- 'Tender Notice'|'RFP'|'EOI'|'PQ'
  category        text,                   -- 'Goods'|'Works'|'Consultancy Services'|...
  nature          text,                   -- 'Local'|'International'
  organization    text,
  department      text,
  city            text,
  country         text NOT NULL DEFAULT 'Pakistan',
  status          text,                   -- 'Published'|'Cancelled'

  -- dates (PKT-aware)
  advertised_on   date,
  closing_at      timestamptz,

  -- links
  detail_url      text,
  invoice_url     text,

  -- change tracking
  content_hash    text NOT NULL,          -- sha256 over key fields for diff detection
  change_status   text NOT NULL DEFAULT 'new',   -- 'new'|'changed'|'unchanged'
  diff            jsonb,                  -- {field: [old, new]} when changed

  -- raw scrape
  raw_data        jsonb NOT NULL DEFAULT '{}',
  scraped_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uq_ppra_run_tender UNIQUE (run_id, tender_no)
);

CREATE INDEX ix_ppra_bids_run_id   ON ppra_bids (run_id, id);
CREATE INDEX ix_ppra_bids_closing  ON ppra_bids (closing_at);
CREATE INDEX ix_ppra_bids_tender   ON ppra_bids (tender_no);
CREATE INDEX ix_ppra_bids_org      ON ppra_bids (organization);
CREATE INDEX ix_ppra_bids_status   ON ppra_bids (status);
```

### `ppra_filter_options`
```sql
CREATE TABLE IF NOT EXISTS ppra_filter_options (
  kind          text NOT NULL,            -- 'tender_type'|'category'|'sector'|'nature'|'status'
  value         text NOT NULL,
  label         text NOT NULL,
  sort_order    integer NOT NULL DEFAULT 0,
  refreshed_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (kind, value)
);
```

---

## 5. Provincial Portal Pattern

Each province follows the same 3-table pattern. Example for KP-PPRA:

```sql
CREATE TABLE IF NOT EXISTS kppra_runs  ( ... );   -- identical structure to ppra_runs
CREATE TABLE IF NOT EXISTS kppra_bids  ( ... );   -- identical structure to ppra_bids
CREATE TABLE IF NOT EXISTS kppra_filter_options ( ... );
```

Fields can be added per-portal as needed (e.g. `kppra_bids.procurement_method`).

---

## 6. Upsert Strategy

All bids are upserted (not inserted blindly) so re-running the same filters on the same day doesn't create duplicate rows. The `content_hash` detects genuine changes:

```python
# In repository.py
stmt = (
    pg_insert(PpraBid)
    .values(**values)
    .on_conflict_do_update(
        constraint="uq_ppra_run_tender",
        set_={k: v for k, v in values.items() if k not in ("run_id", "tender_no")},
    )
)
session.execute(stmt)
```

**Change status logic**:
- `new` — tender_no not seen in parent run (first scrape, or truly new tender)
- `changed` — tender_no seen, but `content_hash` differs (title/status/dates changed)
- `unchanged` — tender_no and hash identical (no action needed)

---

## 7. Date Safety Rules

**Never** insert raw string dates into `date` or `timestamptz` columns.

```python
def _safe_date(val) -> date | None:
    """Reject strings without a 4-digit year. '2/25-26' → None."""
    if not re.search(r'\b20\d{2}\b', str(val)):
        return None
    ...  # parse with dateutil

def _safe_datetime(val) -> datetime | None:
    """Always attach UTC tzinfo; never store naive datetimes."""
    ...
```

---

## 8. Migration Workflow

```
server/migrations/
  2026-10-14_ppra_tables.sql
  2026-10-14_kppra_tables.sql
  2026-11-01_ppra_add_dept_index.sql
```

Run with:
```bash
server/.venv/Scripts/python.exe server/apply_migrations.py
```

`apply_migrations.py` tracks applied migrations in `schema_migrations` table:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  name       text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);
```

**Rules**:
- Never edit a migration that has already been applied to production
- New columns → new migration (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`)
- Schema changes that could lose data require a rollback migration alongside
