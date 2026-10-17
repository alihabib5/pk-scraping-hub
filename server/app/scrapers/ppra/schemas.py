"""Pydantic schemas for the PPRA scraper API."""

from pydantic import BaseModel, Field

from app.core.closing_filter import MIN_DAYS_UNTIL_CLOSE


class PpraFilters(BaseModel):
    """The search form. Dropdown fields carry the site's option ids (see
    `filters.get_filter_options`); names from older runs are still accepted."""

    keyword: str | None = None
    tender_number: str | None = None
    closing_date: str | None = None
    tender_type: str | None = "ALL"
    # Procurements / Disposals / Framework Agreements — the site's "By Method".
    tender_method: str | None = None
    category: str | None = "ALL"
    sector: str | None = "ALL"
    nature: str | None = "ALL"
    organization: str | None = None
    country: str | None = None
    advertise_from: str | None = None
    advertise_to: str | None = None
    status: str | None = "ALL"
    city: str | None = None


class PpraOptions(BaseModel):
    apply_closing_filter: bool | None = None
    closing_runway_days: int | None = Field(default=None, ge=0, le=365)
    delay_ms: int | None = None

    def get_runway_days(self) -> int | None:
        """Returns effective closing runway days (0..365), or None if disabled."""
        if self.closing_runway_days is not None:
            return self.closing_runway_days
        return None if self.apply_closing_filter is False else MIN_DAYS_UNTIL_CLOSE


class PpraScrapeRequest(BaseModel):
    filters: PpraFilters = Field(default_factory=PpraFilters)
    options: PpraOptions = Field(default_factory=PpraOptions)
    live_preview: bool = False
