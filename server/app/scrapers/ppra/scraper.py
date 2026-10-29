"""Selenium automation for PPRA active tenders."""

import logging
import random
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from selenium.common.exceptions import WebDriverException

from app.config import settings
from app.core import run_manager
from app.core.base_scraper import BaseScraper, StopRequested
from app.core.closing_filter import days_until_close
from app.core.exports import archive_run
from app.scrapers.ppra import repository
from app.scrapers.ppra.filters import build_search_url, save_filter_options
from app.scrapers.ppra.parsers import is_karachi, parse_listing, parse_options, parse_total
from app.scrapers.ppra.schemas import PpraFilters, PpraOptions
from app.services.notifier import notify_scrape_completion

logger = logging.getLogger(__name__)


class PpraScraper(BaseScraper):
    def __init__(
        self,
        run_id: str,
        filters: PpraFilters,
        options: PpraOptions,
        parent_run_id: str | None = None,
    ):
        super().__init__(run_id)
        self.filters = filters
        self.options = options
        self.parent_run_id = parent_run_id
        self._skipped_closing = 0
        self._kept_unverified = 0
        self._skipped_city = 0
        self.rows_scraped_total = 0

    def polite_delay(self) -> None:
        delay_min = (self.options.delay_ms or settings.ppra_delay_min_ms) / 1000.0
        delay_max = settings.ppra_delay_max_ms / 1000.0
        delay = random.uniform(delay_min, max(delay_min, delay_max))
        time.sleep(delay)

    def run(self) -> None:
        self.start_driver()
        run_manager.update_run(self.run_id, status="running", step="opening_site")
        self.raise_if_stopped()

        base_url = settings.ppra_base_url
        start_url = urljoin(base_url, settings.ppra_active_tenders_path)

        first_url = build_search_url(self.filters, start_url, page=1)
        logger.info("[run %s] navigating to PPRA with filters: %s", self.run_id, first_url)
        self.navigate(first_url)
        self.raise_if_stopped()

        # The page carries the search form, so keep the console's dropdowns
        # (organizations, sectors, …) in step with the site on every run.
        try:
            save_filter_options(parse_options(self.driver.page_source))
        except Exception:  # noqa: BLE001 — the dropdown cache must never fail a scrape
            logger.exception("[run %s] could not refresh the filter options", self.run_id)

        total_records, total_pages = parse_total(self.driver.page_source)
        logger.info("[run %s] parsed PPRA totals: %d tenders across %d pages", self.run_id, total_records, total_pages)

        run_manager.update_run(
            self.run_id,
            total_expected=total_records,
            total_pages=total_pages,
            bids_found=total_records,
            step="scraping_pages",
        )
        repository.update_run_progress(
            self.run_id, total_expected=total_records, total_pages=total_pages
        )

        parent_hashes = None
        if self.parent_run_id:
            parent_hashes = repository.get_parent_run_hashes(self.parent_run_id)

        current_page = 1
        rows_scraped_total = 0
        rows_new_total = 0
        rows_changed_total = 0

        while current_page <= total_pages:
            self.raise_if_stopped()
            run_manager.update_run(
                self.run_id,
                current_page=current_page,
                step=f"page_{current_page}_of_{total_pages}",
            )

            # Parse listings on current page
            page_records = parse_listing(self.driver.page_source, base_url=base_url)

            # Apply close date filter if requested
            runway = self.options.get_runway_days()
            filtered_records = []
            for rec in page_records:
                if self.options.exclude_karachi and is_karachi(rec.get("city")):
                    self._skipped_city += 1
                    continue
                if runway is not None:
                    days = days_until_close(rec.get("closing_at"))
                    if days is None:
                        self._kept_unverified += 1
                        filtered_records.append(rec)
                    elif days >= runway:
                        filtered_records.append(rec)
                    else:
                        self._skipped_closing += 1
                else:
                    filtered_records.append(rec)

            # Store in DB
            new_c, changed_c, unchanged_c = repository.upsert_bids(
                self.run_id, current_page, filtered_records, parent_hashes
            )
            repository.append_to_mirror(self.run_id, filtered_records)

            rows_scraped_total += len(filtered_records)
            self.rows_scraped_total = rows_scraped_total
            rows_new_total += new_c
            rows_changed_total += changed_c

            run_manager.update_run(
                self.run_id,
                bids_processed=rows_scraped_total,
                rows_new=rows_new_total,
                rows_changed=rows_changed_total,
                skipped_closing=self._skipped_closing,
                kept_unverified=self._kept_unverified,
                skipped_city=self._skipped_city,
            )
            repository.update_run_progress(
                self.run_id,
                current_page=current_page,
                rows_scraped=rows_scraped_total,
                rows_new=rows_new_total,
                rows_changed=rows_changed_total,
                skipped_closing=self._skipped_closing,
                kept_unverified=self._kept_unverified,
                checkpoint={
                    "page": current_page,
                    "last_tender": filtered_records[-1]["tender_no"] if filtered_records else None,
                },
            )

            current_page += 1
            if current_page <= total_pages:
                self.polite_delay()
                # Navigate to next page with active filters preserved
                next_url = build_search_url(self.filters, start_url, page=current_page)
                try:
                    self.navigate(next_url)
                except WebDriverException as exc:
                    # Stop quits the browser mid-load; that must end as a stop, not a short "completed" run.
                    self.raise_if_stopped()
                    logger.warning("[run %s] navigation to page %d failed: %s", self.run_id, current_page, exc)
                    run_manager.add_warning(
                        self.run_id,
                        f"Stopped at page {current_page - 1} of {total_pages}: page {current_page} "
                        f"would not load ({self.describe_failure(exc)}). Results are incomplete.",
                    )
                    break

        run_manager.update_run(self.run_id, step="packaging_results")

    def flush_partial(self) -> int:
        # Rows are upserted page by page as they are parsed, so everything a
        # stopped run gathered is already in ppra_bids — nothing left to write.
        return self.rows_scraped_total


def _finish(run_id: str, status: str, error: str | None = None) -> None:
    """Record the terminal status on both the live run and its ppra_runs row.

    The ppra_runs row is written first: the Excel's Run Summary sheet is built
    from it during archiving, and would otherwise report the run as still
    running with no finish time.
    """
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
    filters = PpraFilters(**filters_dict)
    options = PpraOptions(**options_dict)
    scraper = PpraScraper(run_id, filters, options, parent_run_id)

    try:
        scraper.run()
        _finish(run_id, "completed")
        archive_run(run_id)
        notify_scrape_completion(run_id, "ppra", scraper.rows_scraped_total)
        run_manager.update_run(run_id, status="completed", step="completed")
    except StopRequested:
        logger.info("[run %s] stopped gracefully by user", run_id)
        _finish(run_id, "stopped")
        # Archives the sheet and sets partial_results, which is what the
        # download endpoint requires before it will serve a stopped run.
        scraper.deliver_partial()
    except Exception as exc:
        logger.exception("[run %s] PPRA run failed: %s", run_id, exc)
        cause = scraper.describe_failure(exc)
        _finish(run_id, "failed", error=cause)
        run_manager.add_error(run_id, cause)
        run_manager.update_run(run_id, status="failed", step="failed")
    finally:
        scraper.cleanup()

