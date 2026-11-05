"""Punjab search filters: the site's dropdown options, the run's filter hash, and
the dates a run searches.

The option lists live in `punjab_filter_options`, refreshed from the live page on
every scrape and on demand. Until the first refresh, the checked-in
`filter_options.json` seed is served, so the dropdowns are never empty.
"""

import hashlib
import json
import logging
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.scrapers.punjab.models import PunjabFilterOption
from app.scrapers.punjab.schemas import PunjabFilters

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).with_name("filter_options.json")
PKT = ZoneInfo("Asia/Karachi")

# Far enough for any tender: the furthest close date seen was about 8 months out.
DEFAULT_SEARCH_DAYS = 730

# PunjabFilters field -> the name shown in filenames and the Excel summary. Each
# dropdown field shares its name with the option `kind` it draws from.
FIELD_NAMES = {
    "procurement_type": "Type",
    "procurement_category": "Category",
    "procurement_title": "Title",
    "department": "Department",
}

_lock = threading.Lock()
_cache: dict | None = None  # {"options": {kind: [...]}, "refreshed_at": str | None, "source": str}


def _load() -> dict:
    """The option lists from the DB, or the seed file when the DB has none."""
    try:
        session = SessionLocal()
        try:
            rows = session.execute(
                select(PunjabFilterOption).order_by(PunjabFilterOption.kind, PunjabFilterOption.sort_order)
            ).scalars().all()
            refreshed = session.execute(select(func.max(PunjabFilterOption.refreshed_at))).scalar()
        finally:
            session.close()
        if rows:
            options: dict[str, list[dict[str, str]]] = {}
            for row in rows:
                options.setdefault(row.kind, []).append({"value": row.value, "label": row.label})
            return {
                "options": options,
                "refreshed_at": refreshed.isoformat() if refreshed else None,
                "source": "site",
            }
    except Exception:  # noqa: BLE001 — fall back to the seed rather than show empty dropdowns
        logger.exception("could not read cached Punjab filter options")
    return {
        "options": json.loads(SEED_PATH.read_text(encoding="utf-8")),
        "refreshed_at": None,
        "source": "seed",
    }


def get_filter_options() -> dict:
    """{"options": {kind: [{value, label}]}, "refreshed_at", "source"}."""
    global _cache
    with _lock:
        if _cache is None:
            _cache = _load()
        return _cache


def save_filter_options(options: dict[str, list[dict[str, str]]]) -> int:
    """Replace the cached lists for each kind present. Returns the option count."""
    global _cache
    if not options:
        return 0
    now = datetime.now(timezone.utc)
    session = SessionLocal()
    try:
        for kind, entries in options.items():
            session.execute(delete(PunjabFilterOption).where(PunjabFilterOption.kind == kind))
            # One row per id, so a repeated id on the site can't break the primary key.
            unique = {entry["value"]: entry for entry in entries}.values()
            session.add_all(
                PunjabFilterOption(kind=kind, value=e["value"], label=e["label"], sort_order=i, refreshed_at=now)
                for i, e in enumerate(unique)
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    with _lock:
        _cache = None
    return sum(len(entries) for entries in options.values())


def label_for(field: str, value: object) -> str:
    """The human label for a dropdown value; the value itself when it isn't known."""
    text = str(value).strip()
    for entry in get_filter_options()["options"].get(field, []):
        if entry["value"] == text:
            return entry["label"]
    return text


def filter_labels(filters: dict) -> list[tuple[str, str]]:
    """(field, label) for every dropdown filter applied, in display order."""
    return [
        (field, label_for(field, filters[field]))
        for field in FIELD_NAMES
        if filters.get(field)
    ]


def compute_filters_hash(filters: PunjabFilters) -> str:
    encoded = json.dumps(filters.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def search_dates(filters: PunjabFilters, today: date | None = None) -> tuple[date, date]:
    """The first and last closing day a run covers, both included.

    The default starts today because the site's own default window holds only
    tenders that have already closed.
    """
    today = today or datetime.now(PKT).date()
    last = filters.closing_to or today + timedelta(days=DEFAULT_SEARCH_DAYS)
    first = filters.closing_from or min(today, last)
    return first, last


def site_date(day: date) -> str:
    """A date as the site's boxes hold it: dd/mm/yyyy."""
    return day.strftime("%d/%m/%Y")


def site_to_date(last_day: date) -> str:
    """The value for the To box. The site leaves out tenders closing on the To
    date itself, so covering a last day means sending the day after it."""
    return site_date(last_day + timedelta(days=1))
