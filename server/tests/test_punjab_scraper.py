"""The scraper's row rules and page checks, without a browser."""

from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.core import run_manager
from app.scrapers.punjab import filters as punjab_filters
from app.scrapers.punjab.parsers import PageInfo, SiteChanged
from app.scrapers.punjab.schemas import PunjabFilters, PunjabOptions
from app.scrapers.punjab import scraper as module
from app.scrapers.punjab.scraper import PageFailed, PunjabScraper

FIXTURES = Path(__file__).parent / "fixtures" / "punjab"


def closes_in(days: int) -> str:
    return (datetime.now(ZoneInfo("Asia/Karachi")).date() + timedelta(days=days)).isoformat()


def row(tender_no: str, title: str = "Purchase of Uniform", notice_type: str = "Tender Notice",
        closing_on: str | None = None, rejected_links: int = 0) -> dict:
    return {"tender_no": tender_no, "title": title, "notice_type": notice_type,
            "closing_on": closing_on or closes_in(30), "rejected_links": rejected_links}


def scraper(**options) -> PunjabScraper:
    return PunjabScraper("test", PunjabFilters(), PunjabOptions(**options))


def filtered(options: dict | None = None, **chosen) -> PunjabScraper:
    return PunjabScraper("test", PunjabFilters(**chosen), PunjabOptions(**(options or {})))


@pytest.fixture
def labels(monkeypatch):
    known = {"3": "Goods", "9": "Corrigendum", "561": "Accountant General, Punjab"}
    monkeypatch.setattr(punjab_filters, "label_for", lambda field, value: known[str(value)])


@pytest.fixture
def warnings(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(run_manager, "add_warning", lambda run_id, text: seen.append(text))
    return seen


def on_page(name: str, html: str | None = None) -> PunjabScraper:
    instance = scraper()
    instance.driver = SimpleNamespace(page_source=html or (FIXTURES / name).read_text(encoding="utf-8"))
    return instance


def test_a_repeated_row_is_skipped_and_counted():
    instance = scraper()
    assert len(instance._keep([row("1")])) == 1
    assert instance._keep([row("1"), row("2")]) == [row("2")]
    assert instance._skipped_repeat == 1


def test_only_the_auction_title_is_removed_by_default():
    instance = scraper()
    kept = instance._keep([
        row("1", notice_type="Sales/Auction/Disposal"),
        row("2", title="Auction of Cotton Crop"),
        row("3", title="Rental Crane Service"),
    ])
    assert [r["tender_no"] for r in kept] == ["2", "3"]
    assert instance._skipped_auction == 1


def test_auctions_stay_when_exclusion_is_off():
    instance = scraper(exclude_auctions=False)
    assert len(instance._keep([row("1", notice_type="Sales/Auction/Disposal")])) == 1
    assert instance._skipped_auction == 0


def test_closing_guard_keeps_the_boundary_and_counts_the_rest():
    instance = scraper(closing_runway_days=7)
    kept = instance._keep([row("1", closing_on=closes_in(6)), row("2", closing_on=closes_in(7))])
    assert [r["tender_no"] for r in kept] == ["2"]
    assert instance._skipped_closing == 1


def test_guard_off_keeps_tenders_closing_soon():
    assert len(scraper(apply_closing_filter=False)._keep([row("1", closing_on=closes_in(0))])) == 1


def test_an_unreadable_close_date_is_kept_and_counted():
    instance = scraper()
    record = row("1")
    record["closing_on"] = None
    assert instance._keep([record]) == [record]
    assert instance._kept_unverified == 1


def test_rejected_links_are_counted_even_on_dropped_rows():
    instance = scraper()
    instance._keep([row("1", notice_type="Sales/Auction/Disposal", rejected_links=2)])
    assert instance._rejected_links == 2


def test_valid_tenders_survive_the_auction_exclusion():
    instance = scraper(apply_closing_filter=False)
    kept = instance._keep([
        row("1", notice_type="Sales/Auction/Disposal"),
        row("2", notice_type="Tender Notice"),
        row("3", notice_type="Corrigendum"),
        row("4", notice_type="Request for Proposal"),
    ])
    assert [r["tender_no"] for r in kept] == ["2", "3", "4"]


def test_dropdown_filters_match_the_row_text(labels):
    instance = filtered(procurement_type="3", department="561", options={"apply_closing_filter": False})
    wanted = {**row("1"), "procurement_type": "GOODS", "department": "Accountant General, Punjab"}
    wrong_type = {**row("2"), "procurement_type": "Work", "department": "Accountant General, Punjab"}
    wrong_department = {**row("3"), "procurement_type": "Goods", "department": "Other"}
    assert instance._keep([wanted, wrong_type, wrong_department]) == [wanted]
    assert instance._skipped_filter == 2


def test_the_title_filter_reads_the_notice_type(labels):
    instance = filtered(procurement_title="9", options={"apply_closing_filter": False})
    assert [r["tender_no"] for r in instance._keep([row("1"), row("2", notice_type="Corrigendum")])] == ["2"]


def test_closing_dates_include_both_ends():
    instance = filtered(closing_from=closes_in(10), closing_to=closes_in(12), options={"apply_closing_filter": False})
    records = [row(str(days), closing_on=closes_in(days)) for days in (9, 10, 12, 13)]
    assert [r["tender_no"] for r in instance._keep(records)] == ["10", "12"]
    assert instance._skipped_filter == 2


def test_publish_dates_include_both_ends():
    instance = filtered(published_from="2026-11-01", published_to="2026-11-05", options={"apply_closing_filter": False})
    records = [
        {**row(day), "published_on": f"2026-{day}"}
        for day in ("10-31", "11-01", "11-05", "11-06")
    ]
    assert [r["tender_no"] for r in instance._keep(records)] == ["11-01", "11-05"]
    assert instance._skipped_filter == 2


def test_a_publish_range_can_be_open_ended():
    instance = filtered(published_from="2026-11-05", options={"apply_closing_filter": False})
    records = [{**row("old"), "published_on": "2026-11-04"}, {**row("new"), "published_on": "2027-01-01"}]
    assert [r["tender_no"] for r in instance._keep(records)] == ["new"]


def test_a_range_the_minimum_can_never_meet_still_returns_its_tenders(warnings):
    instance = filtered(closing_to=closes_in(5), options={"closing_runway_days": 9})
    assert len(instance._keep([row("1", closing_on=closes_in(3))])) == 1
    instance.rows_scraped_total = 1
    instance._finish_checks(PageInfo(1, 1, 1, False), True)
    assert any("was not applied" in text for text in warnings)


def test_the_minimum_still_applies_to_a_range_that_can_meet_it():
    instance = filtered(closing_to=closes_in(30), options={"closing_runway_days": 9})
    kept = instance._keep([row("1", closing_on=closes_in(3)), row("2", closing_on=closes_in(20))])
    assert [r["tender_no"] for r in kept] == ["2"]
    assert instance._skipped_closing == 1


def test_a_run_that_saves_nothing_says_why(warnings):
    instance = scraper(closing_runway_days=9)
    instance._keep([row("1", notice_type="Sales/Auction/Disposal"), row("2", closing_on=closes_in(1))])
    instance._finish_checks(PageInfo(2, 1, 1, False), True)
    assert warnings == [
        "The site listed 2 active tenders but none were saved: "
        "1 Sales/Auction/Disposal, 0 not matching your filters, 1 closing too soon."
    ]


def test_the_expected_page_is_accepted():
    _, info = on_page("page_first.html")._read_page(1)
    assert info.total_pages == 9


def test_the_wrong_page_is_refused():
    with pytest.raises(PageFailed):
        on_page("page_first.html")._read_page(2)


def test_an_empty_first_page_is_a_bad_load_not_a_result():
    with pytest.raises(PageFailed):
        on_page("page_empty.html")._read_page(1)


def test_an_empty_later_page_is_a_failure():
    with pytest.raises(PageFailed):
        on_page("page_empty.html")._read_page(2)


def test_a_changed_site_is_reported_as_such():
    with pytest.raises(SiteChanged):
        on_page("", html="<html><body>Service unavailable</body></html>")._read_page(1)


def test_one_publish_day_is_typed_into_the_site_filter_but_a_range_is_not():
    assert filtered(published_from="2026-11-06", published_to="2026-11-06").publish_text == "06 Nov 2026"
    assert filtered(published_from="2026-11-05", published_to="2026-11-06").publish_text is None
    assert filtered(published_from="2026-11-06").publish_text is None
    assert scraper().publish_text is None


def test_closing_days_are_applied_before_the_auction_exclusion():
    instance = scraper()
    kept = instance._keep([
        row("1", notice_type="Sales/Auction/Disposal", closing_on=closes_in(1)),   # too soon: a closing skip
        row("2", notice_type="Sales/Auction/Disposal", closing_on=closes_in(30)),  # fine, but an auction
    ])
    assert kept == []
    assert (instance._skipped_closing, instance._skipped_auction) == (1, 1)


def test_the_site_filter_must_be_the_one_applied(monkeypatch):
    instance = filtered(published_from="2026-11-06", published_to="2026-11-06")
    instance.driver = SimpleNamespace(page_source=(FIXTURES / "page_first.html").read_text(encoding="utf-8"))
    monkeypatch.setattr(module, "publish_filter_text", lambda html: "")
    with pytest.raises(PageFailed):
        instance._read_page(1)
    monkeypatch.setattr(module, "publish_filter_text", lambda html: "06 Nov 2026")
    _, info = instance._read_page(1)
    assert info.total_pages == 9


def test_a_day_with_no_tenders_is_an_empty_result_not_a_bad_load(monkeypatch):
    instance = filtered(published_from="2026-11-07", published_to="2026-11-07")
    instance.driver = SimpleNamespace(page_source=(FIXTURES / "page_empty.html").read_text(encoding="utf-8"))
    monkeypatch.setattr(module, "publish_filter_text", lambda html: "07 Nov 2026")
    _, info = instance._read_page(1)
    assert info.no_records
    with pytest.raises(PageFailed):  # a later page can never be empty
        instance._read_page(2)
