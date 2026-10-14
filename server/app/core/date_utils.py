import re
from datetime import date, datetime, timezone
from dateutil import parser as dt_parser


def safe_date(val: object) -> date | None:
    """Safely parse a date string. Rejects values without 4-digit years."""
    if not val or not isinstance(val, (str, date)):
        return None
    if isinstance(val, date):
        return val
    val_str = str(val).strip()
    if not re.search(r"\b20\d{2}\b", val_str):
        return None
    try:
        parsed = dt_parser.parse(val_str, fuzzy=True)
        return parsed.date()
    except Exception:
        return None


def safe_datetime(val: object) -> datetime | None:
    """Safely parse a datetime string, enforcing UTC-awareness."""
    if not val or not isinstance(val, (str, datetime)):
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    val_str = str(val).strip()
    if not re.search(r"\b20\d{2}\b", val_str):
        return None
    try:
        parsed = dt_parser.parse(val_str, fuzzy=True)
        if not parsed.tzinfo:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None

