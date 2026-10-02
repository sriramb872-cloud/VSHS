# backend-python/app/core/time_utils.py
"""Time helpers for the subscription domain.

TIMEZONE POLICY
---------------
The whole application stores **naive UTC** datetimes (``datetime.utcnow()``
as column defaults - the same convention as ``users``, ``refresh_tokens``,
``audit_logs.timestamp`` etc.). Subscription timestamps (``start_at``,
``end_at``, ``free_until``, ``paid_at``) follow that policy: naive UTC in
the database, compared against ``utcnow()`` on the server. Nothing in this
module ever compares a naive and an aware datetime.

The API layer accepts client input with or without a timezone offset
(``2026-12-31T23:59:59`` or ``2026-12-31T18:30:00+05:30``); aware values
are normalised to UTC and stored without tzinfo.

DURATION POLICY
---------------
Durations are duration_value + duration_unit with *calendar-aware* month
and year arithmetic (Jan 31 + 1 month = Feb 28/29), never a blind
``30 * 24h``. ``duration_value = 0`` means zero duration (instantaneous),
which the subscription service treats as "no free trial" - it is never
coerced to a default of 30 days.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone

from app.models.subscription_plan import DURATION_UNITS


def utcnow() -> datetime:
    """The single server-side interpretation of 'now' (naive UTC)."""
    return datetime.utcnow()


def as_utc_naive(value: datetime) -> datetime:
    """Normalise any client/provider datetime to naive UTC."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-8601 string (with or without offset) to naive UTC."""
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    return as_utc_naive(datetime.fromisoformat(text))


def _add_months(day: datetime, months: int) -> datetime:
    """Calendar-aware month arithmetic with end-of-month clamping.

    Jan 31 + 1 month -> Feb 28/29; Mar 31 + 1 month -> Apr 30.
    """
    total = day.month - 1 + months
    year = day.year + total // 12
    month = total % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month, day=min(day.day, last_day))


def add_duration(start: datetime, value: int, unit: str) -> datetime:
    """Return ``start`` advanced by ``value`` ``unit`` (calendar-aware).

    * DAY   -> exact ``timedelta(days=value)``
    * MONTH -> calendar months, clamped to the month's last day
    * YEAR  -> calendar years, clamped (Feb 29 + 1 year = Feb 28)

    Raises ValueError for an unknown unit or a negative value - callers
    validate ``duration_value >= 0`` and the unit against DURATION_UNITS.
    """
    if unit not in DURATION_UNITS:
        raise ValueError(f"Invalid duration unit: {unit!r}")
    if value < 0:
        raise ValueError("Duration value must not be negative")

    if unit == "DAY":
        return start + timedelta(days=value)
    if unit == "MONTH":
        return _add_months(start, value)
    # YEAR
    return _add_months(start, value * 12)


def seconds_left(end: datetime, now: datetime) -> float:
    """Seconds between ``now`` and ``end`` (negative when past)."""
    return (end - now).total_seconds()


def days_left(end: datetime, now: datetime) -> int:
    """Whole days left until ``end`` (0 when the end is today or past)."""
    delta = end - now
    return delta.days if delta.total_seconds() > 0 else 0
