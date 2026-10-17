"""Tracks scrape runs: status, step and progress counters.

Runs are held in memory keyed by run_id for fast reads, and mirrored to the
`run_state` DB table on every mutation so a run survives a server restart
(otherwise the frontend polls a lost run_id and gets a permanent 404). The dict
is loose so the scraper can attach its own fields (filters, page counts, …).
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_runs: dict[str, dict[str, Any]] = {}

# run_ids the user asked to stop. Once a run is in here its terminal status is
# locked to "stopped": update_run ignores later status/step writes and add_error
# suppresses the browser-teardown errors a forced stop produces, so a
# user-stopped run reads as a clean "Stopped" instead of a scary "Failed".
_stopped: set[str] = set()

# run_ids the user asked to pause. A worker parks at its next checkpoint while
# its id is in here and carries on the moment it leaves — see
# BaseScraper.raise_if_stopped, which is the one place that waits.
_paused: set[str] = set()
# Signalled whenever `_paused` shrinks, so a parked worker wakes at once on
# Resume rather than at the end of a poll interval.
_resumed = threading.Condition(_lock)

# Terminal statuses — a run in any of these is finished and no longer active.
TERMINAL_STATUSES = ("completed", "failed", "stopped")
# Statuses a run can be stopped from: queued (waiting for a slot — see
# app/core/jobs) and everything up to and including execution.
STOPPABLE_STATUSES = ("pending", "queued", "running", "paused")
# Only a run that is actually executing can be paused; a queued run already
# consumes nothing.
PAUSABLE_STATUSES = ("running",)


def _persist(run: dict[str, Any]) -> None:
    """Write-through a snapshot of `run` to the run_state table. Best-effort:
    the scrape must not fail just because the DB is momentarily unavailable."""
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from app.core.models import RunState
        from app.db import SessionLocal

        values = {
            "run_id": run["run_id"],
            "scraper": run.get("scraper"),
            "started_at": run.get("started_at"),
            "data": run,
        }
        stmt = pg_insert(RunState).values(**values).on_conflict_do_update(
            index_elements=[RunState.run_id],
            set_={"scraper": values["scraper"], "started_at": values["started_at"], "data": values["data"]},
        )
        session = SessionLocal()
        try:
            session.execute(stmt)
            session.commit()
        finally:
            session.close()
    except Exception:  # noqa: BLE001 — persistence is best-effort, never fatal to a run
        logger.exception("could not persist run %s", run.get("run_id"))


def load_persisted_runs() -> None:
    """Rehydrate runs from the DB on startup. Any run still in progress was cut
    short by the restart that just happened, so mark it failed — otherwise the
    frontend would poll it forever waiting for a terminal status."""
    try:
        from sqlalchemy import select

        from app.core.models import RunState
        from app.db import SessionLocal

        session = SessionLocal()
        try:
            rows = session.execute(select(RunState)).scalars().all()
        finally:
            session.close()
    except Exception:  # noqa: BLE001 — a DB-less boot still serves everything else
        logger.exception("could not load persisted runs")
        return

    interrupted: list[dict[str, Any]] = []
    with _lock:
        for row in rows:
            run = dict(row.data or {})
            run_id = run.get("run_id")
            if not run_id:
                continue
            if run.get("status") in STOPPABLE_STATUSES:
                run["status"] = "failed"
                run["step"] = "interrupted"
                run["finished_at"] = run.get("finished_at") or datetime.now().isoformat()
                run.setdefault("errors", []).append(
                    "Run interrupted by a server restart — please start it again."
                )
                interrupted.append(run)
            _runs[run_id] = run
    for run in interrupted:
        _persist(run)
    if interrupted:
        logger.info("marked %d interrupted run(s) as failed after restart", len(interrupted))


def create_run(scraper: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    """Register a new run. `scraper` is the portal key ('ppra')."""
    run_id = uuid.uuid4().hex[:12]
    run = {
        "run_id": run_id,
        "scraper": scraper,
        # pending -> queued (waiting for a slot) -> running -> completed |
        # failed | stopped. See app/core/jobs for who moves it between them.
        "status": "pending",
        "step": "queued",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "bids_found": 0,
        "bids_processed": 0,
        "errors": [],
        # Non-fatal notices, kept separate from errors so they don't fail a run.
        "warnings": [],
    }
    if fields:
        run.update(fields)
    with _lock:
        _runs[run_id] = run
        snapshot = dict(run)
    _persist(snapshot)
    return run


def get_run(run_id: str) -> dict[str, Any] | None:
    with _lock:
        run = _runs.get(run_id)
        return dict(run) if run else None


def list_runs(scraper: str | None = None) -> list[dict[str, Any]]:
    with _lock:
        runs = [dict(run) for run in _runs.values() if scraper is None or run.get("scraper") == scraper]
    runs.sort(key=lambda r: r["started_at"], reverse=True)
    return runs


def request_stop(run_id: str) -> bool:
    """Ask an in-flight run to stop. Returns False if the run isn't active.

    Locks the run's terminal status to "stopped" immediately so the UI reflects
    the stop at once and a later status write from the worker (unwinding through
    its own error handling as its browser is torn down) can't flip it to
    "failed". The browser interruption itself is done by the caller via
    live.stop(); this only owns the run-state side.
    """
    with _lock:
        run = _runs.get(run_id)
        if not run or run.get("status") not in STOPPABLE_STATUSES:
            return False
        _stopped.add(run_id)
        # Release a parked worker so a paused run can be stopped outright.
        _paused.discard(run_id)
        _resumed.notify_all()
        run["status"] = "stopped"
        run["step"] = "stopped"
        run["finished_at"] = run.get("finished_at") or datetime.now().isoformat()
        snapshot = dict(run)
    _persist(snapshot)
    return True


def is_stop_requested(run_id: str) -> bool:
    with _lock:
        return run_id in _stopped


def request_pause(run_id: str) -> bool:
    """Ask an executing run to park at its next checkpoint. False if it can't.

    The run keeps its slot and its browser — a hold, not a teardown — so the
    worker carries on at the next page on resume rather than replaying anything.
    """
    with _lock:
        run = _runs.get(run_id)
        if not run or run.get("status") not in PAUSABLE_STATUSES:
            return False
        _paused.add(run_id)
        run["status"] = "paused"
        run["paused_at"] = datetime.now().isoformat()
        snapshot = dict(run)
    _persist(snapshot)
    logger.info("[run %s] pause requested", run_id)
    return True


def request_resume(run_id: str) -> bool:
    """Release a parked run. False if it was not paused. Wakes the worker at
    once rather than letting it find out on its next poll."""
    with _lock:
        run = _runs.get(run_id)
        if not run or run_id not in _paused:
            return False
        _paused.discard(run_id)
        if run.get("status") == "paused":
            run["status"] = "running"
        run["resumed_at"] = datetime.now().isoformat()
        snapshot = dict(run)
        _resumed.notify_all()
    _persist(snapshot)
    logger.info("[run %s] resumed", run_id)
    return True


def is_paused(run_id: str) -> bool:
    with _lock:
        return run_id in _paused


def await_resume(run_id: str, timeout: float = 1.0) -> bool:
    """Block while this run is paused. True if it is still paused on return.

    Bounded so a parked worker stays responsive to a stop.
    """
    with _lock:
        if run_id not in _paused:
            return False
        _resumed.wait(timeout)
        return run_id in _paused


def paused_runs() -> set[str]:
    with _lock:
        return set(_paused)


def update_run(run_id: str, **fields: Any) -> None:
    with _lock:
        run = _runs.get(run_id)
        if not run:
            return
        if run_id in _stopped:
            # A stopped run stays stopped: drop status/step reversions from the
            # worker's teardown, but let finished_at/counts through.
            fields = {k: v for k, v in fields.items() if k not in ("status", "step")}
        run.update(fields)
        snapshot = dict(run)
    _persist(snapshot)


def mark_partial(run_id: str, kept: int) -> None:
    """Record that a stopped run kept the rows it had gathered.

    `partial_results` is what the console keys its Download button off. It is a
    separate field rather than another status: the run *is* stopped and rows are
    missing, and the badge must say so.
    """
    update_run(
        run_id,
        partial_results=True,
        partial_record_count=kept,
        stopped_at=datetime.now().isoformat(),
    )


def add_error(run_id: str, message: str) -> None:
    with _lock:
        run = _runs.get(run_id)
        if not run:
            return
        if run_id in _stopped:
            # The WebDriver errors a forced stop produces aren't real failures.
            return
        run["errors"].append(message)
        snapshot = dict(run)
    _persist(snapshot)


def add_warning(run_id: str, message: str) -> None:
    """Append a non-fatal notice (parallel to add_error). Deduplicated so a
    repeated message doesn't stack up."""
    with _lock:
        run = _runs.get(run_id)
        if not run:
            return
        warnings = run.setdefault("warnings", [])
        if message not in warnings:
            warnings.append(message)
        snapshot = dict(run)
    _persist(snapshot)
