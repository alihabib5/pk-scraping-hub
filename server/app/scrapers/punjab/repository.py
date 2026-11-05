"""Database writes for Punjab runs and tenders, and the local JSONL mirror."""

import json
import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.db import SessionLocal
from app.scrapers.punjab.models import PunjabBid, PunjabRun

logger = logging.getLogger(__name__)


def _iso_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def init_run_in_db(
    run_id: str,
    filters: dict[str, Any],
    filters_hash: str,
    options: dict[str, Any],
    parent_run_id: str | None = None,
) -> None:
    session = SessionLocal()
    try:
        session.add(
            PunjabRun(
                run_id=run_id,
                parent_run_id=parent_run_id,
                status="running",
                filters=filters,
                filters_hash=filters_hash,
                options=options,
                started_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_run_progress(run_id: str, **fields: Any) -> None:
    """Best-effort: a missed progress write must not fail a scrape."""
    session = SessionLocal()
    try:
        run = session.get(PunjabRun, run_id)
        if run:
            for key, value in fields.items():
                setattr(run, key, value)
            session.commit()
    except Exception:  # noqa: BLE001 — progress is advisory; the rows are what matter
        session.rollback()
        logger.exception("[run %s] could not record progress", run_id)
    finally:
        session.close()


def get_parent_run_hashes(parent_run_id: str) -> dict[str, str]:
    """{tender_no: content_hash} from the parent run, to detect changes."""
    session = SessionLocal()
    try:
        rows = session.execute(
            select(PunjabBid.tender_no, PunjabBid.content_hash).where(PunjabBid.run_id == parent_run_id)
        ).all()
        return {row[0]: row[1] for row in rows}
    finally:
        session.close()


def upsert_bids(
    run_id: str,
    page_no: int,
    records: list[dict[str, Any]],
    parent_hashes: dict[str, str] | None = None,
) -> tuple[int, int, int]:
    """Save one page of tenders. Returns (new, changed, unchanged)."""
    if not records:
        return 0, 0, 0

    new_count = changed_count = unchanged_count = 0
    session = SessionLocal()
    try:
        for record in records:
            tender_no = record["tender_no"]
            content_hash = record["content_hash"]
            change_status = "new"
            if parent_hashes is not None and tender_no in parent_hashes:
                change_status = "unchanged" if parent_hashes[tender_no] == content_hash else "changed"

            if change_status == "new":
                new_count += 1
            elif change_status == "changed":
                changed_count += 1
            else:
                unchanged_count += 1

            values = {
                "run_id": run_id,
                "page_no": page_no,
                "position": record["position"],
                "tender_no": tender_no,
                "title": record["title"],
                "notice_type": record.get("notice_type"),
                "procurement_type": record.get("procurement_type"),
                "department": record.get("department"),
                "status": record.get("status"),
                "published_on": _iso_date(record.get("published_on")),
                "closing_on": _iso_date(record.get("closing_on")),
                "notice_url": record.get("notice_url"),
                "document_url": record.get("document_url"),
                "content_hash": content_hash,
                "change_status": change_status,
                "raw_data": record.get("raw_data") or {},
            }
            session.execute(
                pg_insert(PunjabBid).values(**values).on_conflict_do_update(
                    constraint="uq_punjab_run_tender",
                    set_={k: v for k, v in values.items() if k not in ("run_id", "tender_no")},
                )
            )
        session.commit()
        return new_count, changed_count, unchanged_count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def append_to_mirror(run_id: str, records: list[dict[str, Any]]) -> None:
    """Append records to <DATA_DIR>/punjab/<run_id>/tenders.jsonl when mirroring is on."""
    if not settings.punjab_local_mirror or not records:
        return
    try:
        mirror_dir = settings.data_root / "punjab" / run_id
        mirror_dir.mkdir(parents=True, exist_ok=True)
        with open(mirror_dir / "tenders.jsonl", "a", encoding="utf-8") as mirror:
            for record in records:
                clean = {k: v for k, v in record.items() if k != "raw_data"}
                mirror.write(json.dumps(clean, default=str, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("[run %s] local mirror write failed: %s", run_id, exc)
