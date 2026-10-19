"""The run's deliverable: one Excel workbook, built from the database.

The sheet is regenerated from `ppra_bids` on every download, so it always
reflects what is stored. On completion (or stop) `archive_run` also writes a
copy into settings.archive_root/<run_id>/, which the download falls back to if
the database cannot be read.
"""

import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.core.filenames import sanitize_filename

logger = logging.getLogger(__name__)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_ISO_DAY = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def excel_name(run: dict[str, Any]) -> str:
    """`PPRA_Tenders(13-10-2026 to 15-10-2026, Goods).xlsx`: the advertise date
    range, then any other filter applied. With no filters at all, falls back to
    `PPRA_Tenders_<YYYY-MM-DD>_<HHMM>.xlsx` from the run's start time in PKT."""
    # Imported here: the PPRA package imports this module while it loads.
    from app.scrapers.ppra.filters import filter_labels

    filters = run.get("filters") or {}
    start = _ppra_day(filters.get("advertise_from"))
    end = _ppra_day(filters.get("advertise_to"))
    parts: list[str] = []
    if start and end:
        parts.append(start if start == end else f"{start} to {end}")
    elif start:
        parts.append(f"from {start}")
    elif end:
        parts.append(f"to {end}")
    closing = _ppra_day(filters.get("closing_date"))
    if closing:
        parts.append(f"closing {closing}")
    parts += [label for _, label in filter_labels(filters)]
    if parts:
        return sanitize_filename(f"PPRA_Tenders({', '.join(parts)})", max_length=150) + ".xlsx"

    started = run.get("started_at")
    dt = None
    if isinstance(started, datetime):
        dt = started
    elif isinstance(started, str) and started:
        try:
            dt = datetime.fromisoformat(started)
        except ValueError:
            logger.warning("[run %s] unreadable started_at %r; naming the file by the current time",
                           run.get("run_id"), started)
    if not dt:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        # run_manager stamps started_at in the server's local time, not UTC.
        dt = dt.astimezone()
    pkt_dt = dt.astimezone(ZoneInfo("Asia/Karachi"))
    return f"PPRA_Tenders_{pkt_dt.strftime('%Y-%m-%d_%H%M')}.xlsx"


def _ppra_day(value: Any) -> str:
    """A filter date as `dd-mm-yyyy`. The console sends `yyyy-mm-dd`; anything
    else is kept as typed, with `/` made filename-safe."""
    text = str(value or "").strip()
    iso = _ISO_DAY.fullmatch(text)
    if iso:
        year, month, day = iso.groups()
        return f"{day}-{month}-{year}"
    return text.replace("/", "-")


def excel_bytes(run: dict[str, Any]) -> tuple[bytes, str] | None:
    """The run's Excel as (bytes, filename): rebuilt from the DB, or read from
    the archived copy if that fails. None when neither is available."""
    # Imported here: the PPRA package imports this module while it loads.
    from app.scrapers.ppra import export as ppra_export

    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "export.xlsx"
            ppra_export.generate_excel(run["run_id"], out)
            return out.read_bytes(), excel_name(run)
    except Exception:  # noqa: BLE001 — fall back to the archived copy
        logger.exception("[run %s] on-demand Excel generation failed", run.get("run_id"))

    path = run.get("excel_path")
    if path and Path(path).is_file():
        try:
            return Path(path).read_bytes(), excel_name(run)
        except OSError:
            logger.exception("[run %s] could not read excel at %s", run.get("run_id"), path)
    return None


def archive_run(run_id: str) -> str | None:
    """Write the finished run's sheet to settings.archive_root/<run_id>/ and
    record it on the run. Best-effort: returns the path, or None on failure.

    One folder per run because the fallback name has minute resolution, so two
    runs started in the same minute would otherwise overwrite each other.
    """
    from app.core import run_manager

    run = run_manager.get_run(run_id)
    if not run:
        return None

    payload = excel_bytes(run)
    if payload is None:
        logger.error("[run %s] no Excel to archive", run_id)
        return None
    data, name = payload
    out_dir = settings.archive_root / run_id
    out = out_dir / name
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    except OSError:
        logger.exception("[run %s] could not write archive Excel", run_id)
        out.unlink(missing_ok=True)
        return None

    run_manager.update_run(run_id, excel_path=str(out), excel_name=out.name, excel_exported=True)
    return str(out)
