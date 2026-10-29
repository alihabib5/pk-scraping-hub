"""Dates as the PPRA portal prints them, stored without shifting."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.scrapers.ppra.parsers import parse_total
from app.scrapers.ppra.repository import _safe_date, _safe_datetime

PKT = ZoneInfo("Asia/Karachi")


def test_closing_time_is_read_as_pakistan_time():
    # The portal shows PKT with no zone; it used to be stored as UTC, five hours late.
    assert _safe_datetime("Jan 07, 2027 09:30 AM") == datetime(2027, 1, 7, 9, 30, tzinfo=PKT)
    assert _safe_datetime("2026-11-19 19:30") == datetime(2026, 11, 19, 19, 30, tzinfo=PKT)


def test_date_only_and_unreadable_values():
    assert _safe_datetime("Jan 05, 2027") == datetime(2027, 1, 5, tzinfo=PKT)
    assert _safe_date("2026-10-16") == date(2026, 10, 16)
    for junk in ("", None, "TS1/25-26", "Feb 30, 2027 10:00"):
        assert _safe_datetime(junk) is None
        assert _safe_date(junk) is None


def test_parse_total_reads_counts():
    assert parse_total("<p>Showing 1 to 50 of 2,311 entries</p>") == (2311, 47)
    assert parse_total("<p>Showing 1 to 50 of 2,311 entries</p><p>Page 1 of 47</p>") == (2311, 47)
    # "of ," has no digits, so it no longer stops the search before the real count.
    assert parse_total("<p>Terms of , use</p><p>Showing 1 to 50 of 120 entries</p>") == (120, 3)
    assert parse_total("<p>nothing here, of course</p>") == (0, 1)


def test_is_karachi_matches_the_portals_spellings_only():
    from app.scrapers.ppra.parsers import is_karachi

    for city in ("Karachi", "Karachi.", " KARACHI ", "karachi"):
        assert is_karachi(city)
    for other in (None, "", "Lahore", "New Karachi Colony", "Rawalpindi."):
        assert not is_karachi(other)
