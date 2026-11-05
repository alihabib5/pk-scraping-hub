"""Punjab request validation, search dates, and keeping portals apart."""

from datetime import date

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core import exports, run_manager
from app.scrapers.punjab import filters, router
from app.scrapers.punjab.schemas import PunjabFilters, PunjabOptions, PunjabScrapeRequest


@pytest.mark.parametrize(
    "payload",
    [
        {"filters": {"department": "1; DROP TABLE"}},
        {"filters": {"procurement_type": "abc"}},
        {"filters": {"procurement_type": "1234567"}},
        {"filters": {"unknown": "1"}},
        {"filters": {"closing_from": "not-a-date"}},
        {"filters": {"closing_from": "2026-12-01", "closing_to": "2026-11-01"}},
        {"options": {"closing_runway_days": 366}},
        {"options": {"delay_ms": 0}},
        {"filters": {"procurement_title": "5"}},
    ],
)
def test_bad_requests_are_refused(payload):
    with pytest.raises(ValidationError):
        PunjabScrapeRequest(**payload)


def test_auction_search_is_allowed_when_auctions_are_not_excluded():
    PunjabScrapeRequest(filters={"procurement_title": "5"}, options={"exclude_auctions": False})


def test_stored_filters_can_be_read_back():
    request = PunjabScrapeRequest(filters={"procurement_type": "3", "closing_to": "2026-12-31"})
    data = request.filters.model_dump(mode="json")
    assert data["closing_to"] == "2026-12-31"
    assert PunjabFilters(**data) == request.filters


def test_options_keep_the_meaning_the_console_expects():
    assert PunjabOptions().get_runway_days() == 7
    assert PunjabOptions(apply_closing_filter=False).get_runway_days() is None
    assert PunjabOptions(closing_runway_days=3).get_runway_days() == 3
    assert PunjabOptions().exclude_auctions is True


def test_default_search_is_live_tenders_only():
    first, last = filters.search_dates(PunjabFilters(), today=date(2026, 11, 5))
    assert first == date(2026, 11, 5)
    assert last == date(2028, 11, 4)


def test_user_dates_are_kept():
    wanted = PunjabFilters(closing_from="2026-11-10", closing_to="2026-11-20")
    assert filters.search_dates(wanted, today=date(2026, 11, 5)) == (date(2026, 11, 10), date(2026, 11, 20))


def test_a_past_end_date_never_gives_an_inverted_range():
    first, last = filters.search_dates(PunjabFilters(closing_to="2026-10-01"), today=date(2026, 11, 5))
    assert first <= last


def test_site_dates_are_day_first_and_the_last_day_is_covered():
    assert filters.site_date(date(2026, 11, 5)) == "05/11/2026"
    # The site leaves out the To date, so a last day of 31 Dec sends 1 Jan.
    assert filters.site_to_date(date(2026, 12, 31)) == "01/01/2027"


def test_refresh_refuses_a_ppra_run(monkeypatch):
    # Kept out of the database, or it would show up as a real run in the history.
    monkeypatch.setattr(run_manager, "_persist", lambda run: None)
    run = run_manager.create_run("ppra", {"filters": {}, "options": {}})
    with pytest.raises(HTTPException) as caught:
        router.refresh_scrape(run["run_id"])
    assert caught.value.status_code == 404


def test_refresh_refuses_an_unknown_run():
    with pytest.raises(HTTPException) as caught:
        router.refresh_scrape("no-such-run")
    assert caught.value.status_code == 404


def test_each_portal_names_its_own_file():
    ppra = {"scraper": "ppra", "run_id": "a", "started_at": "2026-10-17T06:50:03", "filters": {"category": "Works"}}
    punjab = {"scraper": "punjab", "run_id": "b", "started_at": "2026-10-17T06:50:03",
              "filters": {"closing_from": "2026-11-05", "closing_to": "2026-12-31"}}
    assert exports.excel_name(ppra) == "PPRA_Tenders(Works).xlsx"
    assert exports.excel_name(punjab) == "Punjab_Tenders(05-11-2026 to 31-12-2026).xlsx"


def test_a_run_with_no_portal_key_keeps_the_ppra_name():
    run = {"run_id": "a", "started_at": "2026-10-17T06:50:03", "filters": {"category": "Works"}}
    assert exports.excel_name(run) == "PPRA_Tenders(Works).xlsx"
