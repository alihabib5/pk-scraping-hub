"""Punjab filters: the option lists, how a filter matches a row, and the filter hash.

The Active Tenders page has no search form, so a run reads every tender and these
filters are applied to each row. The option lists can't be read from that page:
they come from `punjab_filter_options`, or the checked-in `filter_options.json`.
"""

import hashlib
import json
import logging
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.db import SessionLocal
from app.scrapers.punjab.models import PunjabFilterOption
from app.scrapers.punjab.schemas import PunjabFilters

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).with_name("filter_options.json")
PKT = ZoneInfo("Asia/Karachi")

# PunjabFilters field -> the name shown in filenames and the Excel summary. Each
# dropdown field shares its name with the option `kind` it draws from.
FIELD_NAMES = {
    "procurement_type": "Type",
    "procurement_category": "Category",
    "procurement_title": "Title",
    "department": "Department",
}

# Dropdown field -> the scraped row key its label is compared with.
ROW_KEYS = {
    "procurement_type": "procurement_type",
    "procurement_title": "notice_type",
    "department": "department",
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


def wanted_labels(filters: PunjabFilters) -> dict[str, str]:
    """{row key: lowercase label the row must have} for each dropdown filter chosen."""
    return {
        key: label_for(field, getattr(filters, field)).lower()
        for field, key in ROW_KEYS.items()
        if getattr(filters, field)
    }


def compute_filters_hash(filters: PunjabFilters) -> str:
    encoded = json.dumps(filters.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
