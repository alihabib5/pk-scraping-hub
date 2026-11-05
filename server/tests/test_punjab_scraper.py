"""The scraper's row rules and page checks, without a browser."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.scrapers.punjab.parsers import SiteChanged
from app.scrapers.punjab.schemas import PunjabFilters, PunjabOptions
from app.scrapers.punjab.scraper import PageFailed, PunjabScraper

FIXTURES = Path(__file__).parent / "fixtures" / "punjab"


def closes_in(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def row(tender_no: str, title: str = "Purchase of Uniform", notice_type: str = "Tender Notice",
        closing_on: str | None = None, rejected_links: int = 0) -> dict:
    return {"tender_no": tender_no, "title": title, "notice_type": notice_type,
            "closing_on": closing_on or closes_in(30), "rejected_links": rejected_links}


def scraper(**options) -> PunjabScraper:
    return PunjabScraper("test", PunjabFilters(), PunjabOptions(**options))


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


def test_the_expected_page_is_accepted():
    _, info = on_page("page_first.html")._read_page(1)
    assert info.total_pages == 19


def test_the_wrong_page_is_refused():
    with pytest.raises(PageFailed):
        on_page("page_first.html")._read_page(2)


def test_an_empty_first_page_is_a_real_result():
    assert on_page("page_empty.html")._read_page(1)[1].no_records


def test_an_empty_later_page_is_a_failure():
    with pytest.raises(PageFailed):
        on_page("page_empty.html")._read_page(2)


def test_a_changed_site_is_reported_as_such():
    with pytest.raises(SiteChanged):
        on_page("", html="<html><body>Service unavailable</body></html>")._read_page(1)
