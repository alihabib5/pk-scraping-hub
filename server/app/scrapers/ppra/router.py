"""FastAPI router for the PPRA scraper."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core import jobs, run_manager
from app.db import get_session
from app.scrapers.ppra import filters as ppra_filters
from app.scrapers.ppra import repository
from app.scrapers.ppra.models import PpraBid
from app.scrapers.ppra.schemas import PpraFilters, PpraOptions, PpraScrapeRequest
from app.scrapers.ppra.scraper import execute_run

router = APIRouter(prefix="/ppra", tags=["ppra"])


def _launch(
    filters: PpraFilters,
    options: PpraOptions,
    search: str,
    live_preview: bool,
    parent_run_id: str | None = None,
) -> dict[str, Any]:
    """Register a run, record it in ppra_runs, and queue it on the worker pool."""
    filters_hash = ppra_filters.compute_filters_hash(filters)
    fields: dict[str, Any] = {
        "search": search,
        "filters": filters.model_dump(),
        "filters_hash": filters_hash,
        "options": options.model_dump(),
        "live_preview": live_preview,
        "total_expected": None,
        "total_pages": None,
        "current_page": 0,
        "rows_new": 0,
        "rows_changed": 0,
        "skipped_closing": 0,
        "kept_unverified": 0,
    }
    if parent_run_id:
        fields["parent_run_id"] = parent_run_id
    run = run_manager.create_run("ppra", fields)

    repository.init_run_in_db(
        run["run_id"], filters.model_dump(), filters_hash, options.model_dump(),
        parent_run_id=parent_run_id,
    )
    jobs.submit(
        run["run_id"], execute_run, run["run_id"], filters.model_dump(), options.model_dump(),
        parent_run_id=parent_run_id,
    )
    return run


@router.post("/scrape")
def start_scrape(request: PpraScrapeRequest) -> dict[str, Any]:
    """Start an active PPRA tenders scrape run."""
    filters = request.filters
    labels = [label for _, label in ppra_filters.filter_labels(filters.model_dump())]
    search = ", ".join(labels) or "all active tenders"
    run = _launch(filters, request.options, search, request.live_preview)
    return {"run_id": run["run_id"], "search": search}


@router.post("/scrape/refresh/{run_id}")
def refresh_scrape(run_id: str) -> dict[str, Any]:
    """Re-run a previous scrape's filters; its tenders are marked new / changed /
    unchanged against that run."""
    parent_run = run_manager.get_run(run_id)
    if not parent_run:
        raise HTTPException(status_code=404, detail=f"Parent run {run_id} not found")
    run = _launch(
        PpraFilters(**parent_run.get("filters", {})),
        PpraOptions(**parent_run.get("options", {})),
        f"Refresh of {run_id}",
        parent_run.get("live_preview", False),
        parent_run_id=run_id,
    )
    return {"run_id": run["run_id"], "parent_run_id": run_id}


@router.get("/scrape/status/{run_id}")
def scrape_status(run_id: str) -> dict[str, Any]:
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
    return run


@router.get("/scrape/runs")
def list_runs() -> dict[str, Any]:
    return {"runs": run_manager.list_runs(scraper="ppra")}


@router.get("/filters")
def get_filters() -> dict[str, Any]:
    """Every dropdown on the PPRA search form, as {kind: [{value, label}]}, plus
    when the lists were last read from the site ("seed" until the first read)."""
    return ppra_filters.get_filter_options()


@router.post("/filters/refresh")
def refresh_filters() -> dict[str, Any]:
    """Re-read the dropdowns from the live site now."""
    try:
        ppra_filters.refresh_from_site()
    except Exception as exc:  # noqa: BLE001 — report the cause instead of a bare 500
        raise HTTPException(status_code=502, detail=f"Could not read the PPRA site: {exc}") from exc
    return ppra_filters.get_filter_options()


@router.get("/bids")
def list_bids(
    run_id: str | None = Query(None, description="Filter by run"),
    query: str = Query("", description="Search tender number / title / organization"),
    after_id: int | None = Query(None, description="Cursor for live updates"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Query scraped tenders from ppra_bids."""
    # With a cursor (including 0, "from the start") rows come oldest-first so a
    # client can page forward without gaps; without one, newest-first.
    cursor = after_id is not None
    stmt = select(PpraBid).order_by(PpraBid.id.asc() if cursor else PpraBid.id.desc())

    if run_id:
        stmt = stmt.where(PpraBid.run_id == run_id)
    if cursor:
        stmt = stmt.where(PpraBid.id > after_id)
    if query:
        like = f"%{query}%"
        stmt = stmt.where(
            or_(
                PpraBid.title.ilike(like),
                PpraBid.tender_no.ilike(like),
                PpraBid.organization.ilike(like),
                PpraBid.city.ilike(like),
            )
        )

    rows = session.execute(stmt.limit(limit).offset(offset)).scalars().all()

    def _bid_dict(b: PpraBid) -> dict[str, Any]:
        return {
            "id": b.id,
            "run_id": b.run_id,
            "page_no": b.page_no,
            "position": b.position,
            "tender_no": b.tender_no,
            "title": b.title,
            "description": b.description,
            "sector": b.sector,
            "tender_ref_no": b.tender_ref_no,
            "tender_type": b.tender_type,
            "category": b.category,
            "nature": b.nature,
            "organization": b.organization,
            "department": b.department,
            "city": b.city,
            "country": b.country,
            "status": b.status,
            "advertised_on": str(b.advertised_on) if b.advertised_on else None,
            "closing_at": str(b.closing_at) if b.closing_at else None,
            "detail_url": b.detail_url,
            "invoice_url": b.invoice_url,
            "change_status": b.change_status,
            "scraped_at": str(b.scraped_at) if b.scraped_at else None,
        }

    return {"bids": [_bid_dict(b) for b in rows], "count": len(rows)}
