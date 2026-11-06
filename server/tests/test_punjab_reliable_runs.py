"""A run must return every tender or say that it didn't, whatever goes wrong on the way."""

import pytest
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from urllib3.exceptions import MaxRetryError

from app.core import run_manager
from app.scrapers.punjab import repository, scraper as module
from app.scrapers.punjab.parsers import PageInfo, SiteChanged
from app.scrapers.punjab.schemas import PunjabFilters, PunjabOptions
from app.scrapers.punjab.scraper import PageFailed, PunjabScraper


def rows(*ids):
    return [{"tender_no": i, "title": "T", "notice_type": "Tender Notice", "closing_on": "2099-01-01",
             "rejected_links": 0} for i in ids]


def info(total, pages, current):
    return PageInfo(total, pages, current, False)


@pytest.fixture
def harness(monkeypatch):
    """A scraper with no browser or database. Pages are lists of rows, and every
    call that would touch Chrome is recorded."""
    instance = PunjabScraper("test", PunjabFilters(), PunjabOptions(apply_closing_filter=False))
    instance.calls = []
    instance.warnings = []
    instance.saved = []
    instance.progress = {}
    monkeypatch.setattr(run_manager, "update_run", lambda *a, **k: None)
    monkeypatch.setattr(run_manager, "add_warning", lambda run_id, text: instance.warnings.append(text))
    monkeypatch.setattr(run_manager, "is_stop_requested", lambda run_id: False)
    monkeypatch.setattr(run_manager, "is_paused", lambda run_id: False)
    monkeypatch.setattr(repository, "update_run_progress", lambda run_id, **k: instance.progress.update(k))
    monkeypatch.setattr(repository, "append_to_mirror", lambda *a: None)
    monkeypatch.setattr(
        repository, "upsert_bids",
        lambda run_id, page, kept, hashes: (instance.saved.extend(r["tender_no"] for r in kept), (len(kept), 0, 0))[1],
    )
    monkeypatch.setattr(module, "parse_listing", lambda html, base: html)
    monkeypatch.setattr(instance, "polite_delay", lambda: None)
    monkeypatch.setattr(instance, "start_driver", lambda: instance.calls.append("start"))
    monkeypatch.setattr(instance, "stop_driver", lambda: instance.calls.append("stop"))
    monkeypatch.setattr(instance, "_open_list", lambda: instance.calls.append("open"))
    monkeypatch.setattr(instance, "_jump_to", lambda page: instance.calls.append(f"jump {page}"))
    return instance


def pages(instance, monkeypatch, *script):
    """`_read_page` returns each scripted page in turn, or raises it if it's an error."""
    queue = list(script)

    def read(expected):
        step = queue.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    monkeypatch.setattr(instance, "_read_page", read)
    monkeypatch.setattr(instance, "_post", lambda action: None)
    instance.driver = type("Driver", (), {"find_element": lambda self, *a: type("E", (), {"click": None})()})()


def test_an_empty_list_fails_the_run_instead_of_completing_with_zero(harness, monkeypatch):
    empty = PageFailed("the site showed no tenders on page 1")
    pages(harness, monkeypatch, empty, empty)
    with pytest.raises(PageFailed):
        harness._open_first_page()
    assert harness.calls.count("open") == 2


def test_an_empty_list_that_loads_on_the_second_try_is_read(harness, monkeypatch):
    good = (rows("1"), info(1, 1, 1))
    pages(harness, monkeypatch, PageFailed("empty"), good)
    assert harness._open_first_page() == good


def test_a_dead_browser_is_restarted_and_the_page_retried(harness, monkeypatch):
    good = (rows("2"), info(2, 2, 2))
    pages(harness, monkeypatch, InvalidSessionIdException("invalid session id"), good)
    assert harness._next_page(2) == good
    assert harness.calls == ["stop", "start", "open", "jump 2"]
    assert any("restarted" in text for text in harness.warnings)


def test_a_dead_browser_that_raises_urllib3_errors_is_also_restarted(harness, monkeypatch):
    good = (rows("2"), info(2, 2, 2))
    pages(harness, monkeypatch, MaxRetryError(None, "/session", "connection refused"), good)
    assert harness._next_page(2) == good
    assert "start" in harness.calls


def test_a_slow_page_is_retried_without_a_new_browser(harness, monkeypatch):
    good = (rows("2"), info(2, 2, 2))
    pages(harness, monkeypatch, PageFailed("did not reload"), good)
    assert harness._next_page(2) == good
    assert "start" not in harness.calls


def test_a_one_off_error_page_is_retried_rather_than_reported_as_a_changed_site(harness, monkeypatch):
    good = (rows("2"), info(2, 2, 2))
    pages(harness, monkeypatch, SiteChanged("the results table is missing"), good)
    assert harness._next_page(2) == good


def test_a_site_that_really_changed_still_fails(harness, monkeypatch):
    changed = SiteChanged("unexpected result columns")
    pages(harness, monkeypatch, changed, changed)
    with pytest.raises(SiteChanged):
        harness._open_first_page()


def test_a_failed_restart_keeps_what_was_saved_and_says_so(harness, monkeypatch):
    def no_browser():
        raise WebDriverException("chrome failed to start")

    monkeypatch.setattr(harness, "start_driver", no_browser)
    pages(harness, monkeypatch, InvalidSessionIdException("invalid session id"))
    result, complete = harness._sweep(rows("1"), info(2, 2, 1), None)
    assert not complete and harness.saved == ["1"]
    assert "Results are incomplete" in harness.warnings[-1]


def test_recoveries_are_limited(harness, monkeypatch):
    harness._recoveries = module.MAX_RECOVERIES
    pages(harness, monkeypatch, PageFailed("x"))
    result, complete = harness._sweep(rows("1"), info(2, 2, 1), None)
    assert not complete and "open" not in harness.calls


def test_a_row_missed_because_the_list_moved_is_found_by_reading_again(harness, monkeypatch):
    pages(harness, monkeypatch, (rows("1", "2"), info(3, 1, 1)), (rows("1", "2", "3"), info(3, 1, 1)))
    harness.run()
    assert harness.saved == ["1", "2", "3"]
    assert harness._skipped_repeat == 0
    assert harness.warnings == [] and "incomplete" not in harness.progress["checkpoint"]


def test_rows_still_missing_after_reading_again_are_reported(harness, monkeypatch):
    pages(harness, monkeypatch, (rows("1"), info(3, 1, 1)), (rows("1"), info(3, 1, 1)))
    harness.run()
    assert "site reports 3" in harness.warnings[-1]
    assert "site reports 3" in harness.progress["checkpoint"]["incomplete"]


def test_a_complete_read_is_not_repeated(harness, monkeypatch):
    pages(harness, monkeypatch, (rows("1", "2"), info(2, 1, 1)))
    harness.run()
    assert harness.calls.count("open") == 1 and harness.warnings == []
