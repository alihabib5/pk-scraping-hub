"""FastAPI router for the Punjab scraper. The routes match `/ppra`, so the
console's shared calls work for both portals."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core import jobs, run_manager
from app.db import get_session
from app.scrapers.punjab import filters as punjab_filters
from app.scrapers.punjab import repository
from app.scrapers.punjab.models import PunjabBid
from app.scrapers.punjab.schemas import PunjabFilters, PunjabOptions, PunjabScrapeRequest
from app.scrapers.punjab.scraper import execute_run

router = APIRouter(prefix="/punjab", tags=["punjab"])


def _launch(
    filters: PunjabFilters,
    options: PunjabOptions,
    search: str,
    live_preview: bool,
    parent_run_id: str | None = None,
) -> dict[str, Any]:
    """Register a run, record it in punjab_runs, and queue it on the worker pool."""
    filters_data = filters.model_dump(mode="json")
    options_data = options.model_dump(mode="json")
    filters_hash = punjab_filters.compute_filters_hash(filters)
    fields: dict[str, Any] = {
        "search": search,
        "filters": filters_data,
        "filters_hash": filters_hash,
        "options": options_data,
        "live_preview": live_preview,
        "total_expected": None,
        "total_pages": None,
        "current_page": 0,
        "rows_new": 0,
        "rows_changed": 0,
        "skipped_closing": 0,
        "kept_unverified": 0,
        "skipped_auction": 0,
        "skipped_repeat": 0,
    }
    if parent_run_id:
        fields["parent_run_id"] = parent_run_id
    run = run_manager.create_run("punjab", fields)

    repository.init_run_in_db(
        run["run_id"], filters_data, filters_hash, options_data, parent_run_id=parent_run_id
    )
    jobs.submit(run["run_id"], execute_run, run["run_id"], filters_data, options_data, parent_run_id=parent_run_id)
    return run


@router.post("/scrape")
def start_scrape(request: PunjabScrapeRequest) -> dict[str, Any]:
    """Start a Punjab scrape run."""
    filters = request.filters
    if filters.closing_to and filters.closing_to < datetime.now(punjab_filters.PKT).date():
        raise HTTPException(
            status_code=422,
            detail="Closing Date To is in the past. The Active Tenders page lists only open "
            "tenders, so choose a later date or leave the dates blank.",
        )
    labels = [label for _, label in punjab_filters.filter_labels(filters.model_dump(mode="json"))]
    search = ", ".join(labels) or "all live tenders"
    run = _launch(filters, request.options, search, request.live_preview)
    return {"run_id": run["run_id"], "search": search}


@router.post("/scrape/refresh/{run_id}")
def refresh_scrape(run_id: str) -> dict[str, Any]:
    """Re-run a previous Punjab scrape; tenders are marked new, changed or unchanged."""
    parent_run = run_manager.get_run(run_id)
    if not parent_run or parent_run.get("scraper") != "punjab":
        raise HTTPException(status_code=404, detail=f"Punjab run {run_id} not found")
    try:
        filters = PunjabFilters(**parent_run.get("filters", {}))
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="This run used a filter the Active Tenders page doesn't support. Start a new run instead.",
        ) from exc
    run = _launch(
        filters,
        PunjabOptions(**parent_run.get("options", {})),
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
    return {"runs": run_manager.list_runs(scraper="punjab")}


@router.get("/filters")
def get_filters(response: Response) -> dict[str, Any]:
    """The option lists behind the console's dropdowns."""
    response.headers["Cache-Control"] = "private, max-age=60"
    return punjab_filters.get_filter_options()


def _bid_dict(bid: PunjabBid) -> dict[str, Any]:
    return {
        "id": bid.id,
        "run_id": bid.run_id,
        "page_no": bid.page_no,
        "position": bid.position,
        "tender_no": bid.tender_no,
        "title": bid.title,
        "notice_type": bid.notice_type,
        "procurement_type": bid.procurement_type,
        "department": bid.department,
        "status": bid.status,
        "published_on": str(bid.published_on) if bid.published_on else None,
        "closing_on": str(bid.closing_on) if bid.closing_on else None,
        "notice_url": bid.notice_url,
        "document_url": bid.document_url,
        "change_status": bid.change_status,
        "scraped_at": str(bid.scraped_at) if bid.scraped_at else None,
    }


@router.get("/bids")
def list_bids(
    run_id: str | None = Query(None, description="Filter by run"),
    query: str = Query("", description="Search tender id / title / department"),
    after_id: int | None = Query(None, description="Cursor for live updates"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Tenders from punjab_bids: oldest-first with a cursor, newest-first without."""
    cursor = after_id is not None
    stmt = select(PunjabBid).order_by(PunjabBid.id.asc() if cursor else PunjabBid.id.desc())
    if run_id:
        stmt = stmt.where(PunjabBid.run_id == run_id)
    if cursor:
        stmt = stmt.where(PunjabBid.id > after_id)
    if query:
        like = f"%{query}%"
        stmt = stmt.where(
            or_(PunjabBid.title.ilike(like), PunjabBid.tender_no.ilike(like), PunjabBid.department.ilike(like))
        )
    rows = session.execute(stmt.limit(limit).offset(offset)).scalars().all()
    return {"bids": [_bid_dict(bid) for bid in rows], "count": len(rows)}
