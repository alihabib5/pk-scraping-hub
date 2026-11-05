"""Selenium automation for the Punjab e-procurement search page.

The site is ASP.NET WebForms: searching and paging are form posts on one URL, so
there is no page address to open. Each step therefore clicks, waits for the page
to be replaced, and checks the new page before anything from it is saved.
"""

import logging
import random
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from app.config import settings
from app.core import run_manager
from app.core.base_scraper import BaseScraper, StopRequested
from app.core.closing_filter import days_until_close
from app.core.exports import archive_run
from app.scrapers.punjab import repository
from app.scrapers.punjab.filters import save_filter_options, search_dates, site_date, site_to_date
from app.scrapers.punjab.parsers import (
    ELEMENT_PREFIX,
    SELECTS,
    PageInfo,
    SiteChanged,
    check_columns,
    is_auction,
    parse_listing,
    parse_options,
    parse_pager,
)
from app.scrapers.punjab.schemas import PunjabFilters, PunjabOptions
from app.services.notifier import notify_scrape_completion

logger = logging.getLogger(__name__)

GRID_ID = f"{ELEMENT_PREFIX}rdgrdManageTender"
RELOAD_TIMEOUT = 60        # seconds to wait for a post to replace the page
MAX_RECOVERIES = 3         # re-searches allowed per run

_RELOADED = (
    "return window.__pkhub !== 1 && document.readyState !== 'loading'"
    " && !!document.querySelector('table.rgMasterTable')"
)


class PageFailed(Exception):
    """A page did not load, or is not the page that was asked for."""


class PunjabScraper(BaseScraper):
    def __init__(
        self,
        run_id: str,
        filters: PunjabFilters,
        options: PunjabOptions,
        parent_run_id: str | None = None,
    ):
        super().__init__(run_id)
        self.filters = filters
        self.options = options
        self.parent_run_id = parent_run_id
        self.first_day, self.last_day = search_dates(filters)
        self.seen: set[str] = set()
        self.rows_scraped_total = 0
        self._rows_new = 0
        self._rows_changed = 0
        self._skipped_closing = 0
        self._kept_unverified = 0
        self._skipped_auction = 0
        self._skipped_repeat = 0
        self._rejected_links = 0
        self._recoveries = 0

    # -- the site ------------------------------------------------------------

    @property
    def base_url(self) -> str:
        return settings.punjab_base_url

    def polite_delay(self) -> None:
        delay_min = settings.punjab_delay_min_ms / 1000.0
        delay_max = max(delay_min, settings.punjab_delay_max_ms / 1000.0)
        time.sleep(random.uniform(delay_min, delay_max))

    def _wait_for_reload(self) -> None:
        """Wait for a post to replace the page. The marker set beforehand lives on
        `window`, so it disappears only when a new document has loaded."""
        deadline = time.monotonic() + RELOAD_TIMEOUT
        while time.monotonic() < deadline:
            self.raise_if_stopped()
            try:
                if self.driver.execute_script(_RELOADED):
                    return
            except WebDriverException:
                # Normal while the old document is being torn down.
                logger.debug("[run %s] page still reloading", self.run_id, exc_info=True)
            time.sleep(0.3)
        raise PageFailed(f"the page did not reload within {RELOAD_TIMEOUT}s")

    def _post(self, action) -> None:
        self.driver.execute_script("window.__pkhub = 1")
        action()
        self._wait_for_reload()

    def _read_page(self, expected_page: int) -> tuple[str, PageInfo]:
        """The current page's HTML and totals, once it is proven to be the right page."""
        html = self.driver.page_source
        check_columns(html)
        info = parse_pager(html)
        if info.no_records and expected_page > 1:
            raise PageFailed(f"page {expected_page} came back empty")
        if not info.no_records and info.current_page != expected_page:
            raise PageFailed(f"expected page {expected_page}, got {info.current_page}")
        return html, info

    def _search(self) -> None:
        """Run the search from a freshly loaded page. Fresh matters: the grid keeps
        its page number across searches, so searching from page 33 of an earlier
        result reports "No Record Found!" for a search that has matches."""
        self.navigate(urljoin(self.base_url, settings.punjab_search_path))
        self.raise_if_stopped()
        try:
            save_filter_options(parse_options(self.driver.page_source))
        except Exception:  # noqa: BLE001 — the dropdown cache must never fail a scrape
            logger.exception("[run %s] could not refresh the filter options", self.run_id)

        for field, suffix in SELECTS.items():
            value = getattr(self.filters, field)
            if value:
                Select(self.driver.find_element(By.ID, ELEMENT_PREFIX + suffix)).select_by_value(value)
        # The boxes are read-only for typing. Values go in as arguments, never as script text.
        for suffix, value in (
            ("txtFromDate", site_date(self.first_day)),
            ("txtToDate", site_to_date(self.last_day)),
        ):
            box = self.driver.find_element(By.ID, ELEMENT_PREFIX + suffix)
            self.driver.execute_script("arguments[0].value = arguments[1]", box, value)
        self._post(self.driver.find_element(By.ID, f"{ELEMENT_PREFIX}btnSubmit").click)

    def _jump_to(self, page: int) -> None:
        """Move the grid to a page. setTimeout runs the call outside Selenium's
        strict-mode wrapper, which the site's Ajax library cannot run under."""
        script = f'setTimeout(function(){{ $find("{GRID_ID}").get_masterTableView().page({int(page)}) }}, 0)'
        self._post(lambda: self.driver.execute_script(script))

    def _recover(self, page: int) -> tuple[str, PageInfo]:
        """Repeat the search and return to `page`. There is no URL to reopen."""
        self._recoveries += 1
        if self._recoveries > MAX_RECOVERIES:
            raise PageFailed(f"gave up after {MAX_RECOVERIES} recoveries")
        logger.warning("[run %s] recovering at page %d (attempt %d)", self.run_id, page, self._recoveries)
        self._search()
        if page > 1:
            self._jump_to(page)
        return self._read_page(page)

    def _open_first_page(self) -> tuple[str, PageInfo]:
        try:
            self._search()
            return self._read_page(1)
        except (PageFailed, WebDriverException) as exc:
            self.raise_if_stopped()
            logger.warning("[run %s] first search failed: %s", self.run_id, exc)
            return self._recover(1)

    def _next_page(self, page: int) -> tuple[str, PageInfo]:
        try:
            self._post(self.driver.find_element(By.CSS_SELECTOR, ".rgPageNext").click)
            return self._read_page(page)
        except (PageFailed, WebDriverException) as exc:
            # Stop quits the browser mid-load; that must end as a stop, not a recovery.
            self.raise_if_stopped()
            logger.warning("[run %s] page %d failed: %s", self.run_id, page, exc)
            return self._recover(page)

    # -- rows ----------------------------------------------------------------

    def _keep(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply the run's rules to a page, counting everything dropped."""
        runway = self.options.get_runway_days()
        kept = []
        for record in records:
            self._rejected_links += record["rejected_links"]
            # A new tender pushes rows on to the next page, so a row can appear twice.
            if record["tender_no"] in self.seen:
                self._skipped_repeat += 1
                continue
            self.seen.add(record["tender_no"])

            if self.options.exclude_auctions and is_auction(record["notice_type"]):
                self._skipped_auction += 1
                continue
            if runway is not None:
                days = days_until_close(record["closing_on"])
                if days is None:
                    self._kept_unverified += 1
                elif days < runway:
                    self._skipped_closing += 1
                    continue
            kept.append(record)
        return kept

    def _save_page(self, html: str, page: int, parent_hashes: dict[str, str] | None) -> None:
        kept = self._keep(parse_listing(html, self.base_url))
        new_count, changed_count, _ = repository.upsert_bids(self.run_id, page, kept, parent_hashes)
        repository.append_to_mirror(self.run_id, kept)

        self.rows_scraped_total += len(kept)
        self._rows_new += new_count
        self._rows_changed += changed_count
        counters = {
            "rows_new": self._rows_new,
            "rows_changed": self._rows_changed,
            "skipped_closing": self._skipped_closing,
            "kept_unverified": self._kept_unverified,
            "skipped_auction": self._skipped_auction,
            "skipped_repeat": self._skipped_repeat,
        }
        run_manager.update_run(self.run_id, bids_processed=self.rows_scraped_total, **counters)
        repository.update_run_progress(
            self.run_id,
            current_page=page,
            rows_scraped=self.rows_scraped_total,
            checkpoint={"page": page, "last_tender": kept[-1]["tender_no"] if kept else None},
            **counters,
        )

    def _record_totals(self, info: PageInfo) -> None:
        run_manager.update_run(
            self.run_id,
            total_expected=info.total_records,
            total_pages=info.total_pages,
            bids_found=info.total_records,
        )
        repository.update_run_progress(
            self.run_id, total_expected=info.total_records, total_pages=info.total_pages
        )

    # -- the run -------------------------------------------------------------

    def run(self) -> None:
        self.start_driver()
        run_manager.update_run(self.run_id, status="running", step="opening_punjab")
        repository.update_run_progress(self.run_id, closing_from=self.first_day, closing_to=self.last_day)
        self.raise_if_stopped()

        html, info = self._open_first_page()
        logger.info("[run %s] %d tenders across %d pages", self.run_id, info.total_records, info.total_pages)
        self._record_totals(info)
        run_manager.update_run(self.run_id, step="scraping_pages")

        parent_hashes = (
            repository.get_parent_run_hashes(self.parent_run_id) if self.parent_run_id else None
        )

        page = 1
        complete = True
        while not info.no_records:
            self.raise_if_stopped()
            run_manager.update_run(
                self.run_id, current_page=page, step=f"page_{page}_of_{info.total_pages}"
            )
            self._save_page(html, page, parent_hashes)

            if page >= info.total_pages:
                break
            self.polite_delay()
            self.raise_if_stopped()
            try:
                html, next_info = self._next_page(page + 1)
            except (PageFailed, WebDriverException) as exc:
                self.raise_if_stopped()
                logger.warning("[run %s] page %d failed for good: %s", self.run_id, page + 1, exc)
                run_manager.add_warning(
                    self.run_id,
                    f"Stopped at page {page} of {info.total_pages}: page {page + 1} would not load "
                    f"({self.describe_failure(exc)}). Results are incomplete.",
                )
                complete = False
                break
            page += 1
            # New tenders arrive during a run, so the totals can move.
            if next_info[:2] != info[:2]:
                self._record_totals(next_info)
            info = next_info

        self._finish_checks(info, complete)
        run_manager.update_run(self.run_id, step="packaging_results")

    def _finish_checks(self, info: PageInfo, complete: bool) -> None:
        if self._rejected_links:
            run_manager.add_warning(
                self.run_id,
                f"{self._rejected_links} PDF link(s) did not match the site's known format and were left out.",
            )
        if complete and len(self.seen) < info.total_records:
            run_manager.add_warning(
                self.run_id,
                f"Read {len(self.seen)} different tenders but the site reports {info.total_records}. "
                "Tenders can change while a run is in progress.",
            )

    def flush_partial(self) -> int:
        # Rows are saved page by page, so everything a stopped run gathered is
        # already in punjab_bids.
        return self.rows_scraped_total


_lists_lock = threading.Lock()


def refresh_lists() -> int:
    """Read the dropdowns from the live page through Chrome, because plain HTTP
    clients fail on this page. One at a time, and outside the worker pool."""
    with _lists_lock:
        reader = BaseScraper("punjab-filter-lists")
        try:
            reader.start_driver()
            reader.navigate(urljoin(settings.punjab_base_url, settings.punjab_search_path))
            options = parse_options(reader.driver.page_source)
        finally:
            reader.cleanup()
    if not options:
        raise SiteChanged("the page had no filter dropdowns")
    return save_filter_options(options)


def _finish(run_id: str, status: str, error: str | None = None) -> None:
    """Record the terminal status. The punjab_runs row is written first, because
    the workbook's Run Summary is built from it during archiving."""
    repository.update_run_progress(
        run_id, status=status, finished_at=datetime.now(timezone.utc), error=error
    )
    run = run_manager.get_run(run_id) or {}
    if not run.get("finished_at"):  # request_stop already stamped a stopped run
        run_manager.update_run(run_id, finished_at=datetime.now().isoformat())


def execute_run(
    run_id: str,
    filters_dict: dict[str, Any],
    options_dict: dict[str, Any],
    parent_run_id: str | None = None,
) -> None:
    """Worker task executed on the thread pool."""
    scraper = PunjabScraper(
        run_id, PunjabFilters(**filters_dict), PunjabOptions(**options_dict), parent_run_id
    )
    try:
        scraper.run()
        _finish(run_id, "completed")
        archive_run(run_id)
        notify_scrape_completion(run_id, "punjab", scraper.rows_scraped_total)
        run_manager.update_run(run_id, status="completed", step="completed")
    except StopRequested:
        logger.info("[run %s] stopped gracefully by user", run_id)
        _finish(run_id, "stopped")
        # Sets partial_results, which the download endpoint needs for a stopped run.
        scraper.deliver_partial()
    except Exception as exc:
        logger.exception("[run %s] Punjab run failed: %s", run_id, exc)
        cause = scraper.describe_failure(exc)
        _finish(run_id, "failed", error=cause)
        run_manager.add_error(run_id, cause)
        run_manager.update_run(run_id, status="failed", step="failed")
    finally:
        scraper.cleanup()
