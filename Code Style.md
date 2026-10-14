# PK-Hub — Code Style

> These rules exist because they prevented real bugs in scraping-hub. Every rule has a reason.

---

## 1. Python

### 1.1 Formatting & Linting
- **Formatter**: `ruff format` (no Black; Ruff is faster and the output is identical)
- **Linter**: `ruff check` with `select = ["E", "F", "B", "I", "UP"]`
- **Type checker**: `pyright` (strict mode) or `mypy --strict`
- Line length: **100** characters
- No unused imports (`F401` is an error, not a warning)

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
select = ["E", "F", "B", "I", "UP"]

[tool.ruff.format]
quote-style = "double"
```

### 1.2 Naming
| Kind | Convention | Example |
|------|-----------|---------|
| Module | `snake_case` | `parsers.py`, `run_manager.py` |
| Class | `PascalCase` | `PpraScraper`, `BaseScraper` |
| Function | `snake_case` | `parse_listing()`, `upsert_bids()` |
| Private helper | `_snake_case` | `_safe_date()`, `_resolve_chromedriver()` |
| Constant | `UPPER_SNAKE` | `MIN_DAYS_UNTIL_CLOSE`, `WAIT_TIMEOUT` |
| Type alias | `PascalCase` | `FiltersHash = str` |

### 1.3 Type Hints
- **Always** annotate function signatures — no bare `Any` return types
- Prefer `X | Y` over `Optional[X]` (Python 3.10+ union syntax)
- Use `Any` only for JSON blobs stored in JSONB — annotate the field, then be specific internally
- Collection return types: `list[dict[str, Any]]` not `List[Dict]`

```python
# Good
def parse_listing(html: str, base_url: str = "https://epms.ppra.gov.pk") -> list[dict[str, Any]]:

# Bad
def parse_listing(html, base_url="https://epms.ppra.gov.pk"):
```

### 1.4 Docstrings
- Module docstring: one line at the top of every `*.py` file
- Function docstring: required for all public functions; optional for private ones if the name is self-explanatory
- Format: Google-style (no RST)

```python
def upsert_bids(
    run_id: str,
    page_no: int,
    records: list[dict[str, Any]],
    parent_hashes: dict[str, str] | None = None,
) -> tuple[int, int, int]:
    """Upsert bids into ppra_bids. Returns (new_count, changed_count, unchanged_count)."""
```

### 1.5 Date Safety — Non-Negotiable Rule
**Never pass a raw string into a `date` or `timestamptz` column.** Always use `_safe_date()` / `_safe_datetime()` from the portal's `repository.py`.

```python
# Good
"advertised_on": _safe_date(rec.get("advertised_on")),
"closing_at":    _safe_datetime(rec.get("closing_at")),

# Bad — will cause Postgres IntegrityError on values like "2/25-26"
"advertised_on": rec.get("advertised_on"),
```

Any string without a 4-digit year must return `None`. This was the root cause of the original `notify_scrape_completion` crash.

### 1.6 Logging
- Use `logging.getLogger(__name__)` at module level — never `print()`
- Always include `[run %s]` as the first token for greppability:
  ```python
  logger.info("[run %s] scraping page %d of %d", self.run_id, page, total)
  logger.warning("[run %s] closing date unverifiable: %s", self.run_id, raw)
  logger.exception("[run %s] PPRA run failed: %s", self.run_id, exc)
  ```
- `logger.exception()` is for unexpected exceptions that abort the run
- `logger.warning()` is for recoverable bad data (malformed dates, empty rows)
- `logger.debug()` is for per-record detail only turned on in dev

### 1.7 Exception Handling
- Catch the narrowest exception possible
- Bare `except Exception` is allowed **only** in `cleanup()`, `flush_partial()`, and `deliver_partial()` — and must be followed by `logger.exception()`
- Never silence exceptions in scraping logic without re-raising or logging
- `BLE001` (blind exception) is a ruff rule — use `# noqa: BLE001` only in the deliberate cleanup paths, with a comment explaining why

### 1.8 Scraper Pattern

Every portal scraper follows this exact structure:

```python
class {Portal}Scraper(BaseScraper):
    def __init__(self, run_id, filters, options, parent_run_id=None): ...
    def build_filtered_url(self, base_url, page=1) -> str: ...
    def run(self) -> None: ...

def execute_run(run_id, filters_dict, options_dict, parent_run_id=None) -> None:
    """Worker task executed on the thread pool."""
    filters = {Portal}Filters(**filters_dict)
    options = {Portal}Options(**options_dict)
    scraper = {Portal}Scraper(run_id, filters, options, parent_run_id)
    try:
        scraper.run()
        archive_run(run_id)
        notify_scrape_completion(run_id, "{portal}", scraper.rows_scraped_total)
        run_manager.update_run(run_id, status="completed", step="completed")
    except StopRequested:
        ...
    except Exception as exc:
        ...
    finally:
        scraper.cleanup()
```

### 1.9 `notify_scrape_completion` Signature
```python
# Correct — always 3 positional args
notify_scrape_completion(run_id, "ppra", scraper.rows_scraped_total)

# Wrong — missing positional args (this was the original bug)
notify_scrape_completion(run_id)
```

---

## 2. TypeScript / React

### 2.1 Formatting & Linting
- **Formatter**: Prettier (default Next.js config)
- **Linter**: ESLint with `next/core-web-vitals` + `@typescript-eslint/recommended`
- TypeScript: `"strict": true` in `tsconfig.json`

### 2.2 Naming
| Kind | Convention | Example |
|------|-----------|---------|
| Component | `PascalCase` | `PpraPanel`, `ConsoleShell` |
| Hook | `use` prefix, camelCase | `useRunStatus`, `usePortalMeta` |
| Utility | `camelCase` | `portalsForRegion()`, `pluralize()` |
| Constant | `UPPER_SNAKE` | `DEFAULT_PORTAL`, `REGIONS` |
| Type / Interface | `PascalCase` | `PortalMeta`, `RunStatus` |
| File | Matches default export name | `PpraPanel.tsx`, `ConsoleShell.tsx` |

### 2.3 Component Rules
- **One component per file** — no barrel files that re-export dozens of things
- Props interface defined inline above the component, not in a separate types file
- Default export for page/layout components, named export for shared components
- No `any` — use `unknown` then narrow, or define a proper type

```tsx
// Good
interface PpraPanelProps {
  runId: string | null;
  onStart: (filters: PpraFilters) => void;
}
export function PpraPanel({ runId, onStart }: PpraPanelProps) { ... }

// Bad
export default function PpraPanel(props: any) { ... }
```

### 2.4 Tailwind Rules
- **Never build class strings by concatenation or template literals** — the purger won't see them:
  ```tsx
  // Bad
  const cls = `bg-${accent}-500`;
  // Good
  const cls = accent.dot; // e.g. "bg-emerald-500" stored as a full string
  ```
- All conditional classes use the full class name in both branches
- Use `clsx` or `cn()` for conditional merging, not string concatenation

### 2.5 Data Fetching
- Use the typed `api.ts` fetch wrappers — never call `fetch()` inline in a component
- All API calls return typed results; no `as any` casts on response data
- SWR polling interval for run status: `2000ms` (2 seconds)
- Polling stops when `status` is in `['completed', 'stopped', 'failed']`

```typescript
// api.ts pattern
export async function getRunStatus(portal: string, runId: string): Promise<RunStatus> {
  const res = await fetch(`/api/${portal}/runs/${runId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<RunStatus>;
}
```

### 2.6 URL as Source of Truth
- The active portal is determined **only** from `params.portal` in the route
- Never store the active portal in `useState` or `localStorage`
- Navigation between portals uses Next.js `<Link>` with the portal key in the path

---

## 3. Shared Conventions

### 3.1 No Abbreviations
Good names over short names:
```
run_id         ✅   rid        ❌
tender_number  ✅   tno        ❌
filters_hash   ✅   fhash      ❌
parse_listing  ✅   pLst       ❌
```

### 3.2 Single Responsibility
Each file does one thing:
- `parsers.py` — HTML → dicts, **no I/O**
- `repository.py` — DB reads/writes, **no HTML parsing**
- `scraper.py` — Selenium automation, **no direct DB calls** (calls repository)
- `router.py` — HTTP endpoints, **no business logic** (calls scraper / repository)

### 3.3 Parser Purity
`parse_listing()` must be a **pure function** — takes HTML string, returns list of dicts, no side effects. This makes it unit-testable with fixture HTML files without a running browser or DB.

### 3.4 Error Messages
Error messages stored in `ppra_runs.error` must be actionable:
```python
# Good
"The browser was terminated mid-run — most likely the machine ran out of memory."

# Bad
"Connection refused"
"NoneType has no attribute get_text"
```

### 3.5 Migration Files
- File name: `YYYY-MM-DD_<description>.sql`
- All DDL wrapped in `IF NOT EXISTS` / `IF EXISTS` — migrations must be re-runnable
- `ALTER TABLE ... ADD COLUMN` uses `IF NOT EXISTS`
- Never `DROP` anything without a comment explaining what takes its place

---

## 4. Git Conventions

```
feat(ppra): add closing-date filter to listing parser
fix(client): restore region-filtered sidebar after rebase
chore: update chromedriver via webdriver-manager
test(ppra): add fixture for responsive table parse
docs: update database.md with kppra schema
```

Format: `type(scope): description`
- `feat` — new capability
- `fix` — bug fix
- `chore` — dependency, tooling, config
- `test` — test additions or changes only
- `docs` — documentation only

Branch: `feat/<portal>-<feature>`, `fix/<brief-description>`

---

## 5. What We Never Do

| ❌ Never | ✅ Instead |
|---------|---------|
| `print()` in server code | `logger.info/warning/exception()` |
| Raw string dates to Postgres | `_safe_date()` / `_safe_datetime()` |
| `notify_scrape_completion(run_id)` | `notify_scrape_completion(run_id, portal, count)` |
| Build Tailwind classes by string concat | Store full class strings in portal registry |
| Import from `scraping-hub` | Copy and adapt; this is a separate repo |
| `git push --force` to `main` | Always PR; rebase locally before pushing |
