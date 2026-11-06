"""The Punjab Excel workbook: tenders with real dates, a live Days Left formula and
PDF links, plus a Run Summary sheet."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl.cell.cell import Cell
from openpyxl.styles import Font
from sqlalchemy import select

from app.config import settings
from app.core import excel_style
from app.core.filenames import sanitize_filename
from app.db import SessionLocal
from app.scrapers.punjab.filters import FIELD_NAMES, filter_labels
from app.scrapers.punjab.models import PunjabBid, PunjabRun
from app.scrapers.punjab.schemas import PunjabOptions

logger = logging.getLogger(__name__)

PKT = ZoneInfo("Asia/Karachi")

HEADERS = (
    "Tender ID", "Title", "Notice Type", "Procurement Type", "Department", "Status",
    "Published Date", "Closing Date", "Days Left", "Tender Notice", "Bidding Document",
    "Change", "Scraped At (PKT)",
)
COL_PUBLISHED, COL_CLOSING, COL_DAYS_LEFT, COL_NOTICE, COL_DOCUMENT, COL_SCRAPED = 7, 8, 9, 10, 11, 13
TEXT_COLUMNS = (1, 2, 3, 4, 5, 6, 12)
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def _as_text(cell: Cell) -> None:
    """Pin a cell to plain text. openpyxl turns any string starting with "=" into a
    formula, and these strings come from a remote site."""
    if isinstance(cell.value, str) and cell.value:
        cell.data_type = "s"
        if cell.value.startswith(FORMULA_STARTS):
            cell.quotePrefix = True


def _to_pkt_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(PKT).replace(tzinfo=None)


def _day(value: Any) -> str:
    """A `yyyy-mm-dd` filter date as `dd-mm-yyyy`."""
    text = str(value or "").strip()
    return "-".join(reversed(text.split("-"))) if text else ""


def excel_name(run: dict[str, Any]) -> str:
    """`Punjab_Tenders(01-11-2026 to 05-11-2026, Goods).xlsx`: the publish date range
    (closing dates on older runs), then any other filter. With no filters, named
    after the run's start in PKT."""
    filters = run.get("filters") or {}
    start, end = _day(filters.get("published_from")), _day(filters.get("published_to"))
    if not (start or end):
        start, end = _day(filters.get("closing_from")), _day(filters.get("closing_to"))
    parts: list[str] = []
    if start and end:
        parts.append(start if start == end else f"{start} to {end}")
    elif start:
        parts.append(f"from {start}")
    elif end:
        parts.append(f"to {end}")
    parts += [label for _, label in filter_labels(filters)]
    if parts:
        return sanitize_filename(f"Punjab_Tenders({', '.join(parts)})", max_length=150) + ".xlsx"

    try:
        started = datetime.fromisoformat(str(run.get("started_at")))
    except ValueError:
        started = datetime.now(timezone.utc)
    if started.tzinfo is None:
        started = started.astimezone()  # run_manager stamps local time
    return f"Punjab_Tenders_{started.astimezone(PKT).strftime('%Y-%m-%d_%H%M')}.xlsx"


def _write_tenders(sheet: Any, rows: list[PunjabBid], scraped_at: datetime) -> None:
    link_font = Font(color="0563C1", underline="single")
    sheet.append(list(HEADERS))
    for index, bid in enumerate(rows, start=2):
        sheet.append([
            excel_style.sanitize_cell(bid.tender_no),
            excel_style.sanitize_cell(bid.title),
            excel_style.sanitize_cell(bid.notice_type or ""),
            excel_style.sanitize_cell(bid.procurement_type or ""),
            excel_style.sanitize_cell(bid.department or ""),
            excel_style.sanitize_cell(bid.status or ""),
            bid.published_on,
            bid.closing_on,
            f"=MAX(0, H{index}-TODAY())" if bid.closing_on else None,
            "View PDF" if bid.notice_url else "",
            "View PDF" if bid.document_url else "",
            bid.change_status or "new",
            scraped_at,
        ])
        for column in TEXT_COLUMNS:
            _as_text(sheet.cell(row=index, column=column))
        sheet.cell(row=index, column=COL_PUBLISHED).number_format = "yyyy-mm-dd"
        sheet.cell(row=index, column=COL_CLOSING).number_format = "yyyy-mm-dd"
        sheet.cell(row=index, column=COL_DAYS_LEFT).number_format = "0"
        sheet.cell(row=index, column=COL_SCRAPED).number_format = "yyyy-mm-dd hh:mm"
        for column, url in ((COL_NOTICE, bid.notice_url), (COL_DOCUMENT, bid.document_url)):
            if url:  # only links that passed parsers.safe_pdf_url are ever stored
                cell = sheet.cell(row=index, column=column)
                cell.hyperlink = url
                cell.font = link_font
    excel_style.format_excel_headers(sheet, header_row=1, autofit=True, freeze=True, auto_filter=True)


def _summary_rows(run_id: str, run: PunjabRun | None, count: int, start: datetime) -> list[tuple[str, Any]]:
    finish = _to_pkt_naive(run.finished_at if run else None)
    filters = (run.filters if run else None) or {}
    options = PunjabOptions(**((run.options if run else None) or {}))

    duration = "—"
    if finish:
        minutes, seconds = divmod(int((finish - start).total_seconds()), 60)
        duration = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

    runway = options.get_runway_days()
    skipped = run.skipped_closing if run else 0
    unverified = run.kept_unverified if run else 0
    guard = (
        "Off — all tenders kept"
        if runway is None
        else f"{runway} days (skipped closing sooner: {skipped}, kept with unreadable date: {unverified})"
    )
    if runway is not None and run and run.closing_to and (run.closing_to - start.date()).days < runway:
        guard = f"Not applied — every tender in the closing date range closes within {runway} days"
    applied = " · ".join(f"{FIELD_NAMES[field]}: {label}" for field, label in filter_labels(filters))
    searched = (
        f"{run.closing_from or 'any'} to {run.closing_to or 'any'}"
        if run and (run.closing_from or run.closing_to)
        else "All"
    )
    published = (
        f"{filters.get('published_from') or 'any'} to {filters.get('published_to') or 'any'}"
        if filters.get("published_from") or filters.get("published_to")
        else "All"
    )
    auctions = f"Excluded ({run.skipped_auction if run else 0} removed)" if options.exclude_auctions else "Included"

    finished = not run or run.status == "completed"
    completeness = ((run.checkpoint if run else None) or {}).get("incomplete") or (
        "All tenders read" if finished else "Partial — the run did not finish"
    )

    return [
        ("Run ID", run_id),
        ("Status", (run.status if run else "completed").capitalize()),
        ("Completeness", completeness),
        ("Scrape Started (PKT)", start.strftime("%Y-%m-%d %H:%M:%S")),
        ("Scrape Finished (PKT)", finish.strftime("%Y-%m-%d %H:%M:%S") if finish else "—"),
        ("Duration", duration),
        ("Source Portal", settings.punjab_base_url.rstrip("/") + settings.punjab_search_path),
        ("Search Filters Applied", applied or "All live tenders"),
        ("Publish Date Filter", published),
        ("Closing Date Filter", searched),
        ("Closing Guard", guard),
        ("Sales/Auction/Disposal", auctions),
        ("Repeated Rows Skipped", run.skipped_repeat if run else 0),
        ("Total Tenders Kept", count),
        ("Total Reported by Portal", run.total_expected if run and run.total_expected else count),
        ("New Tenders", run.rows_new if run else count),
        ("Changed Tenders", run.rows_changed if run else 0),
        ("Time Zone Note", "All timestamps are in Pakistan Standard Time (PKT, UTC+5). The portal lists no closing time."),
    ]


def generate_excel(run_id: str, out_path: str | Path) -> int:
    """Build the workbook for a run from punjab_bids. Returns the tender count."""
    session = SessionLocal()
    try:
        run: PunjabRun | None = session.get(PunjabRun, run_id)
        rows = list(
            session.execute(
                select(PunjabBid)
                .where(PunjabBid.run_id == run_id)
                .order_by(PunjabBid.page_no, PunjabBid.position)
            ).scalars()
        )
    finally:
        session.close()

    start = _to_pkt_naive(run.started_at if run else None) or datetime.now(PKT).replace(tzinfo=None)
    workbook, sheet = excel_style.new_workbook("Punjab Tenders")
    workbook.properties.title = "Punjab Tenders"
    workbook.properties.creator = "PK-Hub"
    workbook.properties.created = start
    _write_tenders(sheet, rows, start)

    summary = workbook.create_sheet(title="Run Summary")
    summary.append(["Parameter", "Value"])
    for parameter, value in _summary_rows(run_id, run, len(rows), start):
        summary.append([parameter, excel_style.sanitize_cell(str(value))])
        _as_text(summary.cell(row=summary.max_row, column=2))
    excel_style.format_excel_headers(summary, header_row=1, autofit=True, freeze=True, auto_filter=False)

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(str(out_file))
    logger.info("[run %s] generated Punjab Excel with %d rows at %s", run_id, len(rows), out_file)
    return len(rows)
