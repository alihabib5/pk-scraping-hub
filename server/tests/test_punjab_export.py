"""Punjab workbook and storage tests. These use the database and remove their own rows."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import delete

from app.core import exports
from app.db import Base, SessionLocal, engine
from app.scrapers.punjab import export, repository
from app.scrapers.punjab.models import PunjabBid, PunjabRun
from app.scrapers.punjab.parsers import compute_content_hash

RUN_ID = "test_punjab_run"
NOTICE = "https://eproc.punjab.gov.pk/Tenders/50485054/4949/0511202610103916431812258713.pdf"
DOCUMENT = "https://eproc.punjab.gov.pk/BiddingDocuments/50485054/4949/0511202610103938566723258713.pdf"


def record(tender_no: str, title: str, **extra) -> dict:
    data = {
        "position": 1, "tender_no": tender_no, "title": title, "notice_type": "Tender Notice",
        "procurement_type": "Goods", "department": "The Bank of Punjab", "status": None,
        "published_on": "2026-11-01", "closing_on": "2026-11-20",
        "notice_url": NOTICE, "document_url": DOCUMENT, "raw_data": {"columns": []},
        **extra,
    }
    data["content_hash"] = compute_content_hash(data)
    return data


def clean() -> None:
    session = SessionLocal()
    session.execute(delete(PunjabRun).where(PunjabRun.run_id.like(f"{RUN_ID}%")))
    session.commit()
    session.close()


@pytest.fixture(autouse=True)
def run_row():
    Base.metadata.create_all(bind=engine)
    clean()
    repository.init_run_in_db(RUN_ID, {"procurement_type": "3"}, "hash", {"exclude_auctions": True})
    repository.update_run_progress(
        RUN_ID, status="completed", finished_at=datetime.now(timezone.utc),
        closing_from=date(2026, 11, 5), closing_to=date(2028, 11, 4),
        skipped_auction=25, skipped_closing=360, skipped_repeat=2, total_expected=934,
    )
    yield
    clean()


def build(tmp_path: Path):
    out = tmp_path / "punjab.xlsx"
    count = export.generate_excel(RUN_ID, out)
    return count, openpyxl.load_workbook(out)


def test_workbook_layout_dates_formula_and_links(tmp_path):
    repository.upsert_bids(RUN_ID, 1, [record("258713", "Purchase of Uniform")])
    count, book = build(tmp_path)
    assert count == 1 and book.sheetnames == ["Punjab Tenders", "Run Summary"]
    sheet = book["Punjab Tenders"]
    assert [c.value for c in sheet[1]] == list(export.HEADERS)
    row = sheet[2]
    assert row[0].value == "258713" and row[1].value == "Purchase of Uniform"
    assert row[6].value.date() == date(2026, 11, 1) and row[7].value.date() == date(2026, 11, 20)
    assert row[6].number_format == row[7].number_format == "dd mmm yyyy"  # 20 Nov 2026, as the site prints it
    assert row[8].value == "=MAX(0, H2-TODAY())"
    assert row[9].hyperlink.target == NOTICE and row[10].hyperlink.target == DOCUMENT


def test_scraped_text_can_never_become_a_formula(tmp_path):
    hostile = '=HYPERLINK("http://example.com","x")'
    repository.upsert_bids(RUN_ID, 1, [record("1", hostile, department="+cmd", status="@sum")])
    _, book = build(tmp_path)
    row = book["Punjab Tenders"][2]
    assert row[1].value == hostile and row[1].data_type == "s" and row[1].quotePrefix
    assert row[4].data_type == "s" and row[5].data_type == "s"
    assert row[8].data_type == "f"  # our own Days Left formula stays a formula


def test_control_characters_do_not_break_the_workbook(tmp_path):
    repository.upsert_bids(RUN_ID, 1, [record("1", "Bad\x01Title")])
    _, book = build(tmp_path)
    assert book["Punjab Tenders"]["B2"].value == "BadTitle"


def test_missing_links_and_dates_stay_empty(tmp_path):
    repository.upsert_bids(RUN_ID, 1, [record("1", "A", notice_url=None, document_url=None, closing_on=None)])
    _, book = build(tmp_path)
    row = book["Punjab Tenders"][2]
    assert row[7].value is None and row[8].value is None
    assert row[9].hyperlink is None and not row[9].value


def test_summary_reports_what_was_removed(tmp_path):
    repository.upsert_bids(RUN_ID, 1, [record("1", "A")])
    _, book = build(tmp_path)
    summary = {row[0].value: row[1].value for row in book["Run Summary"].iter_rows(min_row=2)}
    assert summary["Sales/Auction/Disposal"] == "Excluded (25 removed)"
    assert "skipped closing sooner: 360" in summary["Closing Guard"]
    assert summary["Repeated Rows Skipped"] == "2"
    assert summary["Total Reported by Portal"] == "934"
    assert summary["Closing Date Filter"] == "2026-11-05 to 2028-11-04"


def test_summary_shows_a_finished_run_as_complete(tmp_path):
    repository.upsert_bids(RUN_ID, 1, [record("1", "A")])
    _, book = build(tmp_path)
    summary = {row[0].value: row[1].value for row in book["Run Summary"].iter_rows(min_row=2)}
    assert summary["Completeness"] == "All tenders read"


def test_summary_shows_why_a_run_is_incomplete(tmp_path):
    repository.update_run_progress(RUN_ID, checkpoint={"incomplete": "Stopped at page 3 of 9"})
    repository.upsert_bids(RUN_ID, 1, [record("1", "A")])
    _, book = build(tmp_path)
    summary = {row[0].value: row[1].value for row in book["Run Summary"].iter_rows(min_row=2)}
    assert summary["Completeness"] == "Stopped at page 3 of 9"


def test_summary_says_when_the_minimum_was_not_applied(tmp_path):
    repository.update_run_progress(RUN_ID, closing_to=date.today() + timedelta(days=2))
    repository.upsert_bids(RUN_ID, 1, [record("1", "A")])
    _, book = build(tmp_path)
    summary = {row[0].value: row[1].value for row in book["Run Summary"].iter_rows(min_row=2)}
    assert summary["Closing Guard"].startswith("Not applied")


def test_shared_download_path_builds_the_punjab_workbook():
    repository.upsert_bids(RUN_ID, 1, [record("1", "A")])
    run = {"scraper": "punjab", "run_id": RUN_ID, "started_at": "2026-11-05T10:00:00", "filters": {}}
    data, name = exports.excel_bytes(run)
    assert name.startswith("Punjab_Tenders_") and data[:2] == b"PK"


def test_refresh_marks_new_changed_and_unchanged():
    parent = {"same": compute_content_hash(record("same", "A")), "moved": "old-hash"}
    counts = repository.upsert_bids(
        RUN_ID, 1, [record("same", "A"), record("moved", "B"), record("fresh", "C")], parent
    )
    assert counts == (1, 1, 1)
    session = SessionLocal()
    stored = {b.tender_no: b.change_status for b in session.query(PunjabBid).filter_by(run_id=RUN_ID)}
    session.close()
    assert stored == {"same": "unchanged", "moved": "changed", "fresh": "new"}
