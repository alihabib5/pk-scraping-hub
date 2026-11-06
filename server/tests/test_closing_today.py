"""'Today' for the closing guard is the Pakistan date, whatever the server's clock says."""

from datetime import datetime, timezone

from app.core import closing_filter


def test_today_is_the_pakistan_date_even_when_utc_is_a_day_behind(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            # 20:00 UTC on 6 Nov is 01:00 on 7 Nov in Pakistan.
            return datetime(2026, 11, 6, 20, 0, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(closing_filter, "datetime", Clock)
    assert closing_filter.days_until_close("2026-11-13") == 6
