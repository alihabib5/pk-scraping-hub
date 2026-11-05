"""Punjab parser tests, run against real pages saved from the site (hidden form
state and most of the department list removed to keep them small)."""

from pathlib import Path

import pytest

from app.core.closing_filter import days_until_close
from app.scrapers.punjab import parsers
from app.scrapers.punjab.parsers import is_auction

FIXTURES = Path(__file__).parent / "fixtures" / "punjab"
BASE = "https://eproc.punjab.gov.pk"


def page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_normal_page_totals_and_rows():
    html = page("page_first.html")
    info = parsers.parse_pager(html)
    assert (info.total_records, info.total_pages, info.current_page, info.no_records) == (944, 19, 1, False)
    records = parsers.parse_listing(html, BASE)
    assert len(records) == 50
    first = records[0]
    assert first["tender_no"].isdigit() and len(first["tender_no"]) == 6
    assert first["notice_url"].startswith(f"{BASE}/Tenders/")
    assert first["document_url"].startswith(f"{BASE}/BiddingDocuments/")
    assert first["closing_on"] and first["published_on"] and first["procurement_type"]
    assert first["rejected_links"] == 0


def test_last_page_reports_its_position():
    info = parsers.parse_pager(page("page_last.html"))
    assert (info.current_page, info.total_pages) == (19, 19)


def test_one_page_result_has_no_pager_so_rows_are_the_total():
    info = parsers.parse_pager(page("page_single.html"))
    assert (info.total_records, info.total_pages, info.current_page, info.no_records) == (21, 1, 1, False)


def test_empty_result():
    html = page("page_empty.html")
    parsers.check_columns(html)
    info = parsers.parse_pager(html)
    assert (info.total_records, info.no_records) == (0, True)
    assert parsers.parse_listing(html, BASE) == []


def test_every_fixture_has_the_expected_columns():
    for name in ("page_first.html", "page_last.html", "page_single.html"):
        parsers.check_columns(page(name))


def test_changed_columns_are_detected():
    with pytest.raises(parsers.SiteChanged):
        parsers.check_columns(page("page_first.html").replace("Close Date", "Closing"))
    with pytest.raises(parsers.SiteChanged):
        parsers.check_columns("<html><body>Service unavailable</body></html>")


def test_row_with_missing_cells_is_detected():
    html = '<table><tr class="rgRow"><td>only one</td></tr></table>'
    with pytest.raises(parsers.SiteChanged):
        parsers.parse_listing(html, BASE)


def test_ids_are_unique_on_a_page():
    records = parsers.parse_listing(page("page_first.html"), BASE)
    assert len({r["tender_no"] for r in records}) == len(records)


def test_tender_id_comes_from_the_pdf_name():
    url = f"{BASE}/Tenders/50485054/4949/0511202610103916431812258713.pdf"
    assert parsers.tender_id_from_links(url) == "258713"
    assert parsers.tender_id_from_links(None, url) == "258713"
    assert parsers.tender_id_from_links(None, None) is None


def test_a_longer_future_id_still_works():
    url = f"{BASE}/Tenders/50485054/4949/05112026101039164318121258713.pdf"
    assert parsers.tender_id_from_links(url) == "1258713"


def test_fallback_id_depends_on_content_only():
    one = parsers.fallback_id("Tender", "Dept", "2026-11-01", "2026-11-20")
    assert one.startswith("PB-")
    assert one == parsers.fallback_id("TENDER", "dept", "2026-11-01", "2026-11-20")
    assert one != parsers.fallback_id("Tender", "Dept", "2026-11-01", "2026-11-21")


@pytest.mark.parametrize("notice_type", ["Sales/Auction/Disposal", "  Sales/Auction/Disposal  "])
def test_the_auction_title_is_caught(notice_type):
    assert is_auction(notice_type)


@pytest.mark.parametrize("notice_type", ["Tender Notice", "Corrigendum", "Others", "", None])
def test_every_other_title_is_kept(notice_type):
    assert not is_auction(notice_type)


def test_every_row_of_the_auction_search_is_an_auction():
    records = parsers.parse_listing(page("page_single.html"), BASE)
    assert records and all(is_auction(r["notice_type"]) for r in records)


@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "https://evil.example/Tenders/1/2/0511202610103916431812258713.pdf",
        "//evil.example/Tenders/1/2/0511202610103916431812258713.pdf",
        "Tenders/../../secret/0511202610103916431812258713.pdf",
        "Tenders/50485054/4949/short.pdf",
        "Tenders/50485054/4949/0511202610103916431812258713.exe",
        "Other/50485054/4949/0511202610103916431812258713.pdf",
        "",
        None,
    ],
)
def test_unexpected_links_are_rejected(href):
    assert parsers.safe_pdf_url(href, BASE) is None


def test_a_bad_link_is_dropped_and_counted():
    html = page("page_first.html").replace('href="Tenders/', 'href="javascript:alert(1)//Tenders/', 1)
    first = parsers.parse_listing(html, BASE)[0]
    assert first["notice_url"] is None and first["rejected_links"] == 1


def test_dates_become_iso_so_they_are_not_read_month_first():
    assert parsers.to_iso_date("05 Nov 2026") == "2026-11-05"
    assert parsers.to_iso_date("nonsense") is None
    assert parsers.to_iso_date("") is None
    from datetime import date
    assert days_until_close("2026-11-05", today=date(2026, 11, 1)) == 4


def test_whitespace_is_normalised():
    assert parsers.clean_text("  Purchase   of\xa0Uniform \n") == "Purchase of Uniform"
    assert parsers.clean_text(None) == ""


def test_options_leave_out_all_and_junk_labels():
    html = """
    <select id="ctl00_ContentPlaceHolderSRIS_ddlDepartment">
      <option value="0">--- All ---</option><option value="4585">.</option>
      <option value="561">Accountant General, Punjab</option>
    </select>"""
    assert parsers.parse_options(html) == {
        "department": [{"value": "561", "label": "Accountant General, Punjab"}]
    }


def test_options_from_a_real_page():
    options = parsers.parse_options(page("page_first.html"))
    assert set(options) == set(parsers.SELECTS)
    assert {"value": "5", "label": "Sales/Auction/Disposal"} in options["procurement_title"]
    assert [o["label"] for o in options["procurement_type"]] == ["Work", "Services", "Goods"]


def test_hash_changes_when_a_visible_field_changes():
    base = {"title": "A", "closing_on": "2026-11-20", "notice_url": "x"}
    assert parsers.compute_content_hash(base) == parsers.compute_content_hash(dict(base))
    assert parsers.compute_content_hash(base) != parsers.compute_content_hash({**base, "closing_on": "2026-11-21"})
