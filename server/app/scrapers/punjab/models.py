"""Database models for Punjab e-procurement scrape runs and tenders."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PunjabRun(Base):
    """One row per Punjab scrape run."""

    __tablename__ = "punjab_runs"

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    parent_run_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("punjab_runs.run_id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    filters_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # The closing dates actually searched: the defaults depend on the day of the run.
    closing_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    closing_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    total_expected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_page: Mapped[int] = mapped_column(Integer, default=0)

    rows_scraped: Mapped[int] = mapped_column(Integer, default=0)
    rows_new: Mapped[int] = mapped_column(Integer, default=0)
    rows_changed: Mapped[int] = mapped_column(Integer, default=0)
    skipped_closing: Mapped[int] = mapped_column(Integer, default=0)
    kept_unverified: Mapped[int] = mapped_column(Integer, default=0)
    skipped_auction: Mapped[int] = mapped_column(Integer, default=0)
    skipped_repeat: Mapped[int] = mapped_column(Integer, default=0)

    checkpoint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bids: Mapped[list["PunjabBid"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class PunjabBid(Base):
    """One row per tender kept from the Punjab search results."""

    __tablename__ = "punjab_bids"
    __table_args__ = (UniqueConstraint("run_id", "tender_no", name="uq_punjab_run_tender"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        Text, ForeignKey("punjab_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    tender_no: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    notice_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    procurement_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # A date, not a datetime: the site's table shows no closing time.
    closing_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    change_status: Mapped[str] = mapped_column(Text, nullable=False, default="new")

    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["PunjabRun"] = relationship(back_populates="bids")


class PunjabFilterOption(Base):
    """One option of a dropdown on the search form, cached from the site.
    `value` is the site's own id."""

    __tablename__ = "punjab_filter_options"

    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
