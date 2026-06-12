"""Which tower is live this week?

The community spreadsheet computes the current tower as the number of whole
weeks since Monday 2023-05-29, modulo 29 (0 means tower 29). The guide rolls
over Sunday night into Monday. Verified against the live sheet's "Guide of
the week" tab (2026-06-11 -> Tower 13).
"""

from datetime import date

ANCHOR = date(2023, 5, 29)
CYCLE_WEEKS = 29


def current_tower(on_date=None):
    d = on_date or date.today()
    weeks = (d - ANCHOR).days // 7
    n = weeks % CYCLE_WEEKS
    return n if n else CYCLE_WEEKS


def week_range(on_date=None):
    """The Monday..Sunday range the current guide covers."""
    from datetime import timedelta
    d = on_date or date.today()
    weeks = (d - ANCHOR).days // 7
    start = ANCHOR + timedelta(weeks=weeks)
    return start, start + timedelta(days=6)
