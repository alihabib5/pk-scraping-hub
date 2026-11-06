"""Selenium automation for the Punjab Active Tenders page.

The page has no search form, so a run reads every active tender and applies its
filters to each row. It is ASP.NET WebForms: paging is a form post on one URL, so
each step clicks, waits for the page to be replaced, and checks the new page
before anything from it is saved.
"""

import logging
import random
import time
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urljoin

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from urllib3.exceptions import HTTPError as Urllib3HTTPError

from app.config import settings
from app.core import run_manager
from app.core.base_scraper import BaseScraper, StopRequested
from app.core.closing_filter import days_until_close, parse_close_date
from app.core.exports import archive_run
from app.scrapers.punjab import repository
from app.scrapers.punjab.filters import wanted_labels
from app.scrapers.punjab.parsers import (
    ELEMENT_PREFIX,
    PageInfo,
    SiteChanged,
    check_columns,
    is_auction,
    parse_listing,
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


def _in_range(value: str | None, first: date | None, last: date | None) -> bool:
    """Both ends count. An unreadable date is kept, as the closing guard does."""
    day = parse_close_date(value)
    return day is None or not ((first and day < first) or (last and day > last))


class PageFailed(Exception):
    """A page did not load, or is not the page that was asked for."""


# A dead browser raises urllib3 errors, and a one-off server error page has no
# results table, so both are worth a recovery before giving up.
_PAGE_ERRORS = (PageFailed, SiteChanged, WebDriverException, Urllib3HTTPError)


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
        self.wanted = wanted_labels(filters)
        self.runway = options.get_runway_days()
        # A closing range the minimum can never meet would empty the run, so the
        # dates the user chose win, and a notice says so.
        self._runway_ignored = bool(
            self.runway is not None
            and filters.closing_to
            and days_until_close(filters.closing_to.isoformat()) < self.runway
        )
        if self._runway_ignored:
            self.runway = None
        self.seen: set[str] = set()
        self.rows_scraped_total = 0
        self._rows_new = 0
        self._rows_changed = 0
        self._skipped_closing = 0
        self._kept_unverified = 0
        self._skipped_auction = 0
        self._skipped_repeat = 0
        self._skipped_filter = 0
        self._rejected_links = 0
        self._recoveries = 0
        self._rereading = False
        self._incomplete: str | None = None

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
            except WebDriverException as exc:
                if self._is_dead_session_error(exc):
                    raise
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
        # The list holds every open tender, so an empty page is a bad load, not a result.
        if info.no_records:
            raise PageFailed(
                f"the site showed no tenders on page {expected_page}, so it probably "
                "didn't load properly. Run it again."
            )
        if info.current_page != expected_page:
            raise PageFailed(f"expected page {expected_page}, got {info.current_page}")
        return html, info

    def _open_list(self) -> None:
        self.navigate(urljoin(self.base_url, settings.punjab_search_path))
        self._wait_for_reload()

    def _jump_to(self, page: int) -> None:
        """Move the grid to a page. setTimeout runs the call outside Selenium's
        strict-mode wrapper, which the site's Ajax library cannot run under."""
        script = f'setTimeout(function(){{ $find("{GRID_ID}").get_masterTableView().page({int(page)}) }}, 0)'
        self._post(lambda: self.driver.execute_script(script))

    def _restart_browser(self, page: int) -> None:
        logger.warning("[run %s] the browser died at page %d, restarting it", self.run_id, page)
        self.stop_driver()
        self.raise_if_stopped()
        self.start_driver()
        if self._stop_requested:
            # stop() quit the old browser, so it can't have reached this new one.
            self._driver_closed = False
            self.stop_driver()
            raise StopRequested("run stopped by user")
        run_manager.add_warning(
            self.run_id, f"The browser stopped at page {page} and was restarted. The run carried on from there."
        )

    def _recover(self, page: int, cause: Exception) -> tuple[str, PageInfo]:
        """Reopen the list and return to `page`. A page has no URL of its own."""
        self._recoveries += 1
        if self._recoveries > MAX_RECOVERIES:
            raise PageFailed(f"gave up after {MAX_RECOVERIES} recoveries")
        logger.warning("[run %s] recovering at page %d (attempt %d)", self.run_id, page, self._recoveries)
        self.polite_delay()
        if self._is_dead_session_error(cause):
            self._restart_browser(page)
        self._open_list()
        if page > 1:
            self._jump_to(page)
        return self._read_page(page)

    def _open_first_page(self) -> tuple[str, PageInfo]:
        try:
            self._open_list()
            return self._read_page(1)
        except _PAGE_ERRORS as exc:
            self.raise_if_stopped()
            logger.warning("[run %s] first page failed: %s", self.run_id, exc)
            return self._recover(1, exc)

    def _next_page(self, page: int) -> tuple[str, PageInfo]:
        try:
            self._post(self.driver.find_element(By.CSS_SELECTOR, ".rgPageNext").click)
            return self._read_page(page)
        except _PAGE_ERRORS as exc:
            # Stop quits the browser mid-load; that must end as a stop, not a recovery.
            self.raise_if_stopped()
            logger.warning("[run %s] page %d failed: %s", self.run_id, page, exc)
            return self._recover(page, exc)

    # -- rows ----------------------------------------------------------------

    def _matches(self, record: dict[str, Any]) -> bool:
        """Whether a row passes the run's dropdown and date filters."""
        if any((record.get(key) or "").lower() != label for key, label in self.wanted.items()):
            return False
        chosen = self.filters
        return _in_range(record.get("published_on"), chosen.published_from, chosen.published_to) and _in_range(
            record["closing_on"], chosen.closing_from, chosen.closing_to
        )

    def _keep(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply the run's rules to a page, counting everything dropped."""
        kept = []
        for record in records:
            # A new tender pushes rows on to the next page, so a row can appear twice.
            if record["tender_no"] in self.seen:
                if not self._rereading:
                    self._skipped_repeat += 1
                continue
            self.seen.add(record["tender_no"])
            self._rejected_links += record["rejected_links"]

            if self.options.exclude_auctions and is_auction(record["notice_type"]):
                self._skipped_auction += 1
                continue
            if not self._matches(record):
                self._skipped_filter += 1
                continue
            if self.runway is not None:
                days = days_until_close(record["closing_on"])
                if days is None:
                    self._kept_unverified += 1
                elif days < self.runway:
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
        repository.update_run_progress(
            self.run_id, closing_from=self.filters.closing_from, closing_to=self.filters.closing_to
        )
        self.raise_if_stopped()

        html, info = self._open_first_page()
        logger.info("[run %s] %d tenders across %d pages", self.run_id, info.total_records, info.total_pages)
        self._record_totals(info)
        run_manager.update_run(self.run_id, step="scraping_pages")

        parent_hashes = (
            repository.get_parent_run_hashes(self.parent_run_id) if self.parent_run_id else None
        )

        info, complete = self._sweep(html, info, parent_hashes)
        if complete and len(self.seen) < info.total_records:
            info, complete = self._sweep_again(info, parent_hashes)

        self._finish_checks(info, complete)
        run_manager.update_run(self.run_id, step="packaging_results")

    def _sweep(
        self, html: str, info: PageInfo, parent_hashes: dict[str, str] | None
    ) -> tuple[PageInfo, bool]:
        """Read from page 1 to the end. Returns the latest totals and whether it got there."""
        page = 1
        while True:
            self.raise_if_stopped()
            run_manager.update_run(
                self.run_id, current_page=page, step=f"page_{page}_of_{info.total_pages}"
            )
            self._save_page(html, page, parent_hashes)

            if page >= info.total_pages:
                return info, True
            self.polite_delay()
            self.raise_if_stopped()
            try:
                html, next_info = self._next_page(page + 1)
            except _PAGE_ERRORS as exc:
                self.raise_if_stopped()
                logger.warning("[run %s] page %d failed for good: %s", self.run_id, page + 1, exc)
                self._incomplete = (
                    f"Stopped at page {page} of {info.total_pages}: page {page + 1} would not load "
                    f"({self.describe_failure(exc)}). Results are incomplete."
                )
                run_manager.add_warning(self.run_id, self._incomplete)
                return info, False
            page += 1
            # New tenders arrive during a run, so the totals can move.
            if next_info[:2] != info[:2]:
                self._record_totals(next_info)
            info = next_info

    def _sweep_again(
        self, info: PageInfo, parent_hashes: dict[str, str] | None
    ) -> tuple[PageInfo, bool]:
        """Read once more when tenders are missing: one leaving the list moves later
        rows back a page, past where the run has read. Seen rows are simply skipped."""
        logger.info("[run %s] read %d of %d tenders, reading again", self.run_id, len(self.seen), info.total_records)
        self._rereading = True
        self.polite_delay()
        try:
            html, fresh = self._open_first_page()
        except _PAGE_ERRORS as exc:
            self.raise_if_stopped()
            logger.warning("[run %s] the second read failed: %s", self.run_id, exc)
            return info, True
        self._record_totals(fresh)
        return self._sweep(html, fresh, parent_hashes)

    def _finish_checks(self, info: PageInfo, complete: bool) -> None:
        if self._runway_ignored:
            run_manager.add_warning(
                self.run_id,
                f"Min. days until closing ({self.options.get_runway_days()}) was not applied, because "
                "every tender in your closing date range closes sooner than that.",
            )
        if self.seen and not self.rows_scraped_total:
            run_manager.add_warning(
                self.run_id,
                f"The site listed {len(self.seen)} active tenders but none were saved: "
                f"{self._skipped_auction} Sales/Auction/Disposal, "
                f"{self._skipped_filter} not matching your filters, "
                f"{self._skipped_closing} closing too soon.",
            )
        elif self._skipped_filter:
            run_manager.add_warning(
                self.run_id, f"{self._skipped_filter} active tenders didn't match your filters."
            )
        if self._rejected_links:
            run_manager.add_warning(
                self.run_id,
                f"{self._rejected_links} PDF link(s) did not match the site's known format and were left out.",
            )
        if complete and len(self.seen) < info.total_records:
            self._incomplete = (
                f"Read {len(self.seen)} different tenders but the site reports {info.total_records}. "
                "Tenders can change while a run is in progress."
            )
            run_manager.add_warning(self.run_id, self._incomplete)
        if self._incomplete:
            repository.update_run_progress(self.run_id, checkpoint={"incomplete": self._incomplete})

    def flush_partial(self) -> int:
        # Rows are saved page by page, so everything a stopped run gathered is
        # already in punjab_bids.
        return self.rows_scraped_total


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
