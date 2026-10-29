"""Shared Selenium machinery for portal scrapers.

Subclass BaseScraper and implement the portal-specific flow. The base handles
the Chrome driver, navigation with retries, the live-screenshot hook, and the
cooperative pause/stop checkpoint.
"""

import logging
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from urllib3.exceptions import HTTPError as _Urllib3HTTPError
from webdriver_manager.chrome import ChromeDriverManager

from app.config import settings
from app.core import live, run_manager

logger = logging.getLogger(__name__)

# Chrome network errors that are worth retrying: a transient DNS/socket failure
# rather than a real "this page is wrong" problem. DNS is the common one — a
# resolver that round-robins across upstreams will fail a lookup on a broken
# upstream and succeed on the next attempt via a good one.
TRANSIENT_NET_ERRORS = (
    "err_name_not_resolved",
    "err_name_resolution_failed",
    "err_dns_timed_out",
    "err_internet_disconnected",
    "err_connection_reset",
    "err_connection_closed",
    "err_connection_timed_out",
    "err_connection_failed",
    "err_timed_out",
    "err_empty_response",
    "err_socket_not_connected",
    "err_address_unreachable",
    "err_network_changed",
)
NAVIGATE_ATTEMPTS = 4      # total tries before giving up
NAVIGATE_BACKOFF = 2.0     # seconds, doubled after each failed attempt


class StopRequested(Exception):
    """Raised inside a scrape when the user has asked it to stop, so the flow
    unwinds at the next checkpoint instead of running to completion."""

# A realistic desktop-Chrome UA. Under --headless=new the default UA no longer
# leaks a "HeadlessChrome" token, but bot-protected sites still 403 the
# automation fingerprint, so we pin a normal UA to match.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)


def _clear_stale_wdm_locks(max_age: float = 300) -> None:
    """Remove leftover webdriver-manager lock files older than `max_age` seconds.

    webdriver-manager serialises driver downloads with a lock file under ~/.wdm.
    A process killed mid-install leaves that lock behind, and every later
    start_driver then waits on it and fails with "Timed out waiting for
    webdriver-manager lock". A healthy install holds the lock for seconds, so
    anything old is safe to clear.
    """
    try:
        for lock in (Path.home() / ".wdm").glob(".wdm-lock*"):
            if time.time() - lock.stat().st_mtime > max_age:
                lock.unlink(missing_ok=True)
                logger.warning("removed stale webdriver-manager lock %s", lock)
    except OSError:  # lock cleanup is best-effort; a stuck lock is retried below
        logger.debug("could not clear webdriver-manager locks", exc_info=True)


_driver_path: str | None = None
_driver_path_lock = threading.Lock()


def _resolve_chromedriver() -> str:
    """The chromedriver path, resolved once per server process.

    webdriver-manager checks versions over the network on every install(), which
    adds seconds to each run. A Chrome update while the server is running can
    leave the cached driver mismatched; restarting the server re-resolves it.
    """
    global _driver_path
    with _driver_path_lock:
        if _driver_path is None or not Path(_driver_path).exists():
            _driver_path = _install_chromedriver()
        return _driver_path


def _install_chromedriver() -> str:
    """ChromeDriverManager().install(), self-healing a stale wdm lock.

    Clears clearly-stale locks first; if the resolver still times out on the
    lock, remove it outright and retry once (a concurrent healthy install only
    holds the lock briefly, so a timeout means it is orphaned).
    """
    _clear_stale_wdm_locks()
    try:
        return ChromeDriverManager().install()
    except Exception as exc:  # noqa: BLE001 — only the lock timeout is retried
        if "lock" not in str(exc).lower():
            raise
        logger.warning("webdriver-manager lock timeout — clearing the lock and retrying once")
        _clear_stale_wdm_locks(max_age=0)
        return ChromeDriverManager().install()


class BaseScraper:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.driver: webdriver.Chrome | None = None
        # Flipped by stop() (from another thread) when the user asks to stop.
        self._stop_requested = False
        # Set once the browser has been torn down by stop(): nothing new may be
        # sent to it, though `self.driver` stays put so in-flight Selenium calls
        # still fail as WebDriverException rather than AttributeError.
        self._driver_closed = False

    # -- lifecycle ----------------------------------------------------------

    def start_driver(self) -> None:
        """Launch Chrome. A run started from the "Live preview" button shows the
        browser; every other run is headless."""
        options = Options()
        run = run_manager.get_run(self.run_id) or {}
        headless = not run.get("live_preview", False)
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        else:
            # A visible window is being watched, so give it the whole screen.
            options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Trim Chrome's memory/CPU footprint. The portal is a plain form-and-
        # table page that needs none of the GPU stack, extensions, or background
        # services, and on a memory-tight host that headroom is the difference
        # between a run finishing and Chrome being OOM-killed mid-flow (which
        # surfaces as a dead WebDriver session — see describe_failure).
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-default-apps")
        # Resolve hostnames over DNS-over-HTTPS rather than through the machine's
        # resolver, which on some networks answers whole TLDs with an empty
        # record set and breaks a run with net::ERR_NAME_NOT_RESOLVED.
        # "secure" means DoH only — no silent fall back to the broken resolver.
        if settings.dns_over_https and settings.dns_over_https_templates.strip():
            options.add_argument("--dns-over-https-mode=secure")
            options.add_argument(
                f"--dns-over-https-templates={settings.dns_over_https_templates.strip()}"
            )
        # Return from driver.get() at DOMContentLoaded instead of the load event.
        # Third-party subresources (fonts, analytics) can stall for a minute on a
        # flaky network, and the page itself is usable long before that.
        options.page_load_strategy = "eager"
        # Strip the automation fingerprint that makes bot-protected sites return
        # 403 Forbidden: drop the "controlled by automated software" switches and
        # the AutomationControlled blink feature (which sets navigator.webdriver).
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={USER_AGENT}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        service = Service(_resolve_chromedriver())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(60)
        # Expose this run's browser to the shared live-screenshot endpoint so the
        # Live Preview modal can stream frames while it is open.
        live.register(self.run_id, self)
        # Belt-and-suspenders: ensure navigator.webdriver is undefined on every
        # document before the page's own scripts run, so bot checks don't see it.
        try:
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
            )
        except WebDriverException:
            # Older Chrome builds lack this CDP command; the UA and blink flag still apply.
            logger.debug("[run %s] could not hide navigator.webdriver", self.run_id, exc_info=True)

    def stop_driver(self) -> None:
        if self.driver and self._driver_closed:
            # stop() already quit it; calling quit again just retries against a
            # socket that is gone.
            self.driver = None
            return
        if self.driver:
            try:
                self.driver.quit()
            except Exception:  # noqa: BLE001 — a dead session raises urllib3 errors, not WebDriverException
                logger.debug("[run %s] browser was already gone at shutdown", self.run_id, exc_info=True)
            self.driver = None

    def cleanup(self) -> None:
        live.unregister(self.run_id)
        self.stop_driver()

    def get_screenshot_base64(self) -> str | None:
        """A base64 PNG of the current browser view, or None. Used by the shared
        live-screenshot endpoint; defensive so a frame grab never breaks a run."""
        if not self.driver or self._driver_closed:
            return None
        try:
            return self.driver.get_screenshot_as_base64()
        except Exception:  # noqa: BLE001 — a dead session raises urllib3 errors; a frame grab must never break a run
            logger.debug("[run %s] screenshot failed", self.run_id, exc_info=True)
            return None

    # -- navigation ---------------------------------------------------------

    def navigate(
        self,
        url: str,
        attempts: int = NAVIGATE_ATTEMPTS,
        backoff: float = NAVIGATE_BACKOFF,
    ) -> None:
        """driver.get(url), retrying transient network/DNS failures.

        Non-transient WebDriver errors are re-raised immediately — only the
        errors in TRANSIENT_NET_ERRORS are worth a second attempt. If every
        attempt fails we raise with the host name and the underlying Chrome
        error, so the cause is obvious instead of a bare stack trace.
        """
        delay = backoff
        last_exc: WebDriverException | None = None
        for attempt in range(1, attempts + 1):
            self.raise_if_stopped()  # don't start/retry a load the user has cancelled
            try:
                self.driver.get(url)
                if attempt > 1:
                    logger.info(
                        "[run %s] navigation to %s succeeded on attempt %d",
                        self.run_id, url, attempt,
                    )
                return
            except WebDriverException as exc:
                message = (getattr(exc, "msg", None) or str(exc)).lower()
                if not any(err in message for err in TRANSIENT_NET_ERRORS):
                    raise  # a real navigation error — don't mask it behind retries
                last_exc = exc
                if attempt == attempts:
                    break
                logger.warning(
                    "[run %s] transient network error loading %s (attempt %d/%d) — "
                    "retrying in %.1fs", self.run_id, url, attempt, attempts, delay,
                )
                time.sleep(delay)
                delay *= 2

        host = urlparse(url).hostname or url
        detail = (getattr(last_exc, "msg", None) or str(last_exc)).strip().splitlines()[0]
        raise WebDriverException(
            f"Could not reach {host} after {attempts} attempts — {detail}. "
            f"This is a network/DNS problem rather than a portal change: check "
            f"that this machine can resolve {host} (some ISP resolvers return an "
            f"empty answer for certain domains; a public resolver such as 8.8.8.8 "
            f"or 1.1.1.1 fixes that)."
        ) from last_exc

    # -- failure reporting --------------------------------------------------

    # A dead browser (Chrome killed by the OOM reaper, a hard renderer crash, or
    # the Live-Preview window being closed) doesn't surface as a clean Selenium
    # error: the command socket to chromedriver is simply gone, so the call
    # raises a urllib3 connection error instead. Match those signatures anywhere
    # in the exception chain so the run reports a clear cause.
    _DEAD_SESSION_SIGNATURES = (
        "connection refused",
        "failed to establish a new connection",
        "max retries exceeded",
        "chrome not reachable",
        "no such session",
        "invalid session id",
        "session deleted because of page crash",
        "disconnected: not connected to devtools",
        "unable to connect to renderer",
    )

    @classmethod
    def _is_dead_session_error(cls, exc: BaseException) -> bool:
        """True if `exc` (or anything it wraps) means the browser process is gone."""
        seen: set[int] = set()
        cur: BaseException | None = exc
        while cur is not None and id(cur) not in seen:
            seen.add(id(cur))
            if isinstance(cur, (InvalidSessionIdException, _Urllib3HTTPError)):
                return True
            text = (getattr(cur, "msg", None) or str(cur)).lower()
            if any(sig in text for sig in cls._DEAD_SESSION_SIGNATURES):
                return True
            cur = cur.__cause__ or cur.__context__
        return False

    @classmethod
    def describe_failure(cls, exc: BaseException) -> str:
        """A human-readable cause for a run failure, cleaned up for a dead browser."""
        if cls._is_dead_session_error(exc):
            return (
                "The browser was terminated mid-run — most likely the machine ran "
                "out of memory (Chrome was OOM-killed), or the Live-Preview window "
                "was closed. Free up RAM (close other browsers / stale dev servers) "
                "and run it again."
            )
        return (str(getattr(exc, "msg", None) or exc).strip().splitlines() or [""])[0][:500]

    # -- pause / stop -------------------------------------------------------

    def stop(self) -> None:
        """Interrupt this run from another thread (the stop endpoint).

        Sets the cooperative flag and quits the browser: quitting makes whatever
        Selenium call the worker is blocked on raise at once, so the run unwinds
        immediately rather than only at the next checkpoint. Safe to call more
        than once.
        """
        self._stop_requested = True
        # Mark the browser unusable rather than clearing `self.driver`: clearing
        # it would turn the worker's in-flight Selenium call into an
        # AttributeError, which `except WebDriverException` handlers do not catch.
        self._driver_closed = True
        driver = self.driver
        if driver is not None:
            try:
                driver.quit()
            except Exception:  # noqa: BLE001 — the driver may already be gone
                logger.debug("[run %s] browser was already gone when stopped", self.run_id, exc_info=True)

    def raise_if_stopped(self) -> None:
        """Checkpoint: park while paused, and raise StopRequested on a stop.

        A pause holds the thread and the browser, so resuming continues exactly
        where it stopped with nothing replayed. Stop is checked first and again
        after, so a paused run can be stopped without being resumed first.
        """
        if self._stop_requested or run_manager.is_stop_requested(self.run_id):
            raise StopRequested("run stopped by user")

        if run_manager.is_paused(self.run_id):
            logger.info("[run %s] paused", self.run_id)
            while run_manager.await_resume(self.run_id):
                # Bounded waits, so a stop lands on a parked worker promptly
                # rather than waiting for a resume that may never come.
                if self._stop_requested or run_manager.is_stop_requested(self.run_id):
                    raise StopRequested("run stopped by user")
            logger.info("[run %s] resumed", self.run_id)

        if self._stop_requested or run_manager.is_stop_requested(self.run_id):
            raise StopRequested("run stopped by user")

    # -- stopping with the work kept -----------------------------------------

    def flush_partial(self) -> int:
        """Write whatever this run gathered before Stop; return the row count.

        Overridden by each portal, because only the portal knows where its rows
        are. Must be safe to call on a half-finished run.
        """
        return 0

    def deliver_partial(self) -> None:
        """Package a stopped run so the Stop button does not throw the work away.

        Each step is best-effort, because a stopped run is already unwinding
        through a browser being torn down. The status stays "stopped" — the run
        did not complete — and `partial_results` is what lets the console offer
        its download anyway.
        """
        kept = 0
        try:
            kept = self.flush_partial()
        except Exception:  # noqa: BLE001 — never let the flush lose what is saved
            logger.exception("[run %s] could not flush partial results", self.run_id)

        try:
            from app.core.exports import archive_run

            archive_run(self.run_id)
        except Exception:  # noqa: BLE001 — the download can still rebuild it from the DB
            logger.exception("[run %s] could not package partial results", self.run_id)

        run_manager.mark_partial(self.run_id, kept)
        logger.info(
            "[run %s] stopped by user — kept %d record(s) gathered so far",
            self.run_id, kept,
        )
