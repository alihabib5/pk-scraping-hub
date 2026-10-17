"""Per-run endpoints shared by the console: the jobs list, log tail, live
screenshot, stop / pause / resume, and the Excel download."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core import exports, jobs, live, run_logs, run_manager

router = APIRouter(tags=["runs"])

# What the Active Jobs bar needs per run — deliberately not the whole run dict.
_JOB_FIELDS = (
    "run_id", "scraper", "status", "step", "started_at", "finished_at",
    "bids_found", "bids_processed", "queue_position",
    # Whether a stopped run kept what it had gathered, so the jobs bar can
    # offer its download without a second request per job.
    "partial_results", "partial_record_count",
    # What the run is searching for, for the job's subtitle.
    "search",
)


def _job(run: dict) -> dict:
    """One row of the jobs list."""
    return {field: run.get(field) for field in _JOB_FIELDS}


@router.get("/runs")
def list_all_runs(active: bool = False, limit: int = 50) -> dict:
    """Every run in one call — what the console's session engine polls.
    `active=true` narrows to the ones still going."""
    runs = run_manager.list_runs()
    if active:
        runs = [r for r in runs if r.get("status") not in run_manager.TERMINAL_STATUSES]
    return {"jobs": [_job(r) for r in runs[:limit]], "capacity": jobs.stats()}


@router.get("/runs/{run_id}/logs")
def run_log_tail(run_id: str, after: int = 0) -> dict:
    """This run's log lines newer than `after` — the console passes back the
    last `seq` it saw, so each poll carries only what is new."""
    if not run_manager.get_run(run_id):
        raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
    lines = run_logs.tail(run_id, after=after)
    return {"lines": lines, "seq": lines[-1]["seq"] if lines else after}


@router.get("/runs/{run_id}/screenshot")
def run_screenshot(run_id: str) -> dict:
    """A base64 PNG frame of the run's live browser, or null if none is
    available yet. Always 200 so the modal's poller stays quiet while it waits."""
    return {"screenshot": live.capture(run_id)}


@router.post("/runs/{run_id}/stop")
def stop_run(run_id: str) -> dict:
    """Stop an in-flight run. A run still waiting for a slot is cancelled
    outright; a running one has its state locked to "stopped" and its browser
    interrupted, so it unwinds at once. 409 if the run isn't in progress."""
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
    if run.get("status") not in run_manager.STOPPABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Run is not in progress — nothing to stop.")

    cancelled = jobs.cancel(run_id)
    run_manager.request_stop(run_id)
    if not cancelled:
        live.stop(run_id)
    return {"stopped": True, "run_id": run_id, "cancelled_before_start": cancelled}


@router.post("/runs/{run_id}/pause")
def pause_run(run_id: str) -> dict:
    """Park an executing run at its next page. It keeps its browser and slot,
    so resuming continues exactly where it stopped. 409 unless running."""
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
    if not run_manager.request_pause(run_id):
        raise HTTPException(
            status_code=409,
            detail="Only a running job can be paused — this one is "
                   f"{run.get('status') or 'not running'}.",
        )
    return {"paused": True, "run_id": run_id}


@router.post("/runs/{run_id}/resume")
def resume_run(run_id: str) -> dict:
    """Release a parked run."""
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
    if not run_manager.request_resume(run_id):
        raise HTTPException(status_code=409, detail="This job is not paused — nothing to resume.")
    return {"resumed": True, "run_id": run_id}


@router.get("/runs/{run_id}/download")
def download_run(run_id: str) -> Response:
    """The run's Excel workbook. A stopped run is downloadable too, provided it
    kept something (`partial_results`)."""
    run = run_manager.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Unknown run: {run_id}")
    if run.get("status") == "stopped":
        if not run.get("partial_results"):
            raise HTTPException(
                status_code=409,
                detail="This run was stopped before it gathered any results.",
            )
    elif run.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Run has not completed — nothing to download yet.")

    payload = exports.excel_bytes(run)
    if not payload:
        raise HTTPException(status_code=404, detail="No results are available for this run.")
    data, filename = payload
    return Response(
        content=data,
        media_type=exports.XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
