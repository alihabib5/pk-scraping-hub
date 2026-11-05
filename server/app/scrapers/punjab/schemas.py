"""Request models for the Punjab scraper API.

Unknown fields are refused and dropdowns accept digits only, because these values
end up driving a browser.
"""

from datetime import date
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.closing_filter import MIN_DAYS_UNTIL_CLOSE
from app.scrapers.punjab.parsers import AUCTION_TITLE_ID

SiteId = Annotated[str, StringConstraints(pattern=r"^\d{1,6}$")]


class PunjabFilters(BaseModel):
    """The search form. Dropdowns carry the site's option ids. Blank dates mean
    "from today" and "as far ahead as the site goes", worked out on the day of
    the run, so a Refresh a week later searches from that new day."""

    model_config = ConfigDict(extra="forbid")

    procurement_type: SiteId | None = None
    procurement_category: SiteId | None = None
    procurement_title: SiteId | None = None
    department: SiteId | None = None
    closing_from: date | None = None
    closing_to: date | None = None

    @model_validator(mode="after")
    def _dates_in_order(self) -> Self:
        if self.closing_from and self.closing_to and self.closing_from > self.closing_to:
            raise ValueError("closing_from must not be after closing_to")
        return self


class PunjabOptions(BaseModel):
    """`apply_closing_filter` and `closing_runway_days` share their names and
    meaning with PPRA: the console's status card reads them for every portal."""

    model_config = ConfigDict(extra="forbid")

    apply_closing_filter: bool | None = None
    closing_runway_days: int | None = Field(default=None, ge=0, le=365)
    exclude_auctions: bool = True

    def get_runway_days(self) -> int | None:
        """Effective closing runway in days (0..365), or None if disabled."""
        if self.closing_runway_days is not None:
            return self.closing_runway_days
        return None if self.apply_closing_filter is False else MIN_DAYS_UNTIL_CLOSE


class PunjabScrapeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filters: PunjabFilters = Field(default_factory=PunjabFilters)
    options: PunjabOptions = Field(default_factory=PunjabOptions)
    live_preview: bool = False

    @model_validator(mode="after")
    def _auction_search_needs_auctions(self) -> Self:
        if self.options.exclude_auctions and self.filters.procurement_title == AUCTION_TITLE_ID:
            raise ValueError("searching only auctions while excluding auctions can return nothing")
        return self
