"""Close-date parsing and the runway rule.

Keep only tenders whose closing date is still at least N days away, so there is
enough runway to prepare and submit. A tender we can confirm closes sooner is
dropped; one whose close date we cannot read is KEPT (we can't prove it fails
the rule) and counted, so a drop is never silent.

`parse_close_date` is deliberately permissive: it tries a list of explicit
formats first, then falls back to a robust dateutil parse — but only when the
text actually contains a 4-digit year, so a stray number never parses into a
bogus "past" date that would wrongly drop a tender.
"""

from __future__ import annotations

import logging
import re
import warnings
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

# The default runway, in days, when a run doesn't set its own.
MIN_DAYS_UNTIL_CLOSE = 7

# Explicit formats tried first (fast, unambiguous), against the whole string and
# its first whitespace-delimited token (so a trailing time/label doesn't defeat
# an otherwise-valid date). dateutil covers anything past this list.
_FORMATS = (
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M %p",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%b %d, %Y",
    "%B %d, %Y",
)

_YEAR_RE = re.compile(r"\b\d{4}\b")


def parse_close_date(raw: Any) -> date | None:
    """Parse a portal's close-date value into a calendar date, or None if it
    can't be read. None is the signal to KEEP a bid (we can't prove it fails)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    candidates = [text]
    first_token = text.split()[0]
    if first_token != text:
        candidates.append(first_token)
    for candidate in candidates:
        for fmt in _FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    # Robust fallback — but only when a real 4-digit year is present, so a bare
    # number or partial string never resolves to a bogus (usually past) date.
    if _YEAR_RE.search(text):
        try:
            from dateutil import parser as _du

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # ignore unknown-tzname (e.g. "EST")
                return _du.parse(text, fuzzy=True).date()
        except (ValueError, OverflowError, TypeError):
            # Kept, not dropped: an unreadable date can't prove the tender closes too soon.
            logger.debug("unreadable close date %r — the tender is kept", text)
    return None


def days_until_close(raw: Any, today: date | None = None) -> int | None:
    """Whole days from today until the close date, or None if unreadable."""
    parsed = parse_close_date(raw)
    if parsed is None:
        return None
    return (parsed - (today or date.today())).days
