"""PPRA search filters: the site's dropdown options, the run's filter hash, and
the portal search URL.

The site's dropdowns (sector, organization, country, …) take the site's own
numeric ids. A name is either ignored or matches nothing, so the console sends
ids and everything shown to a person (filename, Excel summary) turns them back
into labels through `label_for`.

The option lists live in `ppra_filter_options`. They are refreshed from the live
page whenever a scrape loads it, and on demand (`refresh_from_site`). Until the
first refresh, the checked-in `filter_options.json` seed is served, so the
dropdowns are never empty.
"""

import hashlib
import json
import logging
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin

from sqlalchemy import delete, func, select

from app.config import settings
from app.db import SessionLocal
from app.scrapers.ppra.models import PpraFilterOption
from app.scrapers.ppra.parsers import parse_options
from app.scrapers.ppra.schemas import PpraFilters

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).with_name("filter_options.json")

# PpraFilters field -> the site's query parameter, in the order they appear in
# filenames and the Excel summary. Dropdown fields share their name with the
# option `kind` they draw from.
FIELD_PARAMS = {
    "category": "procurement_category",
    "tender_type": "tender_type",
    "tender_method": "tender_method",
    "sector": "sector",
    "nature": "tender_nature",
    "status": "status",
    "organization": "organization",
    "country": "country",
    "city": "city",
    "keyword": "keyword",
    "tender_number": "tender_no",
    "closing_date": "closing_date",
    "advertise_from": "advertise_date_from",
    "advertise_to": "advertise_date_to",
}
DROPDOWN_FIELDS = {
    "category", "tender_type", "tender_method", "sector", "nature", "status", "organization", "country",
}

# What each filter is called in the Excel summary.
FIELD_NAMES = {
    "category": "Category",
    "tender_type": "Tender Type",
    "tender_method": "Method",
    "sector": "Sector",
    "nature": "Nature",
    "status": "Status",
    "organization": "Organization",
    "country": "Country",
    "city": "City",
    "keyword": "Keyword",
    "tender_number": "Tender No",
}

_lock = threading.Lock()
_cache: dict | None = None  # {"options": {kind: [...]}, "refreshed_at": str | None, "source": str}


def _is_set(value: object) -> bool:
    return value is not None and str(value).strip() != "" and str(value).strip().upper() != "ALL"


# -- the option catalog --------------------------------------------------------


def _load() -> dict:
    """The option lists from the DB, or the seed file when the DB has none."""
    try:
        session = SessionLocal()
        try:
            rows = session.execute(
                select(PpraFilterOption).order_by(PpraFilterOption.kind, PpraFilterOption.sort_order)
            ).scalars().all()
            refreshed = session.execute(select(func.max(PpraFilterOption.refreshed_at))).scalar()
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
        logger.exception("could not read cached PPRA filter options")
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
    """Replace the cached lists for each kind present. Returns the option count.

    Replaced rather than merged, so an organization the site has dropped stops
    being offered.
    """
    global _cache
    if not options:
        return 0
    now = datetime.now(timezone.utc)
    session = SessionLocal()
    try:
        for kind, entries in options.items():
            session.execute(delete(PpraFilterOption).where(PpraFilterOption.kind == kind))
            session.add_all(
                PpraFilterOption(kind=kind, value=e["value"], label=e["label"], sort_order=i, refreshed_at=now)
                for i, e in enumerate(entries)
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


def refresh_from_site() -> int:
    """Read the dropdowns from the live active-tenders page and cache them.

    A plain HTTP GET is enough: the options are in the page HTML.
    """
    url = urljoin(settings.ppra_base_url, settings.ppra_active_tenders_path)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PK-Hub"})
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", "replace")
    options = parse_options(html)
    if not options:
        raise ValueError("the PPRA page had no filter dropdowns — has the site changed?")
    return save_filter_options(options)


def _options(kind: str) -> list[dict[str, str]]:
    return get_filter_options()["options"].get(kind, [])


def resolve(field: str, value: object) -> str:
    """The site id for a dropdown filter. Accepts an id, or a label (runs saved
    before the console sent ids) — matched case-insensitively."""
    text = str(value).strip()
    if field not in DROPDOWN_FIELDS:
        return text
    entries = _options(FIELD_PARAMS[field])
    if any(e["value"] == text for e in entries):
        return text
    wanted = text.lower()
    for e in entries:
        label = e["label"].lower()
        # "Pre-qualification Notice" also matches "Pre-qualification Notice (PQ)".
        if label == wanted or label.split(" (")[0] == wanted:
            return e["value"]
    return text


def label_for(field: str, value: object) -> str:
    """The human label for a filter value; the value itself when it isn't a known id."""
    text = str(value).strip()
    if field in DROPDOWN_FIELDS:
        for e in _options(FIELD_PARAMS[field]):
            if e["value"] == text:
                return e["label"]
    return text


def filter_labels(filters: dict) -> list[tuple[str, str]]:
    """(field, label) for every applied filter except the dates, in display order.

    Country "Pakistan" is left out: every PPRA tender is in Pakistan, so it adds
    nothing to a filename.
    """
    out = []
    for field in FIELD_NAMES:
        value = filters.get(field)
        if not _is_set(value):
            continue
        label = label_for(field, value)
        if field == "country" and label.lower() == "pakistan":
            continue
        out.append((field, label))
    return out


# -- the run -----------------------------------------------------------------


def compute_filters_hash(filters: PpraFilters) -> str:
    """Compute sha256 hash of canonicalized filter values."""
    dump = filters.model_dump()
    canon = {k: ("" if v is None or v == "ALL" else str(v).strip().lower()) for k, v in dump.items()}
    encoded = json.dumps(canon, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_search_url(filters: PpraFilters, base_url: str, page: int = 1) -> str:
    """The GET URL the site's own search form would produce for these filters."""
    params: dict[str, str] = {}
    if page > 1:
        params["page"] = str(page)
    for field, param in FIELD_PARAMS.items():
        value = getattr(filters, field)
        if _is_set(value):
            params[param] = resolve(field, value)
    qs = urlencode(params)
    return f"{base_url}?{qs}" if qs else base_url
